from __future__ import annotations

import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from jobpilot.app.phase6_main import create_controller
from jobpilot.runtime.paths import ManagedPaths


class FixtureHandler(BaseHTTPRequestHandler):
    flaky_gets = 0
    active_posts = 0
    max_active_posts = 0
    lock = threading.Lock()

    def log_message(self, format: str, *args: object) -> None:
        return

    @staticmethod
    def _form(action: str, *, extra: str = "") -> bytes:
        return f'''<!doctype html><html><body><form method="post" action="{action}">
        <input data-jobpilot-key="name" data-jobpilot-label="Full name" data-jobpilot-context="candidate-core-v1" required>
        <input type="email" data-jobpilot-key="email" data-jobpilot-label="Email" data-jobpilot-context="candidate-core-v1" required>
        {extra}<button data-jobpilot-submit type="submit">Submit</button></form></body></html>'''.encode()

    def _send(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/flaky":
            with self.lock:
                type(self).flaky_gets += 1
                first = type(self).flaky_gets == 1
            if first:
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
        if self.path == "/captcha":
            self._send(b'<html><body><div data-jobpilot-block="captcha">CAPTCHA</div></body></html>')
            return
        extra = ""
        if self.path == "/unknown":
            extra = '<input data-jobpilot-key="favorite_color" data-jobpilot-label="Favorite color" data-jobpilot-context="role-specific-v1" required>'
        if self.path in {"/success", "/known", "/unknown", "/flaky", "/uncertain"}:
            self._send(self._form(self.path, extra=extra))
            return
        self._send(b"not found", 404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        with self.lock:
            type(self).active_posts += 1
            type(self).max_active_posts = max(type(self).max_active_posts, type(self).active_posts)
        try:
            time.sleep(0.1)
            if self.path == "/uncertain":
                self._send(b"<html><body>Submission received without a positive marker.</body></html>")
            else:
                self._send(b'<html><body><div data-jobpilot-confirmation="success">Application received</div></body></html>')
        finally:
            with self.lock:
                type(self).active_posts -= 1


def _attempt(state: dict[str, object], identity: str) -> dict[str, object]:
    return next(item for item in state["applications"]["attempts"] if item["job_identity"] == identity)  # type: ignore[index,union-attr]


def _wait(controller: object, predicate: object, timeout: float = 15.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = controller.snapshot()  # type: ignore[attr-defined]
        if predicate(state):  # type: ignore[operator]
            return state
        time.sleep(0.1)
    raise AssertionError("controlled Phase 6 fixture condition timed out")


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with TemporaryDirectory(prefix="jobpilot-phase6-acceptance-") as temp_dir:
            paths = ManagedPaths(Path(temp_dir) / "JobPilotLocal")
            controller = create_controller(paths, sample_item_seconds=0.01)
            try:
                controller.queue_controlled_application("fixture-success", base + "/success")
                controller.start()
                state = _wait(controller, lambda s: _attempt(s, "fixture-success")["state"] == "needs_review")
                questions = [q for q in state["applications"]["open_questions"] if q["job_identity"] == "fixture-success"]  # type: ignore[index]
                assert {q["question_key"] for q in questions} == {"name", "email"}
                for question in questions:
                    answer = "Candidate Name" if question["question_key"] == "name" else "candidate@example.invalid"
                    controller.approve_application_question(question["id"], answer)
                _wait(controller, lambda s: _attempt(s, "fixture-success")["state"] == "confirmed")

                controller.queue_controlled_application("fixture-unknown", base + "/unknown")
                controller.queue_controlled_application("fixture-known", base + "/known")
                state = _wait(controller, lambda s: _attempt(s, "fixture-unknown")["state"] == "needs_review" and _attempt(s, "fixture-known")["state"] == "confirmed")
                assert any(q["question_key"] == "favorite_color" for q in state["applications"]["open_questions"])  # type: ignore[index]

                controller.queue_controlled_application("fixture-captcha", base + "/captcha")
                controller.queue_controlled_application("fixture-flaky", base + "/flaky")
                controller.queue_controlled_application("fixture-uncertain", base + "/uncertain")
                state = _wait(
                    controller,
                    lambda s: _attempt(s, "fixture-captcha")["state"] == "blocked"
                    and _attempt(s, "fixture-flaky")["state"] == "confirmed"
                    and _attempt(s, "fixture-uncertain")["state"] == "uncertain",
                    timeout=25.0,
                )
                assert int(_attempt(state, "fixture-flaky")["retry_count"]) >= 1
                before = len(state["applications"]["attempts"])  # type: ignore[index]
                controller.queue_controlled_application("fixture-known", base + "/known")
                after = len(controller.snapshot()["applications"]["attempts"])
                assert before == after
                assert FixtureHandler.max_active_posts == 1
                assert any(paths.browser_profile.iterdir())
                controller.stop()
                assert controller.snapshot()["applications"]["worker"]["alive"] is False
            finally:
                controller.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    print("Phase 6 controlled localhost application acceptance passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
