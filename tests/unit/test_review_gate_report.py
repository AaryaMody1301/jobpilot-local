from pathlib import Path

from jobpilot.app.main import run_phase4_gate_report
from jobpilot.runtime.paths import ManagedPaths


def test_phase4_gate_report_is_privacy_safe_and_fail_closed(tmp_path: Path) -> None:
    report = run_phase4_gate_report(ManagedPaths(tmp_path / "JobPilotLocal"))

    assert report["selected_model_install_id"] is None
    assert report["required_distinct_resumes"] == 5
    assert report["approved_distinct_resumes"] == 0
    assert report["remaining"] == 5
    assert report["persisted_gate_complete"] is False
    assert report["current_review_context_complete"] is False
    assert report["ready_to_close_phase4"] is False
    assert report["automatic_tailoring_enabled"] is False
    assert report["employer_submission_enabled"] is False
    assert report["gate_reason"] == "no selected validated model/configuration is awaiting human review"
    assert report["resume_readiness"] == {
        "onboarding_ready": False,
        "master_present": False,
        "master_integrity_verified": False,
        "baseline_compiled": False,
        "offline_baseline_verified": False,
        "template_map_confirmed": False,
        "candidate_facts": 0,
        "approved_facts": 0,
        "rejected_facts": 0,
    }

    private_keys = {"manual_jds", "runs", "facts", "jd_text", "preview", "pdf_relpath", "source_relpath"}
    assert private_keys.isdisjoint(report)
