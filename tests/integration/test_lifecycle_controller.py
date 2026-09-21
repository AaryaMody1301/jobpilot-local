from pathlib import Path

from jobpilot.app.controller import ApplicationController
from jobpilot.domain.states import SessionState
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import Database


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def _controller(tmp_path: Path) -> ApplicationController:
    return ApplicationController(ManagedPaths(tmp_path / "JobPilotLocal"), MIGRATIONS)


def test_launch_is_idle_without_development_worker(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    try:
        state = controller.snapshot()
        assert state["session_state"] == "idle"
        assert state["worker_alive"] is False
        assert "development_mode" not in state
        assert "sample_work" not in state
        assert "sample_counts" not in state
    finally:
        controller.close()


def test_start_pause_stop_updates_session_state(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    try:
        assert controller.start()["session_state"] == "running"
        assert controller.pause()["session_state"] == "paused"
        stopped = controller.stop()
        assert stopped["session_state"] == "idle"
        assert stopped["worker_alive"] is False
    finally:
        controller.close()


def test_settings_persist_but_reopen_never_resumes(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    first = ApplicationController(paths, MIGRATIONS)
    edited = first.snapshot()["targeting"]
    edited["notice_period_days"] = 45
    first.save_targeting(edited)
    first.start()
    first.close()

    reopened = ApplicationController(paths, MIGRATIONS)
    try:
        state = reopened.snapshot()
        assert state["session_state"] == "idle"
        assert state["worker_alive"] is False
        assert state["targeting"]["notice_period_days"] == 45
    finally:
        reopened.close()


def test_crash_recovery_keeps_launch_idle(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    paths.create_all_roots()
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations()
        db.create_runtime_session("crashed-session")
        db.set_runtime_session_state("crashed-session", SessionState.RUNNING)

    controller = ApplicationController(paths, MIGRATIONS)
    try:
        state = controller.snapshot()
        assert state["session_state"] == "idle"
        assert state["worker_alive"] is False
        assert state["recovery"]["crashed_sessions"] == 1
    finally:
        controller.close()
