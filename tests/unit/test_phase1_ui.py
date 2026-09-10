from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src" / "jobpilot" / "ui"


def test_ui_assets_are_local_and_mark_sample_mode() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    js = (UI / "app.js").read_text(encoding="utf-8")
    assert "PHASE 1" in html
    assert "No telemetry" in html
    assert '<script src="app.js"></script>' in html
    assert "http://" not in html.lower()
    assert "https://" not in html.lower()
    assert "fetch(" not in js
    assert "XMLHttpRequest" not in js


def test_targeting_ui_exposes_all_agreed_editable_preferences() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    for control_id in (
        "roles", "min-years", "max-years", "india-cities", "remote-city",
        "remote-country", "remote-origin-required", "salary-minimum",
        "notice-days", "employment-types", "excluded-employers",
        "relocation", "sponsorship",
    ):
        assert f'id="{control_id}"' in html
