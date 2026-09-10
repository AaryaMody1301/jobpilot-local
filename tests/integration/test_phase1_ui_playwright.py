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
        page = browser.new_page()
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


def _resume_state() -> dict:
    return {
        "master": None,
        "integrity": "missing",
        "baseline": None,
        "template_map_status": "missing",
        "regions": [],
        "facts": [],
        "fact_counts": {"candidate": 0, "approved": 0, "rejected": 0},
        "fact_bank_revision": 0,
        "fact_categories": ["experience_bullet", "other", "skill"],
        "supporting_documents": [],
        "tectonic": {"installed": False, "managed": True, "version": "0.17.0", "integrity": "not installed", "download_bytes": 21060223},
        "onboarding_ready": False,
    }


def _state() -> dict:
    return {
        "phase": 2,
        "development_mode": True,
        "session_id": "fixture-session",
        "session_state": "idle",
        "worker_alive": False,
        "target_confirmed_applications": 50,
        "confirmed_applications_today": 0,
        "onboarding_busy": None,
        "targeting": {
            "roles": ["data analyst", "data engineer", "analytics engineer"],
            "target_experience_min_years": 2,
            "target_experience_max_years": 5,
            "india_office_cities": ["Surat"],
            "remote_origin_city": "Surat",
            "remote_origin_country": "India",
            "remote_must_allow_origin": True,
            "relocation_outside_india": True,
            "require_overseas_sponsorship": True,
            "salary_minimum": None,
            "notice_period_days": 30,
            "employment_types": ["permanent_full_time"],
            "excluded_employers": ["Brentwood Industries"],
        },
        "sample_work": [
            {"id": "sample-001", "label": "SAMPLE - lifecycle", "state": "pending", "lease_owner": None, "updated_at": "now"}
        ],
        "sample_counts": {"pending": 1, "running": 0, "done": 0, "failed": 0, "blocked": 0},
        "recovery": {"crashed_sessions": 0, "requeued_work": 0, "uncertain_applications": 0},
        "activity": [],
        "data_root": "C:\\fixture\\JobPilotLocal",
        "resume": _resume_state(),
    }


def test_local_ui_navigation_and_bridge_contract(chromium_page) -> None:
    state = _state()
    chromium_page.add_init_script(
        """
        window.__calls = [];
        window.pywebview = { api: {
          get_state: async () => window.__fixtureState,
          start: async () => { window.__calls.push('start'); return window.__fixtureState; },
          pause: async () => window.__fixtureState,
          stop: async () => window.__fixtureState,
          reset_sample_work: async () => window.__fixtureState,
          save_targeting: async (value) => { window.__calls.push(['save', value.notice_period_days, value.salary_minimum, value.employment_types, value.remote_must_allow_origin]); return window.__fixtureState; }
        }};
        """
    )
    with local_ui_server() as url:
        chromium_page.goto(url)
        chromium_page.evaluate("value => window.__fixtureState = value", state)
        chromium_page.evaluate("window.dispatchEvent(new Event('pywebviewready'))")
        chromium_page.wait_for_function("document.getElementById('session-badge').textContent === 'idle'")

        assert chromium_page.locator("text=Local evaluation mode.").is_visible()
        assert chromium_page.locator("text=SAMPLE - lifecycle").is_visible()
        assert chromium_page.locator("text=Confirmed today").is_visible()
        chromium_page.locator("button[data-view='settings']").click()
        assert chromium_page.locator("#page-title").inner_text() == "Targeting"
        assert chromium_page.locator("#notice-days").input_value() == "30"
        chromium_page.locator("#notice-days").fill("45")
        chromium_page.locator("#salary-minimum").fill("900000")
        chromium_page.locator("#employment-types").fill("permanent_full_time")
        assert chromium_page.locator("#remote-origin-required").is_checked()
        chromium_page.locator("#targeting-form button[type='submit']").click()
        chromium_page.wait_for_function("window.__calls.length === 1")
        assert chromium_page.evaluate("window.__calls[0]") == ["save", 45, 900000, ["permanent_full_time"], True]
