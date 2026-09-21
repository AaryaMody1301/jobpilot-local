from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Mapping, TYPE_CHECKING

from jobpilot.applications.engine import ApplicationJournal, require_controlled_fixture_url
from jobpilot.domain.states import ApplicationState
from jobpilot.storage.database import Database, utc_now_text

if TYPE_CHECKING:
    from jobpilot.resume.tailoring_service import TailoringService


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(value: object) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _decoded(value: object) -> dict[str, Any]:
    try:
        result = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    return result if isinstance(result, dict) else {}


class Phase8ApplicationJournal(ApplicationJournal):
    """Phase 8 orchestration metadata layered on the existing application state journal."""

    def __init__(self, database: Database, tailoring: "TailoringService") -> None:
        super().__init__(database)
        self.tailoring = tailoring

    def attempt_for_job(self, discovered_job_id: str) -> dict[str, Any] | None:
        with self.database._lock:
            row = self.database.connection.execute(
                "SELECT * FROM application_attempts WHERE discovered_job_id=? ORDER BY updated_at DESC LIMIT 1",
                (str(discovered_job_id),),
            ).fetchone()
        return None if row is None else dict(row)

    def register_discovered_job(self, job: Mapping[str, Any], assessment: Mapping[str, Any]) -> dict[str, Any]:
        job_id = str(job.get("id") or "").strip()
        if not job_id:
            raise ValueError("discovered job id is required for orchestration")
        existing = self.attempt_for_job(job_id)
        if existing is not None:
            return existing
        identity = f"job:{job_id}"
        now = utc_now_text()
        eligibility = str(assessment.get("eligibility") or "review")
        reasons = [str(item) for item in assessment.get("hard_reasons", [])]
        if eligibility == "review":
            reasons.extend(str(item) for item in assessment.get("review_reasons", []))
        reason = "; ".join(reasons)[:1000] or "hard eligibility and review checks passed"
        target = {
            "eligible": ApplicationState.ELIGIBLE,
            "review": ApplicationState.NEEDS_REVIEW,
            "ineligible": ApplicationState.INELIGIBLE,
        }.get(eligibility)
        if target is None:
            raise ValueError(f"unsupported eligibility result: {eligibility}")
        with self.database.transaction() as connection:
            application_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO application_attempts(
                    id, job_identity, state, target_url, controlled_fixture, lease_owner,
                    retry_count, next_retry_at, last_reason, created_at, updated_at,
                    discovered_job_id, provider, live_apply_url, eligibility_json
                ) VALUES (?, ?, 'discovered', NULL, 0, NULL, 0, NULL,
                          'discovered job entered Phase 8 orchestration', ?, ?, ?, ?, ?, ?)
                """,
                (
                    application_id,
                    identity,
                    now,
                    now,
                    job_id,
                    str(job.get("provider") or "manual"),
                    str(job.get("apply_url") or job.get("source_url") or ""),
                    _stable_json(dict(assessment)),
                ),
            )
            connection.execute(
                "INSERT INTO application_events(application_id, from_state, to_state, reason, created_at) VALUES (?, NULL, 'discovered', 'discovered job entered Phase 8 orchestration', ?)",
                (application_id, now),
            )
            self._transition_tx(connection, application_id, ApplicationState.ELIGIBILITY_CHECK, "evaluating configured hard eligibility and evidence-backed matching")
            self._transition_tx(connection, application_id, target, reason)
            row = connection.execute("SELECT * FROM application_attempts WHERE id=?", (application_id,)).fetchone()
        return dict(row)

    def resolve_eligibility(self, application_id: str, eligible: bool, note: str) -> dict[str, Any]:
        text = " ".join(str(note or "").split())[:1000]
        if not text:
            raise ValueError("eligibility review resolution requires a note")
        now = utc_now_text()
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM application_attempts WHERE id=?", (application_id,)).fetchone()
            if row is None:
                raise KeyError(application_id)
            assessment = _decoded(row["eligibility_json"])
            if str(row["state"]) != ApplicationState.NEEDS_REVIEW.value or str(assessment.get("eligibility")) != "review":
                raise RuntimeError("application is not awaiting an eligibility review")
            if row["tailoring_run_id"]:
                raise RuntimeError("eligibility review cannot be changed after tailoring started")
            resolution = "approved" if eligible else "rejected"
            connection.execute(
                "UPDATE application_attempts SET eligibility_resolution=?, eligibility_note=?, eligibility_resolved_at=?, updated_at=? WHERE id=?",
                (resolution, text, now, now, application_id),
            )
            self._transition_tx(connection, application_id, ApplicationState.ELIGIBILITY_CHECK, f"human eligibility review resolved: {text}")
            self._transition_tx(
                connection,
                application_id,
                ApplicationState.ELIGIBLE if eligible else ApplicationState.INELIGIBLE,
                f"human eligibility review {resolution}: {text}",
            )
        return self.attempt(application_id)

    def begin_tailoring(self, application_id: str) -> dict[str, Any]:
        row = self.attempt(application_id)
        state = ApplicationState(str(row["state"]))
        if state is ApplicationState.TAILORING:
            return row
        self.transition(application_id, ApplicationState.TAILORING, "eligible application entered evidence-backed resume tailoring")
        return self.attempt(application_id)

    def retry_tailoring(self, application_id: str) -> dict[str, Any]:
        row = self.attempt(application_id)
        if str(row["state"]) != ApplicationState.NEEDS_REVIEW.value:
            raise RuntimeError("application is not waiting on a tailoring prerequisite")
        assessment = _decoded(row["eligibility_json"])
        eligibility_ok = str(assessment.get("eligibility")) == "eligible" or str(row.get("eligibility_resolution") or "") == "approved"
        if not eligibility_ok:
            raise RuntimeError("unresolved eligibility review cannot retry tailoring")
        return self.transition(application_id, ApplicationState.TAILORING, "user retried tailoring after prerequisite review")

    def set_tailoring_run(self, application_id: str, run_id: str) -> dict[str, Any]:
        with self.database.transaction() as connection:
            row = connection.execute("SELECT state FROM application_attempts WHERE id=?", (application_id,)).fetchone()
            if row is None:
                raise KeyError(application_id)
            if str(row["state"]) != ApplicationState.TAILORING.value:
                raise RuntimeError("tailoring run can only be attached while application is tailoring")
            connection.execute(
                "UPDATE application_attempts SET tailoring_run_id=?, last_reason='tailoring run attached', updated_at=? WHERE id=?",
                (str(run_id), utc_now_text(), application_id),
            )
        return self.attempt(application_id)

    def finish_tailoring(self, application_id: str, run: Mapping[str, Any]) -> dict[str, Any]:
        run_id = str(run.get("id") or "")
        if not run_id:
            raise ValueError("tailoring result is missing an id")
        current = self.attempt(application_id)
        if not current.get("tailoring_run_id"):
            self.set_tailoring_run(application_id, run_id)
        status = str(run.get("status") or "")
        if status in {"approved", "auto_validated"}:
            return self.prepare_from_run(application_id)
        target = {
            "needs_review": ApplicationState.REVIEW_REQUIRED,
            "blocked": ApplicationState.BLOCKED,
            "stale": ApplicationState.STALE,
            "failed": ApplicationState.FAILED,
        }.get(status, ApplicationState.NEEDS_REVIEW)
        return self.transition(application_id, target, f"tailoring run {run_id} finished as {status or 'unknown'}")

    def _require_current_run(self, run_id: str) -> dict[str, Any]:
        run = self.tailoring.store.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        status = str(run.get("status") or "")
        if status not in {"approved", "auto_validated"}:
            raise RuntimeError(f"tailoring run is not prepared: {status}")
        validation = run.get("validation") or {}
        if not bool(validation.get("overall_pass")):
            raise RuntimeError("tailoring run did not pass deterministic validation")
        stale = self.tailoring._stale_reason(run)
        if stale:
            raise RuntimeError(f"tailoring run is stale: {stale}")
        if status == "auto_validated" and not self.tailoring.auto_tailoring_is_current():
            raise RuntimeError("automatic tailoring approval is no longer current")
        self.tailoring._verify_run_artifacts(run)
        return run

    def _answers_fingerprint(self) -> str:
        with self.database._lock:
            rows = self.database.connection.execute(
                """
                SELECT id, question_key, context_sha256, label, answer, approved_at
                  FROM approved_application_answers
                 ORDER BY question_key, context_sha256
                """
            ).fetchall()
        return _sha([dict(row) for row in rows])

    def _job(self, discovered_job_id: str) -> dict[str, Any]:
        with self.database._lock:
            row = self.database.connection.execute(
                "SELECT * FROM discovered_jobs WHERE id=?", (discovered_job_id,)
            ).fetchone()
        if row is None:
            raise RuntimeError("discovered job snapshot is missing")
        return dict(row)

    def prepare_from_run(self, application_id: str) -> dict[str, Any]:
        application = self.attempt(application_id)
        run_id = str(application.get("tailoring_run_id") or "")
        if not run_id:
            raise RuntimeError("application has no linked tailoring run")
        run = self._require_current_run(run_id)
        job_id = str(application.get("discovered_job_id") or "")
        if not job_id:
            raise RuntimeError("orchestrated application has no discovered job snapshot")
        job = self._job(job_id)
        if not bool(job.get("active")):
            raise RuntimeError("discovered job is no longer active")
        answers_sha = self._answers_fingerprint()
        manifest = {
            "schema_version": 1,
            "application_id": application_id,
            "job": {
                "id": job_id,
                "provider": job.get("provider"),
                "source_job_id": job.get("source_job_id"),
                "content_sha256": job.get("content_sha256"),
                "source_url": job.get("source_url"),
                "apply_url": job.get("apply_url"),
            },
            "tailoring": {
                "run_id": run_id,
                "manifest_sha256": run.get("manifest_sha256"),
                "pdf_sha256": run.get("pdf_sha256"),
                "master_sha256": run.get("master_sha256"),
                "fact_bank_revision": run.get("fact_bank_revision"),
                "model_install_id": run.get("model_install_id"),
                "runtime_install_id": run.get("runtime_install_id"),
                "device_id": run.get("device_id"),
                "review_context_sha256": run.get("review_context_sha256"),
            },
            "approved_answers_sha256": answers_sha,
        }
        manifest_json = _stable_json(manifest)
        manifest_sha = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
        package_id = str(uuid.uuid4())
        now = utc_now_text()
        with self.database.transaction() as connection:
            row = connection.execute("SELECT state FROM application_attempts WHERE id=?", (application_id,)).fetchone()
            if row is None:
                raise KeyError(application_id)
            state = ApplicationState(str(row["state"]))
            if state not in {ApplicationState.TAILORING, ApplicationState.REVIEW_REQUIRED, ApplicationState.PREPARED, ApplicationState.QUEUED}:
                raise RuntimeError(f"application cannot create a package from {state.value}")
            connection.execute(
                """
                INSERT INTO application_packages(
                    id, application_id, discovered_job_id, tailoring_run_id,
                    manifest_json, manifest_sha256, answers_sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (package_id, application_id, job_id, run_id, manifest_json, manifest_sha, answers_sha, now),
            )
            connection.execute(
                """
                UPDATE application_attempts
                   SET package_id=?, orchestration_context_sha256=?, last_reason=?, updated_at=?
                 WHERE id=?
                """,
                (package_id, manifest_sha, "immutable Phase 8 application package prepared", now, application_id),
            )
            if state in {ApplicationState.TAILORING, ApplicationState.REVIEW_REQUIRED}:
                self._transition_tx(connection, application_id, ApplicationState.PREPARED, "fresh immutable application package prepared")
        return self.attempt(application_id)

    def package_stale_reason(self, application_id: str) -> str | None:
        application = self.attempt(application_id)
        package_id = str(application.get("package_id") or "")
        if not package_id:
            return "application package is missing"
        with self.database._lock:
            package = self.database.connection.execute(
                "SELECT * FROM application_packages WHERE id=? AND application_id=?",
                (package_id, application_id),
            ).fetchone()
        if package is None:
            return "application package record is missing"
        manifest_json = str(package["manifest_json"])
        if hashlib.sha256(manifest_json.encode("utf-8")).hexdigest() != str(package["manifest_sha256"]):
            return "application package manifest failed integrity verification"
        manifest = _decoded(manifest_json)
        job_manifest = manifest.get("job") if isinstance(manifest.get("job"), dict) else {}
        tailoring_manifest = manifest.get("tailoring") if isinstance(manifest.get("tailoring"), dict) else {}
        try:
            job = self._job(str(application.get("discovered_job_id") or ""))
        except Exception as exc:
            return str(exc)
        if not bool(job.get("active")):
            return "job is no longer active"
        if str(job.get("content_sha256") or "") != str(job_manifest.get("content_sha256") or ""):
            return "job description snapshot changed"
        if str(job.get("apply_url") or "") != str(job_manifest.get("apply_url") or ""):
            return "job application URL changed"
        run_id = str(application.get("tailoring_run_id") or "")
        try:
            run = self._require_current_run(run_id)
        except Exception as exc:
            return str(exc)[:500]
        if str(run.get("manifest_sha256") or "") != str(tailoring_manifest.get("manifest_sha256") or ""):
            return "tailoring audit manifest changed"
        if str(run.get("pdf_sha256") or "") != str(tailoring_manifest.get("pdf_sha256") or ""):
            return "tailored resume PDF changed"
        current_answers = self._answers_fingerprint()
        if current_answers != str(package["answers_sha256"]) or current_answers != str(manifest.get("approved_answers_sha256") or ""):
            return "approved application answers changed"
        if bool(application.get("controlled_fixture")):
            try:
                require_controlled_fixture_url(application.get("target_url"))
            except Exception as exc:
                return str(exc)[:500]
        return None

    def mark_stale_prepared(self) -> int:
        with self.database._lock:
            ids = [
                str(row["id"])
                for row in self.database.connection.execute(
                    "SELECT id FROM application_attempts WHERE state='prepared' AND package_id IS NOT NULL"
                ).fetchall()
            ]
        count = 0
        for application_id in ids:
            reason = self.package_stale_reason(application_id)
            if reason:
                self.transition(application_id, ApplicationState.STALE, f"prepared package invalidated: {reason}")
                count += 1
        return count

    def queue_prepared_controlled(self, application_id: str, target_url: str) -> dict[str, Any]:
        url = require_controlled_fixture_url(target_url)
        reason = self.package_stale_reason(application_id)
        if reason:
            row = self.attempt(application_id)
            if str(row["state"]) == ApplicationState.PREPARED.value:
                self.transition(application_id, ApplicationState.STALE, f"prepared package invalidated: {reason}")
            raise RuntimeError(f"prepared application is stale: {reason}")
        with self.database.transaction() as connection:
            row = connection.execute("SELECT state, package_id FROM application_attempts WHERE id=?", (application_id,)).fetchone()
            if row is None:
                raise KeyError(application_id)
            if str(row["state"]) != ApplicationState.PREPARED.value or not row["package_id"]:
                raise RuntimeError("only a fresh prepared application can enter the controlled submission queue")
            connection.execute(
                "UPDATE application_attempts SET target_url=?, controlled_fixture=1, updated_at=? WHERE id=?",
                (url, utc_now_text(), application_id),
            )
            self._transition_tx(connection, application_id, ApplicationState.QUEUED, "prepared package queued for loopback-only Phase 8 submission acceptance")
        return self.attempt(application_id)

    def record_live_inspection(self, application_id: str, result: Mapping[str, Any]) -> dict[str, Any]:
        with self.database.transaction() as connection:
            row = connection.execute("SELECT state, controlled_fixture FROM application_attempts WHERE id=?", (application_id,)).fetchone()
            if row is None:
                raise KeyError(application_id)
            if str(row["state"]) != ApplicationState.PREPARED.value or bool(row["controlled_fixture"]):
                raise RuntimeError("live form recognition is allowed only for a prepared non-controlled application")
            connection.execute(
                "UPDATE application_attempts SET live_form_json=?, live_form_checked_at=?, updated_at=? WHERE id=?",
                (_stable_json(dict(result)), utc_now_text(), utc_now_text(), application_id),
            )
        return self.attempt(application_id)

    def claim_next(self, session_id: str) -> dict[str, Any] | None:
        while True:
            with self.database._lock:
                row = self.database.connection.execute(
                    """
                    SELECT id, package_id FROM application_attempts
                     WHERE controlled_fixture=1 AND state='queued'
                       AND (next_retry_at IS NULL OR next_retry_at<=?)
                     ORDER BY COALESCE(created_at, updated_at), id LIMIT 1
                    """,
                    (utc_now_text(),),
                ).fetchone()
            if row is None:
                return None
            if row["package_id"]:
                reason = self.package_stale_reason(str(row["id"]))
                if reason:
                    self.transition(str(row["id"]), ApplicationState.STALE, f"package invalidated before submit claim: {reason}")
                    continue
            return super().claim_next(session_id)

    def history(self, limit: int = 200) -> list[dict[str, Any]]:
        with self.database._lock:
            rows = self.database.connection.execute(
                """
                SELECT a.*, j.employer, j.title, j.location, j.workplace_type, j.employment_type,
                       j.source_url, j.apply_url, j.published_at,
                       j.compensation_text, j.application_deadline,
                       p.manifest_sha256 AS package_manifest_sha256,
                       p.created_at AS package_created_at,
                       t.status AS tailoring_status,
                       t.pdf_relpath AS tailored_pdf_relpath,
                       t.pdf_sha256 AS tailored_pdf_sha256,
                       t.reviewed_at AS tailored_reviewed_at
                  FROM application_attempts a
                  LEFT JOIN discovered_jobs j ON j.id=a.discovered_job_id
                  LEFT JOIN application_packages p ON p.id=a.package_id
                  LEFT JOIN tailored_resumes t ON t.id=a.tailoring_run_id
                 ORDER BY COALESCE(a.created_at, a.updated_at) DESC, a.id DESC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["eligibility"] = _decoded(item.pop("eligibility_json", "{}"))
            item["live_form"] = _decoded(item.pop("live_form_json", "{}"))
            result.append(item)
        return result

    def workspace_detail(self, application_id: str) -> dict[str, Any]:
        with self.database._lock:
            row = self.database.connection.execute(
                """
                SELECT a.*, j.employer, j.title, j.location, j.workplace_type, j.employment_type,
                       j.source_url, j.apply_url, j.description, j.published_at,
                       j.compensation_text, j.application_deadline,
                       p.manifest_sha256 AS package_manifest_sha256,
                       p.created_at AS package_created_at,
                       t.status AS tailoring_status,
                       t.pdf_relpath AS tailored_pdf_relpath,
                       t.pdf_sha256 AS tailored_pdf_sha256,
                       t.reviewed_at AS tailored_reviewed_at
                  FROM application_attempts a
                  LEFT JOIN discovered_jobs j ON j.id=a.discovered_job_id
                  LEFT JOIN application_packages p ON p.id=a.package_id
                  LEFT JOIN tailored_resumes t ON t.id=a.tailoring_run_id
                 WHERE a.id=?
                """,
                (str(application_id),),
            ).fetchone()
        if row is None:
            raise KeyError(application_id)
        item = dict(row)
        item["eligibility"] = _decoded(item.pop("eligibility_json", "{}"))
        item["live_form"] = _decoded(item.pop("live_form_json", "{}"))
        return item

    def update_workspace(
        self,
        application_id: str,
        *,
        follow_up_at: str | None,
        notes: str,
        next_action: str,
    ) -> dict[str, Any]:
        follow_up = str(follow_up_at or "").strip()
        if follow_up:
            try:
                datetime.fromisoformat(follow_up.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("follow-up date must be ISO-8601") from exc
        notes_text = str(notes or "").strip()
        next_action_text = " ".join(str(next_action or "").split()).strip()
        if len(follow_up) > 40:
            raise ValueError("follow-up date is too long")
        if len(notes_text) > 4000:
            raise ValueError("application notes exceed 4000 characters")
        if len(next_action_text) > 500:
            raise ValueError("next action exceeds 500 characters")
        now = utc_now_text()
        with self.database.transaction() as connection:
            updated = connection.execute(
                """
                UPDATE application_attempts
                   SET follow_up_at=?, notes=?, next_action=?, updated_at=?
                 WHERE id=?
                """,
                (follow_up or None, notes_text, next_action_text, now, str(application_id)),
            ).rowcount
            if updated != 1:
                raise KeyError(application_id)
        return self.attempt(str(application_id))

    def daily_progress(self) -> dict[str, Any]:
        local_zone = datetime.now().astimezone().tzinfo
        today = datetime.now().astimezone().date()
        with self.database._lock:
            rows = self.database.connection.execute(
                "SELECT controlled_fixture, confirmed_at FROM application_attempts WHERE state='confirmed' AND confirmed_at IS NOT NULL"
            ).fetchall()
        real = 0
        controlled = 0
        for row in rows:
            try:
                value = datetime.fromisoformat(str(row["confirmed_at"]))
                local_day = value.astimezone(local_zone).date() if local_zone is not None else value.date()
            except ValueError:
                continue
            if local_day != today:
                continue
            if bool(row["controlled_fixture"]):
                controlled += 1
            else:
                real += 1
        return {
            "local_date": today.isoformat(),
            "target_confirmed": 50,
            "confirmed_real": real,
            "confirmed_controlled": controlled,
            "remaining_to_target": max(0, 50 - real),
            "target_is_not_a_ceiling": True,
            "quality_gates_never_weakened": True,
        }

    def orchestration_summary(self) -> dict[str, Any]:
        history = self.history()
        counts: dict[str, int] = {}
        attention: list[dict[str, Any]] = []
        for item in history:
            state = str(item["state"])
            counts[state] = counts.get(state, 0) + 1
            kind = ""
            if state == ApplicationState.NEEDS_REVIEW.value:
                assessment = item.get("eligibility") or {}
                if str(assessment.get("eligibility")) == "review" and not item.get("eligibility_resolution") and not item.get("tailoring_run_id"):
                    kind = "eligibility_review"
                else:
                    kind = "tailoring_prerequisite"
            elif state == ApplicationState.REVIEW_REQUIRED.value:
                kind = "resume_review"
            elif state == ApplicationState.PREPARED.value and not bool(item.get("controlled_fixture")):
                blockers = list((item.get("live_form") or {}).get("blockers") or [])
                kind = "live_form_blocked" if blockers else "pilot_activation_required"
            elif state in {ApplicationState.BLOCKED.value, ApplicationState.STALE.value, ApplicationState.UNCERTAIN.value}:
                kind = state
            if kind:
                attention.append({**item, "attention_kind": kind})
        with self.database._lock:
            package_count = int(self.database.connection.execute("SELECT COUNT(*) FROM application_packages").fetchone()[0])
        return {
            "counts": counts,
            "attention": attention[:100],
            "history": history,
            "packages": package_count,
            "daily": self.daily_progress(),
            "real_employer_submission_enabled": False,
            "phase9_activation_required": True,
        }
