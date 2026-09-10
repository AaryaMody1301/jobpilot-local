from __future__ import annotations

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
    startup_timeout_seconds: float = 120.0
    _supervisor: ProcessSupervisor | None = field(init=False, default=None, repr=False)
    _process: ManagedProcess | None = field(init=False, default=None, repr=False)
    _port: int | None = field(init=False, default=None, repr=False)

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
        return LlamaServerClient(self.base_url)

    def start(self) -> "LlamaRuntimeSession":
        if self._process is not None:
            return self
        if not self.executable.is_file():
            raise FileNotFoundError(self.executable)
        if not self.model_path.is_file():
            raise FileNotFoundError(self.model_path)
        self._port = _reserve_loopback_port()
        command = [
            str(self.executable),
            "-m", str(self.model_path),
            "--host", "127.0.0.1",
            "--port", str(self._port),
            "--ctx-size", str(self.context_tokens),
            "--parallel", "1",
            "--threads", str(max(1, self.threads)),
            "--no-webui",
            "--n-gpu-layers", "0" if self.backend == "cpu" else "auto",
        ]
        self._supervisor = ProcessSupervisor()
        self._process = self._supervisor.spawn(command, cwd=self.executable.parent)
        deadline = time.monotonic() + self.startup_timeout_seconds
        health_url = f"{self.base_url}/health"
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                self.close()
                raise RuntimeError("llama.cpp server exited before becoming healthy")
            try:
                with urllib.request.urlopen(health_url, timeout=2) as response:
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
