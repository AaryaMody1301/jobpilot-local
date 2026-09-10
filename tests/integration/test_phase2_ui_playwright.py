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
            "roles": ["data analyst"], "target_experience_min_years": 2, "target_experience_max_years": 5,
            "india_office_cities": ["Surat"], "remote_origin_city": "Surat", "remote_origin_country": "India",
            "remote_must_allow_origin": True, "relocation_outside_india": True, "require_overseas_sponsorship": True,
            "salary_minimum": None, "notice_period_days": 30, "employment_types": ["permanent_full_time"],
            "excluded_employers": ["Brentwood Industries"],
        },
        "sample_work": [], "sample_counts": {"pending": 0, "running": 0, "done": 0, "failed": 0, "blocked": 0},
        "recovery": {"crashed_sessions": 0, "requeued_work": 0, "uncertain_applications": 0},
        "activity": [], "data_root": "C:\\fixture\\JobPilotLocal",
        "resume": {
            "master": {"id": "resume-abc", "original_name": "resume.tex", "sha256": "a" * 64, "imported_at": "now", "stored_relpath": "documents/master/resume-abc/source.tex"},
            "integrity": "verified",
            "baseline": {"status": "compiled", "page_count": 1, "compiler_version": "0.17.0", "offline_verified": False, "compile_error": None, "source_metrics": {"external_inputs": []}},
            "template_map_status": "candidate",
            "regions": [{"id": "region-abc-001", "section_name": "Experience", "line_start": 5, "line_end": 5, "display_text": "Built reliable analytics.", "editable": 0}],
            "facts": [{"id": "fact-abc-001", "current_version": 1, "current_status": "candidate", "current_category": "experience_bullet", "value_text": "Quoted \"evidence\" <safe>", "source_document_id": "resume-abc", "source_name": "resume.tex", "source_ref": {"line_start": 5}}],
            "fact_counts": {"candidate": 1, "approved": 0, "rejected": 0},
            "fact_bank_revision": 1,
            "fact_categories": ["experience_bullet", "other"],
            "supporting_documents": [],
            "tectonic": {"installed": True, "managed": True, "version": "0.17.0", "integrity": "verified", "path": "C:\\fixture\\tectonic.exe", "download_bytes": 21060223},
            "onboarding_ready": False,
        },
    }


def test_resume_view_is_local_review_gate_and_escapes_fact_values(chromium_page) -> None:
    state = _state()
    chromium_page.add_init_script(
        """
        window.__calls = [];
        window.pywebview = { api: {
          get_state: async () => window.__fixtureState,
          set_template_region_editable: async (id, value) => { window.__calls.push(['region', id, value]); window.__fixtureState.resume.regions[0].editable = value ? 1 : 0; return window.__fixtureState; },
          confirm_template_map: async () => window.__fixtureState,
          revise_fact: async () => window.__fixtureState,
          set_fact_status: async () => window.__fixtureState,
          create_fact: async () => window.__fixtureState,
          choose_master_resume: async () => window.__fixtureState,
          choose_supporting_document: async () => window.__fixtureState,
          install_tectonic: async () => window.__fixtureState,
          compile_master_resume: async () => window.__fixtureState,
          start: async () => window.__fixtureState,
          pause: async () => window.__fixtureState,
          stop: async () => window.__fixtureState,
          reset_sample_work: async () => window.__fixtureState,
          save_targeting: async () => window.__fixtureState
        }};
        """
    )
    with local_ui_server() as url:
        chromium_page.goto(url)
        chromium_page.evaluate("value => window.__fixtureState = value", state)
        chromium_page.evaluate("window.dispatchEvent(new Event('pywebviewready'))")
        chromium_page.locator("button[data-view='resume']").click()
        assert chromium_page.locator("#page-title").inner_text() == "Resume & facts"
        assert chromium_page.locator("#baseline-summary").inner_text().find("Offline verified: no") >= 0
        assert chromium_page.locator(".fact-value").input_value() == 'Quoted "evidence" <safe>'
        assert chromium_page.locator("script").count() == 1
        chromium_page.locator("#template-regions input").check()
        chromium_page.wait_for_function("window.__calls.length === 1")
        assert chromium_page.evaluate("window.__calls[0]") == ["region", "region-abc-001", True]
