from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import psutil
import pytest

from jobpilot.runtime.process_supervisor import ProcessSupervisor


def _alive(process: subprocess.Popen[bytes]) -> bool:
    return process.poll() is None


def test_supervisor_terminates_owned_process_but_not_unrelated() -> None:
    unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    supervisor = ProcessSupervisor()
    try:
        owned = supervisor.spawn([sys.executable, "-c", "import time; time.sleep(30)"])
        assert owned.poll() is None
        assert _alive(unrelated)
        supervisor.terminate_owned(grace_seconds=0.2)
        deadline = time.monotonic() + 3
        while owned.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert owned.poll() is not None
        assert _alive(unrelated), "supervisor must never terminate an unrelated process"
    finally:
        if unrelated.poll() is None:
            unrelated.terminate()
            unrelated.wait(timeout=5)


@pytest.mark.windows
@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object behavior")
def test_windows_job_object_contains_descendant_tree() -> None:
    supervisor = ProcessSupervisor()
    command = [sys.executable, "-c", "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); time.sleep(30)"]
    owned = supervisor.spawn(command)
    time.sleep(0.5)
    supervisor.terminate_owned(grace_seconds=0.1)
    assert owned.poll() is not None


def test_supervisor_terminates_owned_descendant_tree(tmp_path: Path) -> None:
    pid_file = tmp_path / "child.pid"
    parent_code = "import pathlib,subprocess,sys,time; " + "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); " + f"pathlib.Path({str(pid_file)!r}).write_text(str(p.pid)); " + "time.sleep(30)"
    supervisor = ProcessSupervisor()
    owned = supervisor.spawn([sys.executable, "-c", parent_code])
    deadline = time.monotonic() + 5
    while not pid_file.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert pid_file.exists(), "owned parent did not create child process"
    child_pid = int(pid_file.read_text())
    assert psutil.pid_exists(child_pid)
    supervisor.terminate_owned(grace_seconds=0.2)
    deadline = time.monotonic() + 5
    while psutil.pid_exists(child_pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert owned.poll() is not None
    assert not psutil.pid_exists(child_pid), "owned descendant escaped process containment"
