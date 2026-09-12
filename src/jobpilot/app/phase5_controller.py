from __future__ import annotations

from typing import Any, Mapping

from jobpilot.app.phase4_controller import Phase4ApplicationController
from jobpilot.domain.states import SessionState
from jobpilot.jobs import JobStore, assess_job, dedupe_jobs, fetch_board, normalize_manual_job


class Phase5ApplicationController(Phase4ApplicationController):
    """Public job discovery and local evidence matching; employer submission stays disabled."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.job_store = JobStore(self.database)
        self.database.record_foundation_activity(
            self.session_id,
            "phase5_ready",
            "Phase 5 public discovery/matching loaded; employer submission remains disabled",
        )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = super().snapshot()
            state["phase"] = 5
            state["tailoring"]["phase5_discovery_enabled"] = True
            state["jobs"] = self._job_snapshot()
            return state

    def import_manual_job(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            job = normalize_manual_job(raw)
            self.job_store.upsert(job)
            self.database.record_foundation_activity(
                self.session_id, "manual_job", f"Imported manual job {job['employer']} · {job['title']}"
            )
            return self.snapshot()

    def add_verified_job_board(self, provider: str, employer: str, token: str) -> dict[str, Any]:
        with self._lock:
            cancel = self._begin_onboarding_operation("job-board verification")
        try:
            if cancel.is_set():
                raise RuntimeError("job-board verification cancelled")
            jobs = fetch_board(provider, employer, token)
            with self._lock:
                self._require_open()
                board = self.job_store.add_board(
                    provider, employer, token, verification_source="live public ATS endpoint", user_added=True
                )
                self.job_store.replace_board_jobs(str(board["id"]), jobs)
                self.job_store.mark_checked(str(board["id"]))
                self.database.record_foundation_activity(
                    self.session_id,
                    "job_board_added",
                    f"Verified and added {provider} board {token}; imported {len(jobs)} current jobs",
                )
        finally:
            with self._lock:
                self._end_onboarding_operation()
        return self.snapshot()

    def set_job_board_enabled(self, board_id: str, enabled: bool) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            self.job_store.set_board_enabled(board_id, bool(enabled))
            return self.snapshot()

    def discover_jobs(self) -> dict[str, Any]:
        with self._lock:
            if self._state is not SessionState.IDLE:
                raise RuntimeError("job discovery is allowed only while the session is idle")
            cancel = self._begin_onboarding_operation("public job discovery")
            boards = [board for board in self.job_store.boards() if bool(board["enabled"])]
        imported = 0
        failed = 0
        try:
            for board in boards:
                if cancel.is_set():
                    raise RuntimeError("job discovery cancelled")
                try:
                    jobs = fetch_board(str(board["provider"]), str(board["employer"]), str(board["board_token"]))
                    self.job_store.replace_board_jobs(str(board["id"]), jobs)
                    self.job_store.mark_checked(str(board["id"]))
                    imported += len(jobs)
                except Exception as exc:
                    failed += 1
                    self.job_store.mark_checked(str(board["id"]), str(exc)[-500:])
            with self._lock:
                self._require_open()
                self.database.record_foundation_activity(
                    self.session_id,
                    "job_discovery",
                    f"Checked {len(boards)} verified public boards; observed {imported} jobs; {failed} board errors",
                )
        finally:
            with self._lock:
                self._end_onboarding_operation()
        return self.snapshot()

    def _approved_evidence(self) -> list[dict[str, Any]]:
        master = self.resume_store.get_active_master()
        return self.tailoring._approved_current_facts(master) if master else []

    def _job_snapshot(self) -> dict[str, Any]:
        facts = self._approved_evidence()
        jobs = [assess_job(job, self._targeting, facts) for job in dedupe_jobs(self.job_store.jobs())]
        order = {"eligible": 0, "review": 1, "ineligible": 2}
        jobs.sort(key=lambda job: (order[job["eligibility"]], -int(job["score"]), str(job["employer"]), str(job["title"])))
        counts = {"eligible": 0, "review": 0, "ineligible": 0}
        for job in jobs:
            counts[job["eligibility"]] += 1
        return {
            "boards": self.job_store.boards(),
            "items": jobs,
            "counts": counts,
            "discovery_enabled": True,
            "employer_submission_enabled": False,
            "approved_evidence_facts": len(facts),
        }
