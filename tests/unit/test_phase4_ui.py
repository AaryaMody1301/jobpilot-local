from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src" / "jobpilot" / "ui"


def test_phase4_ui_exposes_manual_jd_evidence_review_and_pdf_preview() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    js = (UI / "app.js").read_text(encoding="utf-8")
    assert "PHASE 4" in html
    assert "Manual JD only in Phase 4" in html
    assert "untrusted local data" in html
    for control_id in (
        "jd-form", "jd-source-url", "jd-text", "save-jd", "manual-jd-list",
        "tailoring-runs", "tailoring-gate", "enable-auto-tailoring",
        "tailoring-inspector", "tailoring-diff", "tailoring-keywords",
        "tailoring-validation", "tailored-pdf-preview",
    ):
        assert f'id="{control_id}"' in html
    for bridge_method in (
        "import_manual_job_description", "generate_tailored_resume", "approve_tailored_resume",
        "reject_tailored_resume", "tailored_pdf_data_uri", "enable_automatic_tailoring",
    ):
        assert bridge_method in js
    assert "explicit local action" in html.lower()
    assert "fetch(" not in js
    assert "XMLHttpRequest" not in js
    assert "employer submission remain disabled" in html.lower() or "employer submission: disabled" in html.lower()
