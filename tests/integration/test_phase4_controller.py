from __future__ import annotations

from pathlib import Path

import pytest

from jobpilot.app.phase4_controller import Phase4ApplicationController
from jobpilot.runtime.paths import ManagedPaths

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def _controller(tmp_path: Path) -> Phase4ApplicationController:
    return Phase4ApplicationController(ManagedPaths(tmp_path / "JobPilotLocal"), MIGRATIONS, sample_item_seconds=0.02)


def test_phase4_launch_is_idle_and_manual_jd_does_not_start_model_or_discovery(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    try:
        before = controller.snapshot()
        assert before["phase"] == 4
        assert before["session_state"] == "idle"
        assert before["worker_alive"] is False
        assert before["tailoring"]["manual_jds"] == []
        assert before["tailoring"]["phase5_discovery_enabled"] is False
        assert before["tailoring"]["employer_submission_enabled"] is False
        assert before["model"]["model_installs"] == []

        after = controller.import_manual_job_description("Data Engineer role. Strong SQL required.")
        assert after["session_state"] == "idle"
        assert after["worker_alive"] is False
        assert len(after["tailoring"]["manual_jds"]) == 1
        assert after["model"]["model_installs"] == []
        assert not any(controller.paths.models.iterdir())
    finally:
        controller.close()


def test_generation_refuses_before_private_resume_and_model_gates(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    try:
        state = controller.import_manual_job_description("SQL data engineer role")
        jd_id = state["tailoring"]["manual_jds"][0]["id"]
        with pytest.raises(RuntimeError, match="master resume"):
            controller.generate_tailored_resume(jd_id)
        assert controller.snapshot()["tailoring"]["runs"] == []
    finally:
        controller.close()


def test_manual_jd_persists_across_clean_reopen_but_session_never_resumes(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    first = Phase4ApplicationController(paths, MIGRATIONS, sample_item_seconds=0.02)
    first.import_manual_job_description("Analytics Engineer role with dbt and SQL")
    first.start()
    first.close()

    second = Phase4ApplicationController(paths, MIGRATIONS, sample_item_seconds=0.02)
    try:
        state = second.snapshot()
        assert state["session_state"] == "idle"
        assert state["worker_alive"] is False
        assert len(state["tailoring"]["manual_jds"]) == 1
        assert state["confirmed_applications_today"] == 0
    finally:
        second.close()
