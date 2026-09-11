from __future__ import annotations

from pathlib import Path

import pytest

from jobpilot.app.phase3_controller import Phase3ApplicationController
from jobpilot.runtime.paths import ManagedPaths

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def test_phase3_controller_launches_idle_and_only_detects_local_hardware(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    controller = Phase3ApplicationController(paths, MIGRATIONS, sample_item_seconds=0.01)
    try:
        state = controller.snapshot()
        assert state["phase"] == 3
        assert state["session_state"] == "idle"
        assert state["worker_alive"] is False
        assert state["model"]["model_installs"] == []
        assert state["model"]["runtime_installs"] == []
        assert state["model"]["auto_tailoring_enabled"] is False
        assert state["model"]["hardware"]["budget"]["max_concurrent_inference"] == 1
    finally:
        controller.close()


def test_model_mutations_are_blocked_while_sample_session_is_running(tmp_path: Path) -> None:
    controller = Phase3ApplicationController(ManagedPaths(tmp_path / "JobPilotLocal"), MIGRATIONS, sample_item_seconds=0.2)
    try:
        controller.start()
        with pytest.raises(RuntimeError, match="idle"):
            controller.refresh_model_hardware()
    finally:
        controller.close()


def test_phase2_resume_gate_remains_independent_and_not_auto_satisfied(tmp_path: Path) -> None:
    controller = Phase3ApplicationController(ManagedPaths(tmp_path / "JobPilotLocal"), MIGRATIONS, sample_item_seconds=0.01)
    try:
        state = controller.snapshot()
        assert state["resume"]["onboarding_ready"] is False
        assert state["model"]["phase4_review_gate_required"] is True
    finally:
        controller.close()
