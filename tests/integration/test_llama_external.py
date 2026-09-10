from __future__ import annotations

import os
import socket
import time
import urllib.request
from pathlib import Path

import pytest

from jobpilot.model.llama_server import LlamaServerClient
from jobpilot.runtime.process_supervisor import ProcessSupervisor


pytestmark = pytest.mark.external


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = exc
        time.sleep(0.25)
    raise AssertionError(f"llama.cpp server did not become healthy: {last_error}")


def test_llama_server_schema_output_is_locally_validated() -> None:
    exe_text = os.environ.get("JOBPILOT_LLAMA_SERVER_EXE")
    model_text = os.environ.get("JOBPILOT_TEST_MODEL_GGUF")
    if not exe_text or not model_text:
        pytest.skip("set JOBPILOT_LLAMA_SERVER_EXE and JOBPILOT_TEST_MODEL_GGUF")
    exe = Path(exe_text)
    model = Path(model_text)
    if not exe.is_file() or not model.is_file():
        pytest.skip("configured llama.cpp executable/model file does not exist")

    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    supervisor = ProcessSupervisor()
    try:
        supervisor.spawn([str(exe), "-m", str(model), "--host", "127.0.0.1", "--port", str(port), "-c", "2048", "-np", "1"])
        _wait_for_health(base)
        client = LlamaServerClient(base)
        result = client.request_resume_edits([
            {"role": "system", "content": "Return only structured resume edits. Use the exact fact IDs supplied by the user."},
            {"role": "user", "content": "Fact fact-001 supports: built validated data pipelines. Rewrite field experience.bullet.1 without adding claims."},
        ])
        assert result.edits
        assert all(edit.field_id for edit in result.edits)
    finally:
        supervisor.terminate_owned(grace_seconds=0.2)
