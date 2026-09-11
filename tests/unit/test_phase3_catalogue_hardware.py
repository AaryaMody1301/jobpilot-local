from __future__ import annotations

import hashlib
import threading
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from jobpilot.model.catalogue import CATALOGUE_VERSION, MODELS, RUNTIMES, get_model, get_runtime
from jobpilot.model.downloads import ArtifactIntegrityError, DownloadCancelled, download_verified, extract_zip_verified
from jobpilot.model.hardware import HardwareProbe, ResourcePressureWatcher, classify_memory_pressure
from jobpilot.model.runtime import LlamaRuntimeSession
from jobpilot.model.tooling import parse_llama_devices


def test_catalogue_is_small_versioned_and_content_pinned() -> None:
    assert CATALOGUE_VERSION == "2026-09-11.1"
    assert [model.id for model in MODELS] == ["qwen3-4b-q4_k_m"]
    assert 1 <= len(RUNTIMES) <= 4
    model = MODELS[0]
    assert model.bytes == 2_497_280_640
    assert model.display_bytes == model.bytes
    assert model.install_id == f"{model.id}-{model.source_revision[:12]}"
    assert model.sha256 == "ab27b9bfa375a178d6cba48f3ad892b94b7739659dcc7aae8058ce0ffed6b328"
    assert model.url.startswith("https://huggingface.co/")
    assert model.license == "Apache-2.0"
    assert model.tested_context_tokens == 4096
    assert model.tier == "preferred"
    assert model.reference_cpu_peak_rss_bytes is not None
    assert get_model(model.id) is model
    for runtime in RUNTIMES:
        assert len(runtime.sha256) == 64
        int(runtime.sha256, 16)
        assert runtime.url.startswith("https://github.com/ggml-org/llama.cpp/releases/download/b10809/")
        assert runtime.version == "0.4.0"
        assert get_runtime(runtime.id) is runtime


def test_hardware_probe_creates_conservative_single_inference_budget(tmp_path: Path) -> None:
    snapshot = HardwareProbe(tmp_path).capture().to_dict()
    assert snapshot["memory"]["total_bytes"] > 0
    assert 0 <= snapshot["budget"]["model_ram_budget_bytes"] <= snapshot["memory"]["total_bytes"]
    assert snapshot["budget"]["model_disk_budget_bytes"] >= 0
    assert snapshot["budget"]["max_concurrent_inference"] == 1
    assert snapshot["budget"]["memory_pressure"] in {"normal", "constrained", "critical"}
    for gpu in snapshot["gpus"]:
        if gpu["total_vram_bytes"] is not None:
            assert gpu["total_vram_bytes"] > 0
        assert gpu["evidence"]


def test_memory_pressure_thresholds_are_explicit() -> None:
    gib = 1024**3
    assert classify_memory_pressure(16 * gib, 8 * gib) == "normal"
    assert classify_memory_pressure(16 * gib, 2 * gib) == "constrained"
    assert classify_memory_pressure(16 * gib, gib - 1) == "critical"


def test_pressure_watcher_records_and_fires_once_on_critical() -> None:
    gib = 1024**3
    samples = iter([
        SimpleNamespace(total=16 * gib, available=4 * gib, percent=75.0),
        SimpleNamespace(total=16 * gib, available=int(1.5 * gib), percent=90.0),
        SimpleNamespace(total=16 * gib, available=512 * 1024**2, percent=97.0),
    ])
    last = SimpleNamespace(total=16 * gib, available=512 * 1024**2, percent=97.0)
    calls: list[str] = []
    watcher = ResourcePressureWatcher(
        interval_seconds=0.01,
        memory_reader=lambda: next(samples, last),
        on_critical=lambda: calls.append("critical"),
    )
    watcher.start()
    deadline = time.time() + 1
    while not watcher.critical and time.time() < deadline:
        time.sleep(0.01)
    evidence = watcher.stop()
    assert watcher.critical
    assert calls == ["critical"]
    assert evidence["worst_pressure"] == "critical"
    assert evidence["critical_triggered"] is True
    assert evidence["min_available_bytes"] == 512 * 1024**2


def test_verified_download_is_atomic_and_rejects_wrong_hash(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"phase3-artifact")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    destination = tmp_path / "dest" / "artifact.bin"
    size = download_verified(url=source.resolve().as_uri(), destination=destination, expected_sha256=digest, expected_bytes=source.stat().st_size, cancel_event=threading.Event())
    assert size == source.stat().st_size
    assert destination.read_bytes() == source.read_bytes()
    assert not destination.with_suffix(".bin.part").exists()
    destination.unlink()
    with pytest.raises(ArtifactIntegrityError):
        download_verified(url=source.resolve().as_uri(), destination=destination, expected_sha256="0" * 64, expected_bytes=source.stat().st_size, cancel_event=threading.Event())
    assert not destination.exists()


def test_download_honors_preexisting_cancel(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"cancel")
    cancel = threading.Event(); cancel.set()
    with pytest.raises(DownloadCancelled):
        download_verified(url=source.resolve().as_uri(), destination=tmp_path / "dest.bin", expected_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), expected_bytes=len(source.read_bytes()), cancel_event=cancel)


def test_zip_extraction_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("../escape.txt", "no")
    with pytest.raises(ArtifactIntegrityError):
        extract_zip_verified(archive, tmp_path / "install")
    assert not (tmp_path / "escape.txt").exists()


def test_zip_extraction_rejects_symlink_entry(tmp_path: Path) -> None:
    archive = tmp_path / "symlink.zip"
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (0o120777 << 16)
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(info, "target")
    with pytest.raises(ArtifactIntegrityError, match="symbolic-link"):
        extract_zip_verified(archive, tmp_path / "install")


def test_llama_device_parser_keeps_runtime_reported_identity_and_memory() -> None:
    raw = """Available devices:\nVulkan0: AMD Radeon Graphics (RADV PHOENIX) (29696 MiB, 28598 MiB free)\nVulkan1: NVIDIA GeForce RTX 4060 Laptop GPU (7956 MiB, 7188 MiB free)"""
    devices = parse_llama_devices(raw)
    assert [item["id"] for item in devices] == ["Vulkan0", "Vulkan1"]
    assert devices[1]["name"] == "NVIDIA GeForce RTX 4060 Laptop GPU"
    assert devices[1]["free_memory_bytes"] == 7188 * 1024**2


def test_llama_runtime_cpu_configuration_forces_no_gpu_or_vision(tmp_path: Path) -> None:
    session = LlamaRuntimeSession(executable=tmp_path / "llama-server.exe", model_path=tmp_path / "model.gguf", backend="cpu", context_tokens=4096, threads=2)
    session._port = 12345
    command = session.command()
    assert command[command.index("--device") + 1] == "none"
    assert command[command.index("--n-gpu-layers") + 1] == "0"
    assert "--no-ui" in command
    assert "--no-mmproj" in command
    assert "--offline" in command
    assert session._api_key
    assert "_api_key" not in repr(session)


def test_vulkan_runtime_requires_explicit_device_before_start(tmp_path: Path) -> None:
    session = LlamaRuntimeSession(executable=tmp_path / "llama-server.exe", model_path=tmp_path / "model.gguf", backend="vulkan", context_tokens=4096, threads=2)
    session._port = 12345
    with pytest.raises(RuntimeError, match="explicitly discovered"):
        session.command()
    session.device_id = "Vulkan1"
    command = session.command()
    assert command[command.index("--device") + 1] == "Vulkan1"
    assert command[command.index("--n-gpu-layers") + 1] == "auto"
