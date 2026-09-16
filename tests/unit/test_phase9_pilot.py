from __future__ import annotations

import json
from pathlib import Path

import pytest

from jobpilot.app.phase9_main import create_controller
from jobpilot.applications.platforms import LeverAdapter
from jobpilot.pilot import PILOT_CONFIRMATION_PHRASE
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import utc_now_text


class _Page:
    def __init__(self, url: str) -> None:
        self.url = url


class _Submit:
    def __init__(self) -> None:
        self.clicked = False

    def click(self, timeout: int) -> None:
        assert timeout == 5000
        self.clicked = True


def test_live_adapter_write_mode_is_explicit_and_host_scoped() -> None:
    live_url = "https://jobs.lever.co/example/apply"
    with pytest.raises(RuntimeError, match="writes are disabled"):
        LeverAdapter(_Page(live_url)).fill({})

    adapter = LeverAdapter(_Page(live_url), allow_live_submit=True)
    submit = _Submit()
    adapter._submit = submit
    adapter.fill({})
    adapter.submit()
    assert submit.clicked is True

    with pytest.raises(RuntimeError, match="writes are disabled"):
        LeverAdapter(_Page("https://example.com/apply"), allow_live_submit=True).fill({})

    with pytest.raises(ValueError, match="mutually exclusive"):
        LeverAdapter(_Page(live_url), allow_live_submit=True, allow_controlled_submit=True)


def test_pilot_activation_resets_on_new_launch(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    controller = create_controller(paths, sample_item_seconds=0.01)
    try:
        state = controller.snapshot()
        assert state["distribution"]["pilot_session_active"] is False
        assert state["distribution"]["real_employer_submission_enabled"] is False
        with pytest.raises(ValueError, match="type exactly"):
            controller.activate_real_application_pilot("enable")
        state = controller.activate_real_application_pilot(PILOT_CONFIRMATION_PHRASE)
        assert state["distribution"]["pilot_session_active"] is True
        assert state["distribution"]["real_employer_submission_enabled"] is True
    finally:
        controller.close()

    reopened = create_controller(paths, sample_item_seconds=0.01)
    try:
        state = reopened.snapshot()
        assert state["distribution"]["pilot_session_active"] is False
        assert state["distribution"]["real_employer_submission_enabled"] is False
    finally:
        reopened.close()


def test_prepared_real_application_requires_activation_and_clean_read_only_inspection(tmp_path: Path) -> None:
    controller = create_controller(ManagedPaths(tmp_path / "JobPilotLocal"), sample_item_seconds=0.01)
    try:
        now = utc_now_text()
        application_id = "phase9-pilot-test"
        clean_inspection = {
            "supported": True,
            "fields": [],
            "blockers": [],
            "submit_controls": 1,
            "read_only": True,
        }
        with controller.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO application_attempts(
                    id, job_identity, state, updated_at, created_at, controlled_fixture,
                    package_id, provider, live_apply_url, live_form_json
                ) VALUES (?, ?, 'prepared', ?, ?, 0, ?, 'lever', ?, ?)
                """,
                (
                    application_id,
                    "job:phase9-pilot-test",
                    now,
                    now,
                    "package-fixture",
                    "https://jobs.lever.co/example/apply",
                    json.dumps(clean_inspection),
                ),
            )
        controller.applications.package_stale_reason = lambda _: None  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="activate the measured"):
            controller.queue_prepared_pilot_application(application_id)

        controller.activate_real_application_pilot(PILOT_CONFIRMATION_PHRASE)
        state = controller.queue_prepared_pilot_application(application_id)
        attempt = next(item for item in state["orchestration"]["history"] if item["id"] == application_id)
        assert attempt["state"] == "queued"
        assert attempt["controlled_fixture"] == 0
        assert attempt["target_url"] == "https://jobs.lever.co/example/apply"
        assert state["distribution"]["pilot_armed_this_launch"] == 1
    finally:
        controller.close()


def test_pilot_queue_rejects_blocked_live_inspection(tmp_path: Path) -> None:
    controller = create_controller(ManagedPaths(tmp_path / "JobPilotLocal"), sample_item_seconds=0.01)
    try:
        now = utc_now_text()
        application_id = "phase9-blocked-test"
        blocked_inspection = {
            "supported": False,
            "fields": [],
            "blockers": ["captcha"],
            "submit_controls": 1,
            "read_only": True,
        }
        with controller.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO application_attempts(
                    id, job_identity, state, updated_at, created_at, controlled_fixture,
                    package_id, provider, live_apply_url, live_form_json
                ) VALUES (?, ?, 'prepared', ?, ?, 0, ?, 'lever', ?, ?)
                """,
                (
                    application_id,
                    "job:phase9-blocked-test",
                    now,
                    now,
                    "package-fixture-blocked",
                    "https://jobs.lever.co/example/apply",
                    json.dumps(blocked_inspection),
                ),
            )
        controller.applications.package_stale_reason = lambda _: None  # type: ignore[method-assign]
        controller.activate_real_application_pilot(PILOT_CONFIRMATION_PHRASE)
        with pytest.raises(RuntimeError, match="captcha"):
            controller.queue_prepared_pilot_application(application_id)
        assert controller.applications.attempt(application_id)["state"] == "prepared"
    finally:
        controller.close()
