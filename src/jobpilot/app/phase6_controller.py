from __future__ import annotations

from typing import Any

from jobpilot.app.phase5_controller import Phase5ApplicationController
from jobpilot.applications import ApplicationJournal, ApplicationWorker
from jobpilot.domain.states import SESSION_MACHINE, SessionState


class Phase6ApplicationController(Phase5ApplicationController):
    """Controlled localhost form engine. Real employer submission remains disabled."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.applications = ApplicationJournal(self.database)
        recovered = self.applications.recover_pre_submit()
        self.recovery["requeued_controlled_applications"] = recovered
        self._application_worker: ApplicationWorker | None = None
        self.database.record_foundation_activity(
            self.session_id,
            "phase6_ready",
            "Phase 6 controlled localhost application engine loaded; real employer submissions remain disabled",
        )

    def start(self) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            if self._onboarding_busy is not None:
                raise RuntimeError(f"finish or cancel {self._onboarding_busy} before starting the session")
            if self._state is SessionState.RUNNING:
                return self.snapshot()
            SESSION_MACHINE.require_transition(self._state, SessionState.RUNNING)
            if self._application_worker is None or not self._application_worker.status()["alive"]:
                self._application_worker = ApplicationWorker(self.paths, self.applications, self.session_id)
                self._application_worker.start()
            else:
                self._application_worker.resume()
            self._state = SessionState.RUNNING
            self.database.set_runtime_session_state(self.session_id, self._state)
            self.database.record_foundation_activity(self.session_id, "start", "Single controlled application worker started or resumed")
            return self.snapshot()

    def pause(self) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            if self._state is SessionState.PAUSED:
                return self.snapshot()
            SESSION_MACHINE.require_transition(self._state, SessionState.PAUSED)
            if self._application_worker is not None:
                self._application_worker.pause()
            self._state = SessionState.PAUSED
            self.database.set_runtime_session_state(self.session_id, self._state)
            self.database.record_foundation_activity(self.session_id, "pause", "No new controlled applications will be claimed")
            return self.snapshot()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            if self._state is SessionState.IDLE:
                return self.snapshot()
            SESSION_MACHINE.require_transition(self._state, SessionState.STOPPING)
            self._state = SessionState.STOPPING
            self.database.set_runtime_session_state(self.session_id, self._state)
            worker = self._application_worker
        if worker is not None:
            worker.stop(60.0)
        with self._lock:
            self._application_worker = None
            SESSION_MACHINE.require_transition(self._state, SessionState.IDLE)
            self._state = SessionState.IDLE
            self.database.set_runtime_session_state(self.session_id, self._state)
            self.database.record_foundation_activity(self.session_id, "stop", "Controlled application worker stopped; app remains open")
            return self.snapshot()

    def queue_controlled_application(self, job_identity: str, target_url: str) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            attempt = self.applications.queue_controlled(job_identity, target_url)
            self.database.record_foundation_activity(
                self.session_id,
                "controlled_application_queue",
                f"Controlled localhost fixture queued or deduplicated: {attempt['job_identity']}",
            )
            return self.snapshot()

    def approve_application_question(self, question_id: str, answer: str) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            self.applications.resolve_question(question_id, answer)
            self.database.record_foundation_activity(
                self.session_id,
                "application_answer_approved",
                "Approved an exact-context controlled-form answer locally",
            )
            return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = super().snapshot()
            worker = self._application_worker.status() if self._application_worker is not None else {
                "alive": False,
                "paused": False,
                "current_application_id": None,
                "last_error": None,
            }
            state["phase"] = 6
            state["worker_alive"] = bool(worker["alive"])
            state["tailoring"]["phase6_controlled_forms_enabled"] = True
            state["applications"] = {
                **self.applications.summary(),
                "worker": worker,
                "controlled_fixture_only": True,
                "real_employer_submission_enabled": False,
            }
            return state

    def close(self) -> None:
        with self._lock:
            worker = self._application_worker
        if worker is not None:
            worker.stop(60.0)
        with self._lock:
            self._application_worker = None
        super().close()
