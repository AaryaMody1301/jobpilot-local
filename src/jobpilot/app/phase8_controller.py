from __future__ import annotations

import os
import threading
import time
from typing import Any

from jobpilot.app.phase6_controller import Phase6ApplicationController
from jobpilot.applications.platforms import AshbyAdapter, GreenhouseAdapter, LeverAdapter
from jobpilot.domain.states import ApplicationState, SessionState
from jobpilot.jobs import assess_job, dedupe_jobs, fetch_board
from jobpilot.orchestration import Phase8ApplicationJournal


class Phase8ApplicationController(Phase6ApplicationController):
    """Explicit-session end-to-end orchestration. Real employer writes remain disabled."""

    DISCOVERY_INTERVAL_SECONDS = 15 * 60

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.applications = Phase8ApplicationJournal(self.database, self.tailoring)
        self.recovery["requeued_phase8_controlled_applications"] = self.applications.recover_pre_submit()
        self._orchestration_stop = threading.Event()
        self._orchestration_paused = threading.Event()
        self._orchestration_thread: threading.Thread | None = None
        self._orchestration_current_id: str | None = None
        self._orchestration_last_error: str | None = None
        self._orchestration_status_text = "Idle"
        self._next_discovery_at = 0.0
        self.database.record_foundation_activity(
            self.session_id,
            "phase8_ready",
            "Phase 8 end-to-end orchestration loaded; real employer submissions remain disabled until Phase 9",
        )

    def start(self) -> dict[str, Any]:
        with self._lock:
            self._orchestration_stop.clear()
            self._orchestration_paused.clear()
        super().start()
        with self._lock:
            if self._orchestration_thread is None or not self._orchestration_thread.is_alive():
                self._orchestration_thread = threading.Thread(
                    target=self._orchestration_loop,
                    name="jobpilot-orchestration-worker",
                    daemon=True,
                )
                self._orchestration_thread.start()
            self._orchestration_status_text = "Running"
            return self.snapshot()

    def pause(self) -> dict[str, Any]:
        self._orchestration_paused.set()
        with self._lock:
            self._orchestration_status_text = "Paused after current safe item"
        return super().pause()

    def stop(self) -> dict[str, Any]:
        self._orchestration_stop.set()
        self._orchestration_paused.clear()
        self.models.cancel_current()
        thread = self._orchestration_thread
        if thread is not None:
            thread.join(60.0)
        with self._lock:
            if thread is None or not thread.is_alive():
                self._orchestration_thread = None
            self._orchestration_current_id = None
            self._orchestration_status_text = "Idle"
        return super().stop()

    def close(self) -> None:
        self._orchestration_stop.set()
        self._orchestration_paused.clear()
        self.models.cancel_current()
        thread = self._orchestration_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(60.0)
        with self._lock:
            self._orchestration_thread = None
            self._orchestration_current_id = None
        super().close()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = super().snapshot()
            thread = self._orchestration_thread
            state["phase"] = 8
            state["tailoring"]["phase8_orchestration_enabled"] = True
            state["tailoring"]["employer_submission_enabled"] = False
            state["applications"]["real_employer_submission_enabled"] = False
            state["orchestration"] = {
                **self.applications.orchestration_summary(),
                "worker": {
                    "alive": bool(thread and thread.is_alive()),
                    "paused": self._orchestration_paused.is_set(),
                    "current_application_id": self._orchestration_current_id,
                    "status": self._orchestration_status_text,
                    "last_error": self._orchestration_last_error,
                },
            }
            return state

    def resolve_application_eligibility(self, application_id: str, eligible: bool, note: str) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            self.applications.resolve_eligibility(application_id, bool(eligible), note)
            self.database.record_foundation_activity(
                self.session_id,
                "eligibility_review_resolved",
                f"Resolved Phase 8 eligibility review for {application_id} as {'eligible' if eligible else 'ineligible'}",
            )
            return self.snapshot()

    def retry_application_tailoring(self, application_id: str) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            self.applications.retry_tailoring(application_id)
            self.database.record_foundation_activity(
                self.session_id, "tailoring_retry", f"Retried Phase 8 tailoring prerequisite for {application_id}"
            )
            return self.snapshot()

    def queue_prepared_controlled_application(self, application_id: str, target_url: str) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            self.applications.queue_prepared_controlled(application_id, target_url)
            self.database.record_foundation_activity(
                self.session_id,
                "phase8_controlled_queue",
                f"Queued fresh prepared package {application_id} for loopback-only submission acceptance",
            )
            return self.snapshot()

    def approve_application_question(self, question_id: str, answer: str) -> dict[str, Any]:
        with self.database._lock:
            row = self.database.connection.execute(
                "SELECT application_id FROM application_questions WHERE id=?", (question_id,)
            ).fetchone()
        application_id = str(row["application_id"]) if row is not None else ""
        worker = self._application_worker
        resume_worker = bool(
            worker is not None
            and self._state is SessionState.RUNNING
            and worker.status()["alive"]
            and not worker.status()["paused"]
        )
        if worker is not None:
            worker.pause()
        try:
            self.applications.resolve_question(question_id, answer)
            if application_id:
                attempt = self.applications.attempt(application_id)
                if attempt.get("package_id") and str(attempt["state"]) == ApplicationState.QUEUED.value:
                    self.applications.prepare_from_run(application_id)
            with self._lock:
                self.database.record_foundation_activity(
                    self.session_id,
                    "application_answer_approved",
                    "Approved an exact-context form answer and refreshed the immutable Phase 8 package after review completed",
                )
                return self.snapshot()
        finally:
            if worker is not None and resume_worker:
                worker.resume()

    def approve_tailored_resume(self, run_id: str, note: str | None = None) -> dict[str, Any]:
        super().approve_tailored_resume(run_id, note)
        with self.database._lock:
            rows = self.database.connection.execute(
                "SELECT id FROM application_attempts WHERE tailoring_run_id=? AND state='review_required'",
                (run_id,),
            ).fetchall()
        for row in rows:
            self.applications.prepare_from_run(str(row["id"]))
        return self.snapshot()

    def inspect_prepared_application(self, application_id: str) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            application = self.applications.attempt(application_id)
            if str(application["state"]) != ApplicationState.PREPARED.value or bool(application.get("controlled_fixture")):
                raise RuntimeError("only a prepared real-employer package can be inspected read-only")
            stale = self.applications.package_stale_reason(application_id)
            if stale:
                self.applications.transition(application_id, ApplicationState.STALE, f"prepared package invalidated before live recognition: {stale}")
                raise RuntimeError(f"prepared application is stale: {stale}")
            provider = str(application.get("provider") or "")
            target = str(application.get("live_apply_url") or "")

        adapter_type = {
            "greenhouse": GreenhouseAdapter,
            "lever": LeverAdapter,
            "ashby": AshbyAdapter,
        }.get(provider)
        if adapter_type is None:
            result = {"supported": False, "fields": [], "blockers": ["unsupported_provider"], "submit_controls": 0, "read_only": True}
            self.applications.record_live_inspection(application_id, result)
            return self.snapshot()

        from playwright.sync_api import sync_playwright

        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(self.paths.browsers))
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                str(self.paths.browser_profile), headless=True, accept_downloads=False, service_workers="block"
            )
            context.set_default_timeout(5000)
            page = context.new_page()
            try:
                inspection = adapter_type(page).inspect(target)
                result = {
                    "supported": bool(inspection.supported),
                    "fields": [
                        {"name": field.name, "field_type": field.field_type, "required": field.required, "label": field.label}
                        for field in inspection.fields
                    ],
                    "blockers": list(inspection.blockers),
                    "submit_controls": int(inspection.submit_controls),
                    "read_only": True,
                }
            finally:
                page.close()
                context.close()
        self.applications.record_live_inspection(application_id, result)
        self.database.record_foundation_activity(
            self.session_id,
            "phase8_live_recognition",
            f"Read-only {provider} recognition recorded for {application_id}; no employer write path was invoked",
        )
        return self.snapshot()

    def run_orchestration_cycle(self, *, discover: bool = False) -> dict[str, Any]:
        """Run one explicit idle diagnostic cycle; Start uses the same implementation continuously."""
        with self._lock:
            self._require_idle_onboarding()
        cancel = threading.Event()
        if discover:
            self._discover_once(cancel)
        self._orchestrate_once(cancel)
        return self.snapshot()

    def _discover_once(self, cancel: threading.Event) -> None:
        boards = [board for board in self.job_store.boards() if bool(board["enabled"])]
        imported = 0
        failed = 0
        for board in boards:
            if cancel.is_set():
                return
            try:
                jobs = fetch_board(str(board["provider"]), str(board["employer"]), str(board["board_token"]))
                self.job_store.replace_board_jobs(str(board["id"]), jobs)
                self.job_store.mark_checked(str(board["id"]))
                imported += len(jobs)
            except Exception as exc:
                failed += 1
                self.job_store.mark_checked(str(board["id"]), str(exc)[-500:])
        self.database.record_foundation_activity(
            self.session_id,
            "phase8_discovery",
            f"Explicit running session checked {len(boards)} verified public boards; observed {imported} jobs; {failed} board errors",
        )

    def _tailoring_gate_reason(self) -> str | None:
        state = self.models.store.model_state()
        selected = str(state.get("selected_model_install_id") or "")
        if not selected:
            return "select and validate a local model before orchestration can tailor resumes"
        if self.tailoring.auto_tailoring_is_current():
            return None
        gate = self.models.store.review_gate(selected)
        approved = int(gate.get("approved_distinct_resumes") or 0)
        if bool(gate.get("complete")):
            return "five-resume review gate is complete; explicitly enable automatic tailoring before unattended generation continues"
        with self.database._lock:
            pending = int(self.database.connection.execute(
                "SELECT COUNT(*) FROM application_attempts WHERE state='review_required'"
            ).fetchone()[0])
        if pending >= max(0, 5 - approved):
            return "waiting for the remaining first-five tailored resume reviews"
        return None

    def _resource_pressure(self) -> str:
        try:
            hardware = self.models.refresh_hardware()
            return str((hardware.get("budget") or {}).get("memory_pressure") or "unknown")
        except Exception as exc:
            self._orchestration_last_error = str(exc)[:1000]
            return "unknown"

    def _orchestrate_once(self, cancel: threading.Event) -> bool:
        stale = self.applications.mark_stale_prepared()
        if stale:
            self._orchestration_status_text = f"Invalidated {stale} stale prepared package(s)"
            return True

        for attempt in self.applications.history():
            if str(attempt["state"]) != ApplicationState.REVIEW_REQUIRED.value:
                continue
            run_id = str(attempt.get("tailoring_run_id") or "")
            run = self.tailoring_store.get_run(run_id) if run_id else None
            status = str((run or {}).get("status") or "")
            if status in {"approved", "auto_validated"}:
                self.applications.prepare_from_run(str(attempt["id"]))
                self._orchestration_status_text = "Prepared a reviewed resume package"
                return True
            if status == "stale":
                self.applications.transition(str(attempt["id"]), ApplicationState.STALE, "linked tailored resume became stale")
                return True
            if status in {"blocked", "failed"}:
                self.applications.transition(str(attempt["id"]), ApplicationState.BLOCKED, f"linked tailored resume is {status}")
                return True

        candidate = next(
            (
                item for item in reversed(self.applications.history())
                if str(item["state"]) in {ApplicationState.ELIGIBLE.value, ApplicationState.TAILORING.value}
            ),
            None,
        )
        if candidate is not None:
            application_id = str(candidate["id"])
            state = ApplicationState(str(candidate["state"]))
            if state is ApplicationState.ELIGIBLE:
                gate_reason = self._tailoring_gate_reason()
                if gate_reason:
                    if gate_reason.startswith("select and validate"):
                        self.applications.transition(application_id, ApplicationState.NEEDS_REVIEW, gate_reason)
                        self._orchestration_status_text = gate_reason
                        return True
                    self._orchestration_status_text = gate_reason
                    return False
                pressure = self._resource_pressure()
                if pressure == "critical":
                    self._orchestration_status_text = "Critical memory pressure; new tailoring is paused without weakening quality gates"
                    return False
                self.applications.begin_tailoring(application_id)
            self._orchestration_current_id = application_id
            try:
                with self.database._lock:
                    job = self.database.connection.execute(
                        "SELECT * FROM discovered_jobs WHERE id=?", (candidate["discovered_job_id"],)
                    ).fetchone()
                if job is None:
                    self.applications.transition(application_id, ApplicationState.STALE, "discovered job disappeared before tailoring")
                    return True
                jd = self.tailoring.import_manual_jd(str(job["description"]), str(job["source_url"]))
                run = self.tailoring.generate(str(jd["id"]), cancel)
                self.applications.set_tailoring_run(application_id, str(run["id"]))
                self.applications.finish_tailoring(application_id, run)
                self.database.record_foundation_activity(
                    self.session_id,
                    "phase8_tailoring",
                    f"Orchestrated tailoring for {application_id} finished as {run['status']}",
                )
                self._orchestration_status_text = f"Tailoring finished as {run['status']}"
                return True
            except Exception as exc:
                if cancel.is_set():
                    self._orchestration_status_text = "Stopped at a pre-submit tailoring checkpoint"
                    return True
                current = self.applications.attempt(application_id)
                if str(current["state"]) == ApplicationState.TAILORING.value:
                    self.applications.transition(
                        application_id,
                        ApplicationState.NEEDS_REVIEW,
                        f"tailoring prerequisite or resource check needs attention: {str(exc)[:700]}",
                    )
                self._orchestration_last_error = str(exc)[:1000]
                self._orchestration_status_text = "Tailoring needs attention"
                return True
            finally:
                self._orchestration_current_id = None

        facts = self._approved_evidence()
        existing = {str(item.get("discovered_job_id") or "") for item in self.applications.history()}
        assessed = [assess_job(job, self._targeting, facts) for job in dedupe_jobs(self.job_store.jobs())]
        order = {"eligible": 0, "review": 1, "ineligible": 2}
        assessed.sort(key=lambda job: (order[str(job["eligibility"])], -int(job["score"]), str(job["employer"]), str(job["title"])))
        for job in assessed:
            if str(job["id"]) in existing:
                continue
            attempt = self.applications.register_discovered_job(job, job)
            self._orchestration_status_text = f"Matched {job['employer']} · {job['title']} as {attempt['state']}"
            return True
        self._orchestration_status_text = "No unprocessed discovered jobs"
        return False

    def _orchestration_loop(self) -> None:
        try:
            while not self._orchestration_stop.is_set():
                if self._orchestration_paused.is_set():
                    self._orchestration_stop.wait(0.2)
                    continue
                if time.monotonic() >= self._next_discovery_at:
                    self._orchestration_status_text = "Refreshing verified public job boards"
                    self._discover_once(self._orchestration_stop)
                    self._next_discovery_at = time.monotonic() + self.DISCOVERY_INTERVAL_SECONDS
                    if self._orchestration_stop.is_set():
                        break
                did_work = self._orchestrate_once(self._orchestration_stop)
                self._orchestration_stop.wait(0.1 if did_work else 0.5)
        except Exception as exc:
            self._orchestration_last_error = str(exc)[:1000]
            self._orchestration_status_text = "Orchestration worker stopped on an error"
        finally:
            self._orchestration_current_id = None
