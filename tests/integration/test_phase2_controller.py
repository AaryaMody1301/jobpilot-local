from pathlib import Path

import pytest

from jobpilot.app.controller import ApplicationController
from jobpilot.runtime.paths import ManagedPaths

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def _controller(tmp_path: Path) -> ApplicationController:
    return ApplicationController(ManagedPaths(tmp_path / "JobPilotLocal"), MIGRATIONS, sample_item_seconds=0.05)


def _resume(path: Path) -> Path:
    path.write_text(
        "\\documentclass{article}\n\\begin{document}\n\\section{Experience}\n"
        "\\begin{itemize}\n\\item Evidence-backed statement.\n\\end{itemize}\n\\end{document}\n",
        encoding="utf-8",
    )
    return path


def test_phase2_snapshot_starts_without_resume_or_background_onboarding(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    try:
        state = controller.snapshot()
        assert state["phase"] == 2
        assert state["session_state"] == "idle"
        assert state["worker_alive"] is False
        assert state["onboarding_busy"] is None
        assert state["resume"]["master"] is None
        assert state["resume"]["onboarding_ready"] is False
    finally:
        controller.close()


def test_resume_changes_are_forbidden_while_session_running(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    source = _resume(tmp_path / "resume.tex")
    try:
        controller.start()
        with pytest.raises(RuntimeError):
            controller.import_master_resume(source)
    finally:
        controller.close()


def test_fact_must_be_resolved_and_template_confirmed_before_onboarding_ready(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    try:
        controller.import_master_resume(_resume(tmp_path / "resume.tex"))
        state = controller.snapshot()["resume"]
        assert state["fact_counts"]["candidate"] == 1
        region = state["regions"][0]
        controller.set_template_region_editable(region["id"], True)
        controller.confirm_template_map()
        fact = controller.snapshot()["resume"]["facts"][0]
        controller.set_fact_status(fact["id"], "approved")
        state = controller.snapshot()["resume"]
        assert state["template_map_status"] == "confirmed"
        assert state["fact_counts"]["approved"] == 1
        assert state["onboarding_ready"] is False
    finally:
        controller.close()


def test_fact_approval_rechecks_source_integrity(tmp_path: Path) -> None:
    controller = _controller(tmp_path)
    try:
        controller.import_master_resume(_resume(tmp_path / "resume.tex"))
        state = controller.snapshot()["resume"]
        fact = state["facts"][0]
        master = state["master"]
        stored = controller.paths.root / master["stored_relpath"]
        stored.write_text("tampered", encoding="utf-8")
        with pytest.raises(RuntimeError, match="integrity"):
            controller.set_fact_status(fact["id"], "approved")
        assert controller.snapshot()["resume"]["facts"][0]["current_status"] == "candidate"
    finally:
        controller.close()
