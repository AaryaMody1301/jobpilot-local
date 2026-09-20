from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

import pytest


ROOT = Path(__file__).resolve().parents[2]
UI_DIR = ROOT / "src" / "jobpilot" / "ui"


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


@contextmanager
def local_ui_server():
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(UI_DIR), **kwargs)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/index.html"
    finally:
        server.shutdown()
        thread.join(2)
        server.server_close()


def _state(*, pilot_active: bool = False) -> dict:
    return {
        "session_state": "idle",
        "onboarding_busy": None,
        "confirmed_applications_today": 0,
        "activity": [],
        "data_root": r"C:\fixture\JobPilotLocal",
        "resume": {"onboarding_ready": False},
        "model": None,
        "tailoring": None,
        "jobs": {
            "counts": {"eligible": 0, "review": 0, "ineligible": 0},
            "approved_evidence_facts": 0,
            "boards": [],
            "items": [],
        },
        "orchestration": {
            "daily": {
                "local_date": "2026-09-20",
                "confirmed_real": 0,
                "target_confirmed": 50,
                "remaining_to_target": 50,
                "confirmed_controlled": 0,
            },
            "counts": {},
            "attention": [],
            "history": [],
            "packages": 0,
            "worker": {
                "alive": False,
                "paused": False,
                "current_application_id": None,
                "status": "Idle",
                "last_error": None,
            },
        },
        "distribution": {
            "app_version": "0.1.2",
            "pilot_authorized": True,
            "pilot_session_active": pilot_active,
            "real_employer_submission_enabled": pilot_active,
            "pilot_confirmation_phrase": "ENABLE MEASURED REAL APPLICATION PILOT",
            "pilot_armed_this_launch": 0,
            "pilot_arm_limit": 5,
            "pilot_policy_revision": "phase9-v1",
            "backup": {"format_version": 1, "local_backups": 0, "restore_pending": False},
        },
    }


def test_final_shell_has_current_product_ui_without_development_fixture_controls(chromium_page) -> None:
    with local_ui_server() as url:
        chromium_page.goto(url)
        chromium_page.wait_for_selector("#distribution-panel")
        chromium_page.wait_for_selector("#orchestration-panel")

        body = chromium_page.locator("body").inner_text()
        assert "PHASE 4" not in body
        assert "PHASE 5" not in body
        assert "PHASE 6" not in body
        assert "PHASE 8" not in body
        assert "PHASE 9" not in body
        assert chromium_page.locator("#application-queue-form").count() == 0
        assert chromium_page.locator("#job-discover").count() == 1
        assert chromium_page.locator("#distribution-panel").count() == 1
        assert chromium_page.locator("#orchestration-panel").count() == 1
        assert chromium_page.locator("script").count() == 1
        assert chromium_page.locator('[data-view="dashboard"]').get_attribute("aria-current") == "page"

        chromium_page.locator('[data-view="history"]').click()
        assert chromium_page.locator("#page-title").inner_text() == "Applications"
        assert chromium_page.locator('[data-view="history"]').get_attribute("aria-current") == "page"
        assert chromium_page.locator('[data-view="dashboard"]').get_attribute("aria-current") is None


def test_measured_pilot_actions_render_in_final_shell_and_require_exact_phrase(chromium_page) -> None:
    state = _state()
    chromium_page.add_init_script(
        """
        window.__calls = [];
        window.pywebview = { api: new Proxy({}, {
          get: (_, name) => async (...args) => {
            window.__calls.push([String(name), ...args]);
            return window.__fixtureState;
          }
        })};
        """
    )
    with local_ui_server() as url:
        chromium_page.goto(url)
        chromium_page.evaluate("state => { window.__fixtureState = state; render(state); showView('system'); }", state)

        phrase = "ENABLE MEASURED REAL APPLICATION PILOT"
        confirmation = chromium_page.locator("#pilot-confirmation")
        activate = chromium_page.locator("#pilot-activate")

        assert activate.is_disabled()
        confirmation.fill("enable")
        assert activate.is_disabled()
        confirmation.fill(phrase)
        assert activate.is_enabled()

        chromium_page.locator("#distribution-create-backup").click()
        chromium_page.locator("#distribution-restore-backup").click()
        activate.click()

        chromium_page.wait_for_function("window.__calls.length === 3")
        assert chromium_page.evaluate("window.__calls") == [
            ["choose_local_backup"],
            ["choose_local_restore"],
            ["activate_real_application_pilot", phrase],
        ]
