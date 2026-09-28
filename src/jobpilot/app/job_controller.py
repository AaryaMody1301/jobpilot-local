from __future__ import annotations

from typing import Any, Mapping

from jobpilot.app.tailoring_controller import TailoringController
from jobpilot.domain.states import SessionState
from jobpilot.jobs import JobStore, assess_job, dedupe_jobs, fetch_board, fetch_job_metadata, normalize_manual_job


class JobController(TailoringController):
    """Public job discovery and local evidence matching; employer submission stays disabled."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.job_store = JobStore(self.database)
        self.database.record_foundation_activity(
            self.session_id,
            "jobs_ready",
            "Public discovery/matching loaded; employer submission remains disabled",
        )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = super().snapshot()
            state["tailoring"]["job_discovery_enabled"] = True
            state["jobs"] = self._job_snapshot(state["resume"].get("template_bundle_error"))
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
            skipped: list[str] = []
            jobs = fetch_board(provider, employer, token, skipped=skipped)
            with self._lock:
                self._require_open()
                board = self.job_store.add_board(
                    provider, employer, token, verification_source="live public ATS endpoint", user_added=True
                )
                self.job_store.replace_board_jobs(str(board["id"]), jobs)
                self.job_store.mark_checked(str(board["id"]), f"Skipped {len(skipped)} malformed posting(s): {skipped[0]}"[:500] if skipped else None)
                self.database.record_foundation_activity(
                    self.session_id,
                    "job_board_added",
                    f"Verified and added {provider} board {token}; imported {len(jobs)} current jobs; skipped {len(skipped)} malformed postings",
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
        skipped_total = 0
        try:
            for board in boards:
                if cancel.is_set():
                    raise RuntimeError("job discovery cancelled")
                try:
                    skipped: list[str] = []
                    jobs = fetch_board(str(board["provider"]), str(board["employer"]), str(board["board_token"]), skipped=skipped)
                    self.job_store.replace_board_jobs(str(board["id"]), jobs)
                    self.job_store.mark_checked(str(board["id"]), f"Skipped {len(skipped)} malformed posting(s): {skipped[0]}"[:500] if skipped else None)
                    imported += len(jobs)
                    skipped_total += len(skipped)
                except Exception as exc:
                    failed += 1
                    self.job_store.mark_checked(str(board["id"]), str(exc)[-500:])
            with self._lock:
                self._require_open()
                self.database.record_foundation_activity(
                    self.session_id,
                    "job_discovery",
                    f"Checked {len(boards)} verified public boards; observed {imported} jobs; skipped {skipped_total} malformed postings; {failed} board errors",
                )
        finally:
            with self._lock:
                self._end_onboarding_operation()
        return self.snapshot()

    def job_workspace_detail(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            job = self.job_store.job(job_id)
            try:
                facts = self._approved_evidence()
            except Exception as exc:
                assessed = assess_job(job, self._targeting, [])
                if assessed["eligibility"] == "eligible":
                    assessed["eligibility"] = "review"
                assessed["review_reasons"].append(f"approved resume evidence is unavailable: {str(exc)[:300]}")
                return assessed
            return assess_job(job, self._targeting, facts)

    def refresh_job_metadata(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            cancel = self._begin_onboarding_operation("job metadata refresh")
        try:
            with self._lock:
                self._require_open()
                job = self.job_store.job(job_id)
            if cancel.is_set():
                raise RuntimeError("job metadata refresh cancelled")
            metadata = fetch_job_metadata(job)
            with self._lock:
                self._require_open()
                self.job_store.update_metadata(
                    job_id,
                    compensation_text=metadata.get("compensation_text"),
                    application_deadline=metadata.get("application_deadline"),
                )
                self.database.record_foundation_activity(
                    self.session_id,
                    "job_metadata",
                    f"Refreshed public metadata for {job.get('provider')} job {job.get('source_job_id')}",
                )
        finally:
            with self._lock:
                self._end_onboarding_operation()
        return self.snapshot()

    def _approved_evidence(self, *, verify_template: bool = True) -> list[dict[str, Any]]:
        master = self.resume_store.get_active_master()
        if master is not None and verify_template:
            self.documents.verified_bundle(master)
        return self.tailoring._approved_current_facts(master) if master else []

    def job_workspace_page(self, search: str = "", eligibility: str = "all", offset: int = 0) -> dict[str, Any]:
        """Assess the complete saved match set when the user requests a workspace page."""
        if eligibility not in {"all", "eligible", "review", "ineligible"} or not 0 <= offset <= 1_000_000:
            raise ValueError("invalid job workspace filter or offset")
        with self._lock:
            self._require_open()
            error = None
            try:
                facts = self._approved_evidence()
            except Exception as exc:
                facts = []
                error = f"approved resume evidence is unavailable: {str(exc)[:300]}"
            # Dedupe precedes slicing so a duplicate at a page boundary cannot hide a unique job.
            jobs = [assess_job(job, self._targeting, facts) for job in dedupe_jobs(self.job_store.jobs(None, search=search))]
            if error:
                for job in jobs:
                    if job["eligibility"] == "eligible":
                        job["eligibility"] = "review"
                    job["review_reasons"].append(error)
            counts = {status: sum(job["eligibility"] == status for job in jobs) for status in ("eligible", "review", "ineligible")}
            if eligibility != "all":
                jobs = [job for job in jobs if job["eligibility"] == eligibility]
            order = {"eligible": 0, "review": 1, "ineligible": 2}
            jobs.sort(key=lambda job: (order[job["eligibility"]], -int(job["score"]), str(job["employer"]), str(job["title"]), str(job["id"])))
            return {"items": [{key: value for key, value in job.items() if key != "description"} for job in jobs[offset:offset + 50]],
                    "total": len(jobs), "counts": counts, "offset": offset, "page_size": 50, "evidence_error": error}

    def _job_snapshot(self, bundle_error: str | None = None) -> dict[str, Any]:
        evidence_error = bundle_error
        try:
            facts = self._approved_evidence(verify_template=False) if not bundle_error else []
        except Exception as exc:
            facts = []
            evidence_error = f"approved resume evidence is unavailable: {str(exc)[:300]}"
        jobs = [assess_job(job, self._targeting, facts) for job in dedupe_jobs(self.job_store.jobs())]
        if evidence_error:
            for job in jobs:
                if job["eligibility"] == "eligible":
                    job["eligibility"] = "review"
                job["review_reasons"].append(evidence_error)
        order = {"eligible": 0, "review": 1, "ineligible": 2}
        jobs.sort(key=lambda job: (order[job["eligibility"]], -int(job["score"]), str(job["employer"]), str(job["title"])))
        jobs = [{key: value for key, value in job.items() if key != "description"} for job in jobs]
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
            "evidence_error": evidence_error,
        }
