from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from jobpilot.app.bridge import DesktopBridge
from jobpilot.app.main import create_controller, run_review_gate_report
from jobpilot.domain.states import ApplicationState
from jobpilot.domain.states import SessionState
from jobpilot.jobs import assess_job, normalize_manual_job
from jobpilot.pilot import LiveHostedFormEngine
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.settings import TargetingSettings


def _job(index: int, title: str = "Data Analyst") -> dict[str, object]:
    return normalize_manual_job({
        "employer": f"Example {index}", "title": title, "location": "Surat, India",
        "workplace_type": "onsite", "employment_type": "permanent_full_time",
        "source_url": f"https://example.invalid/jobs/{index}",
        "description": "Permanent full-time data analyst role in Surat.",
    })


def test_desktop_model_actions_return_full_product_state(tmp_path: Path) -> None:
    controller = create_controller(ManagedPaths(tmp_path / "profile"))
    try:
        bridge = DesktopBridge(controller)
        with patch.object(controller, "select_model_for_review", return_value={"selection": {}}):
            selected = bridge.select_model_for_review("fixture")
        with patch.object(controller, "enable_automatic_tailoring", return_value={"selection": {}}):
            enabled = bridge.enable_automatic_tailoring()
        for state in (selected, enabled):
            assert state["session_state"] == "idle"
            assert "resume" in state and "model" in state and "orchestration" in state
    finally:
        controller.close()


def test_second_process_cannot_recover_an_active_profile(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "profile")
    controller = create_controller(paths)
    try:
        controller.start()
        with pytest.raises(RuntimeError, match="already open"):
            create_controller(paths)
        assert run_review_gate_report(paths)["remaining"] == 5
        assert controller.database.connection.execute(
            "SELECT state FROM runtime_sessions WHERE id=?", (controller.session_id,)
        ).fetchone()[0] == "running"
    finally:
        controller.stop()
        controller.close()
    reopened = create_controller(paths)
    reopened.close()


def test_scheduler_keeps_eligible_application_until_model_is_ready(tmp_path: Path) -> None:
    controller = create_controller(ManagedPaths(tmp_path / "profile"))
    try:
        controller.job_store.upsert(_job(0))
        assert controller._orchestrate_once(threading.Event()) is True
        assert controller._orchestrate_once(threading.Event()) is False
        assert controller.applications.history()[0]["state"] == "eligible"
    finally:
        controller.close()


def test_scheduler_processes_jobs_past_display_limits(tmp_path: Path) -> None:
    controller = create_controller(ManagedPaths(tmp_path / "profile"))
    try:
        for index in range(205):
            controller.job_store.upsert(_job(index, title="Accountant"))
        for _ in range(205):
            assert controller._orchestrate_once(threading.Event()) is True
        assert controller.database.connection.execute("SELECT COUNT(*) FROM application_attempts").fetchone()[0] == 205
        assert len(controller.applications.history()) == 200  # Display size does not cap the scheduler.
    finally:
        controller.close()


def test_matching_does_not_infer_permission_from_unrelated_city_or_negated_sponsorship() -> None:
    job = _job(1)
    remote = assess_job({**job, "location": "Remote - Germany only", "workplace_type": "remote",
                         "description": "Work remotely from Germany only. Our offices include India."}, TargetingSettings(), [])
    assert remote["eligibility"] != "eligible"
    sponsorship = assess_job({**job, "location": "Berlin, Germany", "workplace_type": "onsite",
                              "description": "Visa sponsorship is not available."}, TargetingSettings(), [])
    assert sponsorship["eligibility"] == "ineligible"
    contract = assess_job({**job, "employment_type": "contract"},
                          TargetingSettings(employment_types=("contract",)), [])
    assert contract["eligibility"] == "eligible"


def test_rebuild_preserves_audit_and_refuses_any_prior_submit(tmp_path: Path) -> None:
    controller = create_controller(ManagedPaths(tmp_path / "profile"))
    try:
        controller.job_store.upsert(_job(7, title="Accountant"))
        controller.run_orchestration_cycle()
        original = controller.applications.history()[0]
        assert original["state"] == "ineligible"
        controller.save_targeting({**controller._targeting.to_dict(), "roles": ["Accountant"]})
        controller.rebuild_application(str(original["id"]))
        newer = controller.applications.attempt_for_job(str(original["discovered_job_id"]))
        assert newer is not None and newer["id"] != original["id"]
        assert newer["state"] == "eligible"
        assert controller.applications.attempt(str(original["id"]))["state"] == "ineligible"
        with pytest.raises(RuntimeError, match="latest"):
            controller.rebuild_application(str(original["id"]))
        controller.applications.transition(str(newer["id"]), ApplicationState.STALE, "fixture stale before submission")
        with controller.database.transaction() as connection:
            connection.execute("UPDATE application_attempts SET submit_started_at=? WHERE id=?", ("2026-01-01T00:00:00Z", original["id"]))
        with pytest.raises(RuntimeError, match="submission evidence"):
            controller.rebuild_application(str(newer["id"]))
    finally:
        controller.close()


def test_stop_signals_application_before_waiting_for_discovery(tmp_path: Path) -> None:
    controller = create_controller(ManagedPaths(tmp_path / "profile"))
    order: list[str] = []

    class Worker:
        def request_stop(self) -> None:
            order.append("application_signaled")

        def stop(self, timeout: float = 60.0) -> bool:
            order.append("application_joined")
            return True

        def status(self) -> dict[str, object]:
            return {"alive": False, "paused": False, "current_application_id": None, "last_error": None}

    class Thread:
        def join(self, timeout: float) -> None:
            assert order == ["application_signaled"]
            order.append("discovery_joined")

        def is_alive(self) -> bool:
            return False

    controller._application_worker = Worker()  # type: ignore[assignment]
    controller._orchestration_thread = Thread()  # type: ignore[assignment]
    controller._state = SessionState.RUNNING
    try:
        controller.stop()
        assert order == ["application_signaled", "discovery_joined", "application_joined"]
    finally:
        controller.close()


def test_pilot_rechecks_package_after_filling_before_submit(tmp_path: Path) -> None:
    transitions: list[str] = []
    clicked: list[str] = []

    class Journal:
        stale = False
        database = SimpleNamespace(_lock=threading.RLock())

        def package_stale_reason(self, application_id: str) -> str | None:
            return "profile changed" if self.stale else None

        def transition(self, application_id: str, state: ApplicationState, reason: str) -> None:
            transitions.append(state.value)

        def record_pilot_inspection(self, *args: object) -> None:
            return None

    class Adapter:
        hosts = ("jobs.lever.co",)

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def inspect(self, target: str) -> object:
            return SimpleNamespace(supported=True, fields=[], blockers=[], submit_controls=1)

        def fill(self, answers: object) -> None:
            journal.stale = True

        def submit(self) -> None:
            clicked.append("submit")

    class Context:
        def set_default_timeout(self, timeout: int) -> None:
            pass

        def new_page(self) -> object:
            return SimpleNamespace(close=lambda: None)

        def close(self) -> None:
            pass

    class Playwright:
        def __enter__(self) -> object:
            return SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=lambda *args, **kwargs: Context()))

        def __exit__(self, *args: object) -> None:
            pass

    journal = Journal()
    engine = LiveHostedFormEngine(ManagedPaths(tmp_path / "profile"), journal, lambda: True)  # type: ignore[arg-type]
    with patch("playwright.sync_api.sync_playwright", return_value=Playwright()), \
         patch("jobpilot.pilot._ADAPTERS", {"lever": Adapter}), \
         patch.object(engine, "_resume_path", return_value=tmp_path / "resume.pdf"):
        engine.process({"id": "fixture", "provider": "lever", "target_url": "https://jobs.lever.co/acme/123"}, threading.Event())
    assert transitions == ["filling", "ready_to_submit", "stale"]
    assert clicked == []
