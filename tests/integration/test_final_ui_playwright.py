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
        chromium_page.locator("#distribution-panel").wait_for(state="attached")
        chromium_page.locator("#orchestration-panel").wait_for(state="attached")

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


def test_active_pilot_arming_is_available_from_applications_attention_lane(chromium_page) -> None:
    state = _state(pilot_active=True)
    state["orchestration"]["attention"] = [
        {
            "id": "app-1",
            "state": "prepared",
            "employer": "Example",
            "title": "Data Engineer",
            "eligibility": {"hard_reasons": [], "review_reasons": []},
            "attention_kind": "pilot_activation_required",
            "last_reason": "fresh package prepared",
            "live_form": {
                "read_only": True,
                "supported": True,
                "blockers": [],
                "submit_controls": 1,
            },
        }
    ]
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
        chromium_page.evaluate("state => { window.__fixtureState = state; render(state); showView('history'); }", state)

        arm = chromium_page.locator('[data-pilot-queue="app-1"]')
        assert arm.count() == 1
        arm.click()
        chromium_page.wait_for_function("window.__calls.length === 1")
        assert chromium_page.evaluate("window.__calls") == [
            ["queue_prepared_pilot_application", "app-1"],
        ]


def test_job_and_application_workspace_filters_and_saves_local_follow_up(chromium_page) -> None:
    state = _state()
    state["jobs"] = {
        "counts": {"eligible": 1, "review": 0, "ineligible": 0},
        "approved_evidence_facts": 3,
        "boards": [],
        "items": [{
            "id": "job-1",
            "provider": "lever",
            "employer": "Acme",
            "title": "Data Engineer",
            "location": "Surat, India",
            "workplace_type": "onsite",
            "employment_type": "permanent_full_time",
            "source_url": "https://jobs.lever.co/acme/job-1",
            "apply_url": "https://jobs.lever.co/acme/job-1/apply",
            "description": "Required SQL and Python experience.",
            "published_at": "2026-09-20T00:00:00Z",
            "last_seen_at": "2026-09-21T00:00:00Z",
            "compensation_text": "INR 1800000 - 2400000",
            "application_deadline": "2026-10-15",
            "eligibility": "eligible",
            "hard_reasons": [],
            "review_reasons": [],
            "required_requirements": ["Required SQL and Python experience."],
            "preferred_requirements": [],
            "matched_required": ["Required SQL and Python experience."],
            "matched_preferred": [],
            "supported_terms": ["python", "sql"],
            "score": 95,
            "score_reasons": {"role": 40, "required_evidence": 35, "preferred_evidence": 5, "eligibility_clarity": 15},
        }],
    }
    state["orchestration"]["history"] = [{
        "id": "app-1",
        "state": "prepared",
        "provider": "lever",
        "employer": "Acme",
        "title": "Data Engineer",
        "location": "Surat, India",
        "source_url": "https://jobs.lever.co/acme/job-1",
        "apply_url": "https://jobs.lever.co/acme/job-1/apply",
        "description": "Required SQL and Python experience.",
        "compensation_text": "INR 1800000 - 2400000",
        "application_deadline": "2026-10-15",
        "created_at": "2026-09-21T00:00:00Z",
        "submit_started_at": None,
        "confirmed_at": None,
        "last_reason": "immutable package prepared",
        "follow_up_at": None,
        "notes": "",
        "next_action": "",
        "tailoring_run_id": "tailor-1",
        "tailoring_status": "approved",
        "tailored_pdf_relpath": "artifacts/tailor-1.pdf",
        "tailored_pdf_sha256": "a" * 64,
        "package_id": "package-1",
        "package_manifest_sha256": "b" * 64,
        "eligibility": {"hard_reasons": [], "review_reasons": []},
        "live_form": {},
    }]
    state["orchestration"]["counts"] = {"prepared": 1}

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
        chromium_page.evaluate("state => { window.__fixtureState = state; render(state); showView('jobs'); }", state)

        chromium_page.locator("#job-search").fill("Acme")
        assert chromium_page.locator('[data-job-select="job-1"]').count() == 1
        assert "INR 1800000 - 2400000" in chromium_page.locator("#job-detail").inner_text()
        assert "Required SQL and Python experience." in chromium_page.locator("#job-detail").inner_text()

        chromium_page.locator('[data-view="history"]').click()
        assert chromium_page.locator('[data-application-select="app-1"]').count() == 1
        assert chromium_page.locator('[data-application-preview="tailor-1"]').count() == 1
        chromium_page.locator("#application-follow-up").fill("2026-10-01")
        chromium_page.locator("#application-next-action").fill("Follow up with recruiter")
        chromium_page.locator("#application-notes").fill("Screening completed.")
        chromium_page.locator("#application-workspace-form button[type='submit']").click()
        chromium_page.wait_for_function("window.__calls.some(call => call[0] === 'update_application_workspace')")
        call = chromium_page.evaluate("window.__calls.find(call => call[0] === 'update_application_workspace')")
        assert call == [
            "update_application_workspace",
            "app-1",
            "2026-10-01",
            "Screening completed.",
            "Follow up with recruiter",
        ]
