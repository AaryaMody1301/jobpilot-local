from pathlib import Path

import pytest

from jobpilot.applications.controlled import inspect_controlled_form


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"


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


def test_read_only_fixture_inspection_does_not_submit(chromium_page) -> None:
    inspection = inspect_controlled_form(chromium_page, FIXTURES / "application_basic.html")
    assert inspection.supported
    assert inspection.submit_controls == 1
    assert {field.name for field in inspection.fields} == {"first_name", "email", "resume", "note"}
    assert {field.name for field in inspection.fields if field.required} == {"first_name", "email", "resume"}
    assert chromium_page.evaluate("window.__submitCount") == 0


def test_fixture_captcha_blocks_support_without_submit(chromium_page) -> None:
    inspection = inspect_controlled_form(chromium_page, FIXTURES / "application_captcha.html")
    assert not inspection.supported
    assert "captcha" in inspection.blockers
