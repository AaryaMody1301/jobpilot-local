from pathlib import Path
import time

from jobpilot.app.controller import ApplicationController
from jobpilot.domain.states import SessionState
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import Database, utc_now_text


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def _controller(tmp_path: Path, *, item_seconds: float = 0.2) -> ApplicationController:
    return ApplicationController(ManagedPaths(tmp_path / "JobPilotLocal"), MIGRATIONS, sample_item_seconds=item_seconds)


def test_launch_is_idle_and_does_not_create_worker(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    try:
        state = controller.snapshot()
        assert state["session_state"] == "idle"
        assert state["worker_alive"] is False
        assert all(item["state"] == "pending" for item in state["sample_work"])
        assert state["confirmed_applications_today"] == 0
    finally:
        controller.close()


def test_pause_prevents_scheduling_next_sample_item(tmp_path: Path) -> None:
    controller = _controller(tmp_path, item_seconds=0.18)
    try:
        controller.start()
        time.sleep(0.04)
        controller.pause()
        time.sleep(0.25)
        first = controller.snapshot()
        done_after_current = first["sample_counts"]["done"]
        assert done_after_current <= 1
        time.sleep(0.25)
        second = controller.snapshot()
        assert second["sample_counts"]["done"] == done_after_current
        assert second["sample_counts"]["running"] == 0
        assert second["session_state"] == "paused"
    finally:
        controller.close()


def test_stop_cancels_running_sample_and_keeps_app_idle(tmp_path: Path) -> None:
    controller = _controller(tmp_path, item_seconds=2.0)
    try:
        controller.start()
        time.sleep(0.05)
        stopped = controller.stop()
        assert stopped["session_state"] == "idle"
        assert stopped["worker_alive"] is False
        assert stopped["sample_counts"]["running"] == 0
        assert stopped["sample_counts"]["pending"] >= 1
    finally:
        controller.close()


def test_settings_persist_but_reopen_never_resumes(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    first = ApplicationController(paths, MIGRATIONS, sample_item_seconds=0.05)
    edited = first.snapshot()["targeting"]
    edited["notice_period_days"] = 45
    first.save_targeting(edited)
    first.start()
    time.sleep(0.08)
    first.close()

    reopened = ApplicationController(paths, MIGRATIONS, sample_item_seconds=0.05)
    try:
        state = reopened.snapshot()
        assert state["session_state"] == "idle"
        assert state["worker_alive"] is False
        assert state["targeting"]["notice_period_days"] == 45
        assert state["sample_counts"]["running"] == 0
    finally:
        reopened.close()


def test_crash_recovery_requeues_sample_and_launches_idle(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    paths.create_all_roots()
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations()
        db.seed_sample_work()
        db.create_runtime_session("crashed-session")
        db.set_runtime_session_state("crashed-session", SessionState.RUNNING)
        claimed = db.claim_next_sample_work("crashed-session")
        assert claimed is not None

    controller = ApplicationController(paths, MIGRATIONS, sample_item_seconds=0.05)
    try:
        state = controller.snapshot()
        assert state["session_state"] == "idle"
        assert state["worker_alive"] is False
        assert state["recovery"]["crashed_sessions"] == 1
        assert state["recovery"]["requeued_work"] == 1
        assert state["sample_counts"]["running"] == 0
    finally:
        controller.close()


def test_close_leaves_no_phase1_worker_thread(tmp_path: Path) -> None:
    import threading

    controller = _controller(tmp_path, item_seconds=2.0)
    controller.start()
    time.sleep(0.05)
    controller.close()
    assert not any(thread.name.startswith("jobpilot-phase1-sample-") for thread in threading.enumerate())
