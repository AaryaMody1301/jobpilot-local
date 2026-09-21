from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from jobpilot.app.main import create_controller
from jobpilot.domain.states import ApplicationState
from jobpilot.runtime.paths import ManagedPaths


class _FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        self._send(b'''<!doctype html><html><body><form method="post" action="/apply">
        <input data-jobpilot-key="name" data-jobpilot-label="Full name" data-jobpilot-context="orchestration-v1" required>
        <input type="email" data-jobpilot-key="email" data-jobpilot-label="Email" data-jobpilot-context="orchestration-v1" required>
        <button data-jobpilot-submit type="submit">Submit</button></form></body></html>''')

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        self._send(b'<html><body><div data-jobpilot-confirmation="success">Application received</div></body></html>')


class _FakeTailoringStore:
    def __init__(self, run: dict[str, object]) -> None:
        self.run = run

    def get_run(self, run_id: str) -> dict[str, object] | None:
        return dict(self.run) if run_id == self.run["id"] else None


class _FakeTailoring:
    def __init__(self, run: dict[str, object]) -> None:
        self.store = _FakeTailoringStore(run)

    def _stale_reason(self, run: object) -> None:
        return None

    def _verify_run_artifacts(self, run: object) -> None:
        return

    def auto_tailoring_is_current(self) -> bool:
        return True


def _wait(controller: object, application_id: str, expected: str, timeout: float = 20.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = controller.snapshot()  # type: ignore[attr-defined]
        attempt = next(item for item in state["orchestration"]["history"] if item["id"] == application_id)  # type: ignore[index,union-attr]
        if attempt["state"] == expected:
            return state
        time.sleep(0.1)
    raise AssertionError(f"orchestration application did not reach {expected}")


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    target = f"http://127.0.0.1:{server.server_port}/form"
    try:
        with TemporaryDirectory(prefix="jobpilot-orchestration-acceptance-") as temp_dir:
            controller = create_controller(ManagedPaths(Path(temp_dir) / "JobPilotLocal"), sample_item_seconds=0.01)
            try:
                for board in controller.job_store.boards():
                    controller.set_job_board_enabled(str(board["id"]), False)
                controller.import_manual_job({
                    "employer": "orchestration Fixture Co",
                    "title": "Data Analyst",
                    "location": "Surat, India",
                    "workplace_type": "onsite",
                    "employment_type": "permanent_full_time",
                    "source_url": "https://example.invalid/jobs/orchestration-controlled",
                    "apply_url": "https://example.invalid/jobs/orchestration-controlled/apply",
                    "description": "Permanent full-time data analyst role in Surat.",
                })
                job = controller.job_store.jobs()[0]
                attempt = controller.applications.register_discovered_job(job, {
                    **job, "eligibility": "eligible", "hard_reasons": [], "review_reasons": []
                })
                application_id = str(attempt["id"])
                controller.applications.begin_tailoring(application_id)
                run = {
                    "id": "orchestration-controlled-run",
                    "status": "approved",
                    "validation": {"overall_pass": True},
                    "manifest_sha256": "a" * 64,
                    "pdf_sha256": "b" * 64,
                    "master_sha256": "c" * 64,
                    "fact_bank_revision": 1,
                    "model_install_id": "model-fixture",
                    "runtime_install_id": "runtime-fixture",
                    "device_id": "none",
                    "review_context_sha256": "d" * 64,
                }
                fake = _FakeTailoring(run)
                controller.applications.tailoring = fake  # type: ignore[assignment]
                controller.applications.set_tailoring_run(application_id, str(run["id"]))
                controller.applications.finish_tailoring(application_id, run)
                assert controller.applications.attempt(application_id)["state"] == ApplicationState.PREPARED.value
                controller.queue_prepared_controlled_application(application_id, target)
                controller.start()
                state = _wait(controller, application_id, "needs_review")
                questions = [q for q in state["applications"]["open_questions"] if q["application_id"] == application_id]  # type: ignore[index]
                assert {q["question_key"] for q in questions} == {"name", "email"}
                for question in questions:
                    answer = "Candidate Name" if question["question_key"] == "name" else "candidate@example.invalid"
                    controller.approve_application_question(str(question["id"]), answer)
                state = _wait(controller, application_id, "confirmed")
                assert state["orchestration"]["daily"]["confirmed_real"] == 0  # type: ignore[index]
                assert state["orchestration"]["daily"]["confirmed_controlled"] == 1  # type: ignore[index]
                assert state["orchestration"]["daily"]["target_confirmed"] == 50  # type: ignore[index]
                assert state["orchestration"]["real_employer_submission_enabled"] is False  # type: ignore[index]
                assert state["orchestration"]["packages"] >= 2  # answer approval refreshes the immutable package
                controller.stop()
            finally:
                controller.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    print("orchestration end-to-end controlled orchestration acceptance passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
