"""Controlled loopback forms only; never contact or submit to an employer."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

import pytest

from jobpilot.applications.platforms import LeverAdapter


@pytest.fixture
def browser():
    playwright = pytest.importorskip("playwright.sync_api")
    try:
        driver = playwright.sync_playwright().start()
    except Exception as exc:
        pytest.skip(f"Playwright driver unavailable: {exc}")
    try:
        try:
            opened = driver.chromium.launch(headless=True)
        except Exception as exc:
            pytest.skip(f"Playwright Chromium unavailable: {exc}")
        try:
            yield opened
        finally:
            opened.close()
    finally:
        driver.stop()


@pytest.fixture
def local_forms():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - stdlib callback
            if self.path == "/form":
                body = """<!doctype html><form id="application">
                <label>Full name*<input name="name" required></label>
                <label for="resume">Resume*</label><input id="resume" name="resume" type="file" required style="display:none">
                <button type="submit">Submit application</button></form>
                <script>document.querySelector('form').onsubmit = event => {
                  event.preventDefault();
                  if (!document.querySelector('[name=resume]').files.length) return;
                  setTimeout(() => { document.body.innerHTML =
                    '<div data-jobpilot-confirmation="success">Application submitted.</div>'; }, 3500);
                };</script>"""
            else:
                blocker = '<div id="captcha">Complete verification</div>' if self.path == "/blocked" else ""
                body = f'<!doctype html>{blocker}<iframe title="Application" src="/form"></iframe>'
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_hidden_resume_upload_in_iframe_and_delayed_confirmation(browser, local_forms, tmp_path: Path) -> None:
    resume = tmp_path / "controlled-resume.pdf"
    resume.write_bytes(b"controlled fixture")
    page = browser.new_page()
    try:
        adapter = LeverAdapter(page, allow_controlled_submit=True)
        inspection = adapter.inspect(local_forms + "/iframe")
        assert inspection.supported and {field.name for field in inspection.fields if field.required} == {"name", "resume"}
        adapter.fill({"name": "Controlled Candidate", "resume": str(resume)})
        adapter.submit()
        assert adapter.confirm().confirmed
    finally:
        page.close()


def test_outer_frame_blocker_remains_a_submit_blocker(browser, local_forms) -> None:
    page = browser.new_page()
    try:
        adapter = LeverAdapter(page, allow_controlled_submit=True)
        inspection = adapter.inspect(local_forms + "/blocked")
        assert not inspection.supported and "captcha" in inspection.blockers
        with pytest.raises(RuntimeError, match="blocker"):
            adapter.submit()
    finally:
        page.close()
