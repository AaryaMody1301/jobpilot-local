from pathlib import Path

from jobpilot.app.phase4_main import run_phase4_gate_report
from jobpilot.runtime.paths import ManagedPaths


def test_phase4_gate_report_is_privacy_safe_and_fail_closed(tmp_path: Path) -> None:
    report = run_phase4_gate_report(ManagedPaths(tmp_path / "JobPilotLocal"))

    assert report["phase"] == 4
    assert report["selected_model_install_id"] is None
    assert report["required_distinct_resumes"] == 5
    assert report["approved_distinct_resumes"] == 0
    assert report["remaining"] == 5
    assert report["persisted_gate_complete"] is False
    assert report["current_review_context_complete"] is False
    assert report["ready_to_close_phase4"] is False
    assert report["automatic_tailoring_enabled"] is False
    assert report["phase5_discovery_enabled"] is False
    assert report["employer_submission_enabled"] is False
    assert report["gate_reason"] == "no selected validated model/configuration is awaiting Phase 4 review"

    private_keys = {"manual_jds", "runs", "facts", "jd_text", "preview", "pdf_relpath", "source_relpath"}
    assert private_keys.isdisjoint(report)
