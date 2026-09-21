from __future__ import annotations

import threading
import time
from pathlib import Path

from jobpilot.model.runtime import LlamaRuntimeSession


class _FakeSupervisor:
    def __init__(self) -> None:
        self.close_calls = 0
        self._lock = threading.Lock()

    def close(self) -> None:
        with self._lock:
            self.close_calls += 1
        time.sleep(0.01)


def test_concurrent_runtime_close_releases_owned_supervisor_once(tmp_path: Path) -> None:
    session = LlamaRuntimeSession(
        executable=tmp_path / "llama-server.exe",
        model_path=tmp_path / "model.gguf",
        backend="cpu",
        context_tokens=4096,
        threads=2,
    )
    supervisor = _FakeSupervisor()
    session._supervisor = supervisor  # type: ignore[assignment]
    session._port = 12345

    threads = [threading.Thread(target=session.close) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=1)

    assert supervisor.close_calls == 1
    assert session._supervisor is None
    assert session._process is None
    assert session._port is None
