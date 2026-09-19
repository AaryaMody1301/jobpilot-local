from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src" / "jobpilot" / "ui"


def test_phase8_eligibility_resolution_requires_note_before_bridge_call() -> None:
    js = (UI / "phase8.js").read_text(encoding="utf-8")

    assert 'disabled>Mark eligible</button>' in js
    assert 'disabled>Mark ineligible</button>' in js
    assert "addEventListener('input'" in js
    assert "const disabled = !input.value.trim();" in js
    assert "const note = input ? input.value.trim() : '';" in js
    assert "if (!note)" in js
    assert "resolve_application_eligibility', id, eligibility === 'approved', note" in js
