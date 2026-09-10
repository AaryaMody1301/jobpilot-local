from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src" / "jobpilot" / "ui"


def test_phase3_ui_exposes_resource_model_and_explicit_download_controls() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    js = (UI / "app.js").read_text(encoding="utf-8")
    assert "PHASE 3" in html
    for control_id in ("refresh-hardware", "check-model-updates", "runtime-catalogue", "model-catalogue", "model-evaluations"):
        assert f'id="{control_id}"' in html
    assert "No automatic model activity" in html
    assert "No cloud AI" in html
    assert "window.confirm" in js
    assert "install_model_runtime" in js
    assert "install_local_model" in js
    assert "evaluate_local_model" in js
    assert "select_model_for_phase4_review" in js
    assert "fetch(" not in js
    assert "XMLHttpRequest" not in js
