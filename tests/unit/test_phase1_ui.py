from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src" / "jobpilot" / "ui"


def test_ui_assets_are_local_and_preserve_sample_lifecycle_boundary() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    js = (UI / "app.js").read_text(encoding="utf-8")
    lowered = html.lower()
    assert "PHASE 4" in html
    assert "sample lifecycle" in lowered
    assert "No telemetry" in html
    assert '<script src="app.js"></script>' in html
    assert "connect-src 'none'" in lowered
    # Phase 4 may display or record an employer URL as inert user data, but it
    # must not load any remote script, stylesheet, image, iframe, or fetch API.
    for attribute in ('src="http://', 'src="https://', 'href="http://', 'href="https://'):
        assert attribute not in lowered
    assert "fetch(" not in js
    assert "XMLHttpRequest" not in js


def test_targeting_ui_exposes_all_agreed_editable_preferences() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    for control_id in ("roles", "min-years", "max-years", "india-cities", "remote-city", "remote-country", "remote-origin-required", "salary-minimum", "notice-days", "employment-types", "excluded-employers", "relocation", "sponsorship"):
        assert f'id="{control_id}"' in html
