from __future__ import annotations

import json
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from jobpilot.applications import GreenhouseAdapter, LeverAdapter
from jobpilot.jobs import fetch_board

_FORM = b"""<!doctype html><html><body>
<h1>Submit your application</h1>
<form id="application">
<label>Full name*<input name="name" required></label>
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


def _controlled(browser: Any, adapter_type: type, root: Path) -> dict[str, object]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    resume = root / f"{adapter_type.provider}-resume.txt"
    resume.write_text("controlled resume fixture", encoding="utf-8")
    page = browser.new_page()
    try:
        adapter = adapter_type(page, allow_controlled_submit=True)
        inspection = adapter.inspect(f"http://127.0.0.1:{server.server_address[1]}/{adapter_type.provider}")
        assert inspection.supported and inspection.submit_controls == 1
        assert {field.name for field in inspection.fields if field.required} == {"name", "email", "resume", "notice"}
        adapter.fill({"name": "Controlled Candidate", "email": "controlled@example.invalid", "resume": str(resume), "notice": "30"})
        adapter.submit()
        assert adapter.confirm().confirmed
        return {"controlled_supported": True, "controlled_confirmed": True}
    finally:
        page.close()
        server.shutdown(); server.server_close(); thread.join(5)


def _live(browser: Any, adapter_type: type, employer: str, token: str, url_key: str) -> dict[str, object]:
    jobs = fetch_board(adapter_type.provider, employer, token)
    assert jobs, f"verified {employer} {adapter_type.provider} board returned no current jobs"
    failures: list[str] = []
    for job in jobs[:8]:
        url = str(job.get(url_key) or "")
        if not url:
            continue
        page = browser.new_page()
        try:
            adapter = adapter_type(page)
            inspection = adapter.inspect(url)
            if inspection.fields and inspection.submit_controls == 1:
                try:
                    adapter.submit()
                except RuntimeError as exc:
                    assert "disabled for live employer pages" in str(exc)
                else:
                    raise AssertionError(f"live {adapter_type.provider} submit guard did not fail closed")
                return {
                    "live_url": url,
                    "live_fields": len(inspection.fields),
                    "live_supported": inspection.supported,
                    "live_blockers": list(inspection.blockers),
                    "live_write_guard": True,
                }
            failures.append(f"{url}: {','.join(inspection.blockers) or 'unrecognized'}")
        except Exception as exc:
            failures.append(f"{url}: {type(exc).__name__}: {exc}")
        finally:
            page.close()
        time.sleep(0.25)
    raise AssertionError(f"no current {employer} {adapter_type.provider} form was recognized read-only: " + " | ".join(failures))


def main() -> int:
    providers = (
        (GreenhouseAdapter, "GitLab", "gitlab", "source_url"),
        (LeverAdapter, "Nium", "nium", "apply_url"),
    )
    with tempfile.TemporaryDirectory(prefix="jobpilot-phase7-") as temp_dir, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            results = {}
            for adapter_type, employer, token, url_key in providers:
                results[adapter_type.provider] = {
                    **_controlled(browser, adapter_type, Path(temp_dir)),
                    **_live(browser, adapter_type, employer, token, url_key),
                }
        finally:
            browser.close()
    print(json.dumps(results, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
