from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PHASE9_JS = ROOT / "src" / "jobpilot" / "ui" / "phase9.js"


@pytest.fixture
def chromium_page():
    playwright_module = pytest.importorskip("playwright.sync_api")
    with playwright_module.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium unavailable: {exc}")
        page = browser.new_page(viewport={"width": 960, "height": 660})
        try:
            yield page
        finally:
            browser.close()


def test_phase9_controls_render_and_dispatch_explicit_actions(chromium_page) -> None:
    chromium_page.set_content(
        """
        <div class="privacy-note"></div>
        <div class="eyebrow"></div>
        <section id="dashboard"><div class="banner"></div></section>
        <section id="system"></section>
        <div id="phase8-attention">
          <div><button data-phase8-inspect="app-1">Inspect live form read-only</button></div>
        </div>
        """
    )
    chromium_page.add_script_tag(
        content="""
        window.latestState = null;
        window.__calls = [];
        window.escapeHtml = value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
        window.escapeAttr = value => window.escapeHtml(value).replaceAll('"', '&quot;').replaceAll("'", '&#39;');
        window.invoke = async (name, ...args) => { window.__calls.push([name, ...args]); return {}; };
        window.render = state => { window.latestState = state; };
        """
    )
    chromium_page.add_script_tag(path=str(PHASE9_JS))

    state = {
        "session_state": "idle",
        "distribution": {
            "app_version": "0.1.0",
            "pilot_authorized": True,
            "pilot_session_active": True,
            "real_employer_submission_enabled": True,
            "pilot_confirmation_phrase": "ENABLE MEASURED REAL APPLICATION PILOT",
            "pilot_armed_this_launch": 0,
            "pilot_arm_limit": 5,
            "pilot_policy_revision": "phase9-v1",
            "backup": {"format_version": 1, "local_backups": 0, "restore_pending": False},
        },
        "orchestration": {
            "attention": [
                {
                    "id": "app-1",
                    "state": "prepared",
                    "live_form": {"read_only": True, "supported": True, "blockers": [], "submit_controls": 1},
                }
            ]
        },
    }
    chromium_page.evaluate("state => window.render(state)", state)

    assert chromium_page.locator("#phase9-distribution").count() == 1
    assert chromium_page.locator("#phase9-pilot").inner_text().find("ACTIVE") >= 0
    assert chromium_page.locator('[data-phase9-pilot-queue="app-1"]').count() == 1
    assert chromium_page.locator("#phase9-create-backup").is_enabled()
    assert chromium_page.locator("#phase9-restore-backup").is_enabled()
    assert chromium_page.locator("#phase9-deactivate-pilot").is_enabled()

    chromium_page.locator("#phase9-create-backup").click()
    chromium_page.locator("#phase9-restore-backup").click()
    chromium_page.locator("#phase9-deactivate-pilot").click()
    chromium_page.locator('[data-phase9-pilot-queue="app-1"]').click()

    assert chromium_page.evaluate("window.__calls") == [
        ["choose_local_backup"],
        ["choose_local_restore"],
        ["deactivate_real_application_pilot"],
        ["queue_prepared_pilot_application", "app-1"],
    ]


def test_phase9_activation_requires_user_entered_phrase(chromium_page) -> None:
    chromium_page.set_content(
        """
        <div class="privacy-note"></div><div class="eyebrow"></div>
        <section id="dashboard"><div class="banner"></div></section>
        <section id="system"></section><div id="phase8-attention"></div>
        """
    )
    chromium_page.add_script_tag(
        content="""
        window.latestState = null;
        window.__calls = [];
        window.escapeHtml = value => String(value ?? '');
        window.escapeAttr = value => String(value ?? '');
        window.invoke = async (name, ...args) => { window.__calls.push([name, ...args]); return {}; };
        window.render = state => { window.latestState = state; };
        """
    )
    chromium_page.add_script_tag(path=str(PHASE9_JS))
    chromium_page.evaluate(
        "state => window.render(state)",
        {
            "session_state": "idle",
            "distribution": {
                "app_version": "0.1.0",
                "pilot_authorized": True,
                "pilot_session_active": False,
                "real_employer_submission_enabled": False,
                "pilot_confirmation_phrase": "ENABLE MEASURED REAL APPLICATION PILOT",
                "pilot_armed_this_launch": 0,
                "pilot_arm_limit": 5,
                "pilot_policy_revision": "phase9-v1",
                "backup": {"format_version": 1, "local_backups": 0, "restore_pending": False},
            },
            "orchestration": {"attention": []},
        },
    )

    phrase = "ENABLE MEASURED REAL APPLICATION PILOT"
    chromium_page.locator("#phase9-pilot-confirmation").fill(phrase)
    chromium_page.locator("#phase9-activate-pilot").click()
    assert chromium_page.evaluate("window.__calls") == [["activate_real_application_pilot", phrase]]
