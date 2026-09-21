from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src" / "jobpilot" / "ui"


def test_ui_assets_are_local_and_exclude_development_sample_lifecycle() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    js = (UI / "app.js").read_text(encoding="utf-8")
    lowered = html.lower()
    assert "LOCAL-FIRST JOB APPLICATION WORKSPACE" in html
    assert "sample lifecycle" not in lowered
    assert "No telemetry" in html
    assert '<script src="app.js"></script>' in html
    assert "connect-src 'none'" in lowered
    # The local shell may display or record employer URLs as inert user data, but it
    # must not load remote scripts, stylesheets, images, iframes, or fetch APIs.
    for attribute in ('src="http://', 'src="https://', 'href="http://', 'href="https://'):
        assert attribute not in lowered
    assert "fetch(" not in js
    assert "XMLHttpRequest" not in js


def test_targeting_ui_exposes_all_agreed_editable_preferences() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    for control_id in ("roles", "min-years", "max-years", "india-cities", "remote-city", "remote-country", "remote-origin-required", "salary-minimum", "notice-days", "employment-types", "excluded-employers", "relocation", "sponsorship"):
        assert f'id="{control_id}"' in html
