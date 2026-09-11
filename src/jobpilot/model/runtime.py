from __future__ import annotations

import os
import secrets
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from jobpilot.model.llama_server import LlamaServerClient
from jobpilot.runtime.process_supervisor import ManagedProcess, ProcessSupervisor


def _reserve_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@dataclass(slots=True)
class LlamaRuntimeSession:
    executable: Path
    model_path: Path
    backend: str
    context_tokens: int
    threads: int
    device_id: str | None = None
    startup_timeout_seconds: float = 120.0
    _supervisor: ProcessSupervisor | None = field(init=False, default=None, repr=False)
    _process: ManagedProcess | None = field(init=False, default=None, repr=False)
    _port: int | None = field(init=False, default=None, repr=False)
    _api_key: str = field(init=False, default_factory=lambda: secrets.token_urlsafe(32), repr=False)

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process is not None else None

    @property
    def base_url(self) -> str:
        if self._port is None:
            raise RuntimeError("llama.cpp runtime is not started")
        return f"http://127.0.0.1:{self._port}"

    @property
    def client(self) -> LlamaServerClient:
        return LlamaServerClient(self.base_url, api_key=self._api_key)

    def command(self) -> list[str]:
        if self.backend == "cpu":
            device = "none"
            gpu_layers = "0"
        elif self.backend == "vulkan":
            device = (self.device_id or "").strip()
            if not device:
                raise RuntimeError("Vulkan inference requires an explicitly discovered llama.cpp device id")
            if not device.casefold().startswith("vulkan"):
                raise RuntimeError(f"device {device!r} is not a Vulkan device")
            gpu_layers = "auto"
        else:
            raise RuntimeError(f"unsupported local inference backend: {self.backend}")
        return [
            str(self.executable),
            "-m", str(self.model_path),
            "--host", "127.0.0.1",
            "--port", str(self._port),
            "--ctx-size", str(self.context_tokens),
            "--parallel", "1",
            "--threads", str(max(1, self.threads)),
            "--no-ui",
            "--no-mmproj",
            "--offline",
            "--cors-origins", "localhost",
            "--no-cors-credentials",
            "--device", device,
            "--n-gpu-layers", gpu_layers,
        ]

    def start(self) -> "LlamaRuntimeSession":
        if self._process is not None:
            return self
        if not self.executable.is_file():
            raise FileNotFoundError(self.executable)
        if not self.model_path.is_file():
            raise FileNotFoundError(self.model_path)
        self._port = _reserve_loopback_port()
        command = self.command()
        environment = dict(os.environ)
        environment["LLAMA_API_KEY"] = self._api_key
        self._supervisor = ProcessSupervisor()
        self._process = self._supervisor.spawn(command, cwd=self.executable.parent, env=environment)
        deadline = time.monotonic() + self.startup_timeout_seconds
        health_url = f"{self.base_url}/health"
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                self.close()
                raise RuntimeError("llama.cpp server exited before becoming healthy")
            try:
                request = urllib.request.Request(health_url, headers={"Authorization": f"Bearer {self._api_key}"})
                with urllib.request.urlopen(request, timeout=2) as response:
                    if response.status == 200:
                        return self
            except (urllib.error.URLError, TimeoutError):
                pass
            time.sleep(0.25)
        self.close()
        raise TimeoutError("llama.cpp server did not become healthy before timeout")

    def close(self) -> None:
        if self._supervisor is not None:
            self._supervisor.close()
        self._supervisor = None
        self._process = None
        self._port = None

    def __enter__(self) -> "LlamaRuntimeSession":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
