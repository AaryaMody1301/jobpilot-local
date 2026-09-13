from __future__ import annotations

import json
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

from jobpilot.applications import GreenhouseAdapter
from jobpilot.jobs import fetch_board

_FORM = b"""<!doctype html><html><body>
<h1>Apply for this job</h1>
<form id="application">
<label>First Name*<input name="first_name" required></label>
<label>Email*<input name="email" type="email" required></label>
<label>Resume/CV*<input name="resume" type="file" required></label>
<label>Notice period*<select name="notice" required><option value="">Select</option><option value="30">30 days</option></select></label>
<button type="submit">Submit application</button>
</form>
<script>
document.getElementById('application').addEventListener('submit', event => {
  event.preventDefault();
  document.body.innerHTML = '<div data-jobpilot-confirmation="success">Thank you for applying. Application submitted.</div>';
});
</script>
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(_FORM)))
        self.end_headers()
        self.wfile.write(_FORM)

    def log_message(self, format: str, *args: object) -> None:
        return


def _controlled_acceptance(browser, root: Path) -> dict[str, object]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    resume = root / "resume.txt"
    resume.write_text("controlled resume fixture", encoding="utf-8")
    page = browser.new_page()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/greenhouse"
        adapter = GreenhouseAdapter(page, allow_controlled_submit=True)
        inspection = adapter.inspect(url)
        assert inspection.supported
        assert inspection.submit_controls == 1
        assert {field.name for field in inspection.fields if field.required} == {"first_name", "email", "resume", "notice"}
        adapter.fill({
            "first_name": "Controlled",
            "email": "controlled@example.invalid",
            "resume": str(resume),
            "notice": "30",
        })
        adapter.submit()
        confirmation = adapter.confirm()
        assert confirmation.confirmed
        return {"controlled_supported": True, "controlled_confirmed": True}
    finally:
        page.close()
        server.shutdown()
        server.server_close()
        thread.join(5)


def _live_recognition(browser) -> dict[str, object]:
    jobs = fetch_board("greenhouse", "GitLab", "gitlab")
    assert jobs, "verified GitLab Greenhouse board returned no current jobs"
    failures: list[str] = []
    for job in jobs[:6]:
        page = browser.new_page()
        try:
            url = str(job["source_url"])
            adapter = GreenhouseAdapter(page)
            inspection = adapter.inspect(url)
            if inspection.fields and inspection.submit_controls == 1:
                try:
                    adapter.submit()
                except RuntimeError as exc:
                    assert "disabled for live employer pages" in str(exc)
                else:
                    raise AssertionError("live Greenhouse submit guard did not fail closed")
                return {
                    "live_url": url,
                    "live_fields": len(inspection.fields),
                    "live_supported": inspection.supported,
                    "live_blockers": list(inspection.blockers),
                    "live_write_guard": True,
                }
            failures.append(f"{url}: {','.join(inspection.blockers) or 'unrecognized'}")
        except Exception as exc:
            failures.append(f"{job.get('source_url')}: {type(exc).__name__}: {exc}")
        finally:
            page.close()
        time.sleep(0.25)
    raise AssertionError("no current GitLab Greenhouse form was recognized read-only: " + " | ".join(failures))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="jobpilot-phase7a-") as temp_dir, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            result = {
                "provider": "greenhouse",
                **_controlled_acceptance(browser, Path(temp_dir)),
                **_live_recognition(browser),
            }
        finally:
            browser.close()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
