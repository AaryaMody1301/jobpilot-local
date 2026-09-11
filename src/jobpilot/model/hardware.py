from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import subprocess
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import psutil

_GIB = 1024**3
_MIB = 1024**2


def classify_memory_pressure(total_bytes: int, available_bytes: int) -> str:
    total = max(0, int(total_bytes))
    available = max(0, int(available_bytes))
    ratio = available / total if total else 0.0
    if available < 1 * _GIB or ratio < 0.12:
        return "critical"
    if available < 2 * _GIB or ratio < 0.20:
        return "constrained"
    return "normal"


@dataclass(frozen=True, slots=True)
class GpuDevice:
    name: str
    vendor: str
    total_vram_bytes: int | None
    driver_version: str | None
    evidence: str
    backend_candidates: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["backend_candidates"] = list(self.backend_candidates)
        return value


@dataclass(frozen=True, slots=True)
class HardwareSnapshot:
    platform: dict[str, Any]
    memory: dict[str, Any]
    cpu: dict[str, Any]
    disk: dict[str, Any]
    gpus: tuple[GpuDevice, ...]
    budget: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": dict(self.platform),
            "memory": dict(self.memory),
            "cpu": dict(self.cpu),
            "disk": dict(self.disk),
            "gpus": [gpu.to_dict() for gpu in self.gpus],
            "budget": dict(self.budget),
        }


class ResourcePressureWatcher:
    """Polls live RAM pressure during one local inference operation."""

    def __init__(
        self,
        *,
        interval_seconds: float = 0.25,
        memory_reader: Callable[[], Any] = psutil.virtual_memory,
        on_critical: Callable[[], None] | None = None,
    ) -> None:
        self.interval_seconds = max(0.05, float(interval_seconds))
        self.memory_reader = memory_reader
        self.on_critical = on_critical
        self._stop = threading.Event()
        self._critical = threading.Event()
        self._thread = threading.Thread(target=self._run, name="jobpilot-resource-pressure", daemon=True)
        self._lock = threading.Lock()
        self._min_available: int | None = None
        self._max_used_percent = 0.0
        self._worst = "normal"
        self._callback_fired = False

    @property
    def critical(self) -> bool:
        return self._critical.is_set()

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        if self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)
        with self._lock:
            return {
                "worst_pressure": self._worst,
                "min_available_bytes": self._min_available,
                "max_used_percent": self._max_used_percent,
                "critical_triggered": self._critical.is_set(),
            }

    def _run(self) -> None:
        rank = {"normal": 0, "constrained": 1, "critical": 2}
        while not self._stop.wait(self.interval_seconds):
            try:
                memory = self.memory_reader()
                total = int(memory.total)
                available = int(memory.available)
                used_percent = float(memory.percent)
            except Exception:
                continue
            pressure = classify_memory_pressure(total, available)
            callback: Callable[[], None] | None = None
            with self._lock:
                self._min_available = available if self._min_available is None else min(self._min_available, available)
                self._max_used_percent = max(self._max_used_percent, used_percent)
                if rank[pressure] > rank[self._worst]:
                    self._worst = pressure
                if pressure == "critical" and not self._callback_fired:
                    self._callback_fired = True
                    self._critical.set()
                    callback = self.on_critical
            if callback is not None:
                try:
                    callback()
                finally:
                    self._stop.set()
                    return


class HardwareProbe:
    """Conservative local hardware/resource probe with no network access."""

    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root

    def capture(self) -> HardwareSnapshot:
        self.data_root.mkdir(parents=True, exist_ok=True)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(str(self.data_root))
        logical = psutil.cpu_count(logical=True) or 1
        physical = psutil.cpu_count(logical=False) or logical
        frequency = psutil.cpu_freq()
        cpu_features = self._cpu_features()
        gpus = tuple(self._gpu_devices())

        total = int(memory.total)
        available = int(memory.available)
        free_disk = int(disk.free)
        os_other_reserve = max(3 * _GIB, int(total * 0.25))
        browser_reserve = int(1.5 * _GIB)
        app_reserve = 768 * _MIB
        pressure_reserve = 1 * _GIB
        static_model_budget = max(0, total - os_other_reserve - browser_reserve - app_reserve - pressure_reserve)
        live_model_budget = max(0, available - app_reserve - pressure_reserve)
        model_ram_budget = min(static_model_budget, live_model_budget)
        model_disk_budget = max(0, free_disk - 5 * _GIB)
        pressure = classify_memory_pressure(total, available)

        return HardwareSnapshot(
            platform={
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "python_architecture": platform.architecture()[0],
            },
            memory={
                "total_bytes": total,
                "available_bytes": available,
                "used_percent": float(memory.percent),
            },
            cpu={
                "brand": platform.processor() or "unknown",
                "physical_cores": int(physical),
                "logical_cores": int(logical),
                "max_frequency_mhz": float(frequency.max) if frequency else None,
                "features": cpu_features,
            },
            disk={
                "path": str(self.data_root),
                "total_bytes": int(disk.total),
                "free_bytes": free_disk,
                "used_percent": float(disk.percent),
            },
            gpus=gpus,
            budget={
                "policy_version": "phase3-v2",
                "os_and_other_apps_reserve_bytes": os_other_reserve,
                "browser_reserve_bytes": browser_reserve,
                "jobpilot_reserve_bytes": app_reserve,
                "pressure_reserve_bytes": pressure_reserve,
                "model_ram_budget_bytes": model_ram_budget,
                "model_disk_budget_bytes": model_disk_budget,
                "memory_pressure": pressure,
                "max_concurrent_inference": 1,
            },
        )

    @staticmethod
    def _cpu_features() -> list[str]:
        features: list[str] = []
        if os.name == "nt":
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.IsProcessorFeaturePresent.argtypes = [ctypes.c_uint]
            kernel32.IsProcessorFeaturePresent.restype = ctypes.c_int
            for name, value in (
                ("sse2", 10),
                ("sse3", 13),
                ("ssse3", 36),
                ("sse4_1", 37),
                ("sse4_2", 38),
                ("avx", 39),
                ("avx2", 40),
                ("avx512f", 41),
            ):
                if kernel32.IsProcessorFeaturePresent(value):
                    features.append(name)
            return features

        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.is_file():
            text = cpuinfo.read_text(encoding="utf-8", errors="ignore").lower()
            for name in ("sse2", "sse3", "ssse3", "sse4_1", "sse4_2", "avx", "avx2", "avx512f"):
                if name in text:
                    features.append(name)
        return features

    def _gpu_devices(self) -> list[GpuDevice]:
        devices = self._nvidia_devices()
        known_names = {item.name.casefold() for item in devices}
        if os.name == "nt":
            for item in self._windows_display_devices():
                if item.name.casefold() not in known_names:
                    devices.append(item)
        return devices

    @staticmethod
    def _nvidia_devices() -> list[GpuDevice]:
        executable = shutil.which("nvidia-smi")
        if not executable:
            return []
        try:
            result = subprocess.run(
                [
                    executable,
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
                creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0),
            )
        except (OSError, subprocess.SubprocessError):
            return []
        devices: list[GpuDevice] = []
        for line in result.stdout.splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 3:
                continue
            try:
                vram = int(float(parts[1]) * _MIB)
            except ValueError:
                vram = None
            devices.append(
                GpuDevice(
                    name=parts[0] or "NVIDIA GPU",
                    vendor="NVIDIA",
                    total_vram_bytes=vram,
                    driver_version=parts[2] or None,
                    evidence="nvidia-smi",
                    backend_candidates=("vulkan",),
                )
            )
        return devices

    @staticmethod
    def _windows_display_devices() -> list[GpuDevice]:
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not powershell:
            return []
        command = (
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name,DriverVersion | ConvertTo-Json -Compress"
        )
        try:
            result = subprocess.run(
                [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
                capture_output=True,
                text=True,
                timeout=6,
                check=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            decoded = json.loads(result.stdout or "[]")
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            return []
        rows = decoded if isinstance(decoded, list) else [decoded]
        devices: list[GpuDevice] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("Name") or "").strip()
            if not name:
                continue
            lower = name.casefold()
            vendor = "NVIDIA" if "nvidia" in lower else "AMD" if ("amd" in lower or "radeon" in lower) else "Intel" if "intel" in lower else "unknown"
            devices.append(
                GpuDevice(
                    name=name,
                    vendor=vendor,
                    total_vram_bytes=None,
                    driver_version=str(row.get("DriverVersion") or "").strip() or None,
                    evidence="Win32_VideoController name only; VRAM intentionally unknown",
                    backend_candidates=("vulkan",) if vendor != "unknown" else tuple(),
                )
            )
        return devices
