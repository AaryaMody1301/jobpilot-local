from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src" / "jobpilot" / "ui"


def test_assets_are_local_and_exclude_development_sample_lifecycle() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    js = (UI / "app.js").read_text(encoding="utf-8")
    lowered = html.lower()
    assert "LOCAL-FIRST JOB APPLICATION WORKSPACE" in html
    assert "sample lifecycle" not in lowered
    assert "No telemetry" in html
    assert '<script src="app.js"></script>' in html
    assert "connect-src 'none'" in lowered
    for attribute in ('src="http://', 'src="https://', 'href="http://', 'href="https://'):
        assert attribute not in lowered
    assert "fetch(" not in js
    assert "XMLHttpRequest" not in js


def test_targeting_exposes_all_editable_preferences() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    for control_id in (
        "roles", "min-years", "max-years", "india-cities", "remote-city", "remote-country",
        "remote-origin-required", "salary-minimum", "notice-days", "employment-types",
        "excluded-employers", "relocation", "sponsorship",
    ):
        assert f'id="{control_id}"' in html


def test_local_model_controls_preserve_explicit_download_and_evaluation_boundary() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    js = (UI / "app.js").read_text(encoding="utf-8")
    for control_id in (
        "refresh-hardware", "check-model-updates", "runtime-catalogue", "model-catalogue",
        "model-review-gate", "model-evaluations",
    ):
        assert f'id="{control_id}"' in html
    assert "No automatic model download or switching" in html
    assert "No cloud AI" in html
    assert "VulkanN" in html
    assert "five human approvals" in html
    assert "window.confirm" in js
    for method in (
        "install_model_runtime", "install_local_model", "evaluate_local_model",
        "select_model_for_phase4_review",
    ):
        assert method in js
    assert "model-config" in js
    assert "clientOnboardingBusy" in js
    assert "invokeOnboarding" in js
    assert "Boolean(state.onboarding_busy || clientOnboardingBusy)" in js


def test_tailoring_exposes_untrusted_jd_evidence_review_and_pdf_preview() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    js = (UI / "app.js").read_text(encoding="utf-8")
    assert "Manual job descriptions stay untrusted." in html
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
    assert "expected_content_tokens_present" in js
    assert "edited_fields_present_in_pdf" not in js
    assert "explicit local action" in html.lower()
    assert "Real employer writes start disabled" in html or "Employer submission: disabled" in js


def test_eligibility_resolution_requires_note_before_bridge_call() -> None:
    js = (UI / "app.js").read_text(encoding="utf-8")
    assert 'disabled>Mark eligible</button>' in js
    assert 'disabled>Mark ineligible</button>' in js
    assert "const disabled = !input.value.trim();" in js
    assert "const note = input ? input.value.trim() : '';" in js
    assert "if (!note)" in js
    assert "resolve_application_eligibility', id, eligibility === 'approved', note" in js
