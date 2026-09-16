from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

from jobpilot.applications.engine import (
    ApplicationWorker,
    ControlledFormEngine,
    PRE_SUBMIT_STATES,
    question_context_sha256,
)
from jobpilot.applications.platforms import AshbyAdapter, GreenhouseAdapter, LeverAdapter
from jobpilot.domain.states import ApplicationState
from jobpilot.orchestration import Phase8ApplicationJournal
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import utc_now_text

PILOT_CONFIRMATION_PHRASE = "ENABLE MEASURED REAL APPLICATION PILOT"
PILOT_MAX_ARMED_PER_LAUNCH = 5
PILOT_POLICY_REVISION = "phase9-pilot-v1"

_ADAPTERS = {
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "ashby": AshbyAdapter,
}


def _decoded(value: object) -> dict[str, Any]:
    try:
        parsed = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _live_target(provider: str, value: object) -> str:
    adapter_type = _ADAPTERS.get(provider)
    if adapter_type is None:
        raise ValueError(f"unsupported pilot provider: {provider or 'unknown'}")
    text = str(value or "").strip()
    parsed = urlparse(text)
    if not 1 <= len(text) <= 2000 or parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("real pilot application URL must be an absolute HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError("real pilot application URL cannot contain credentials")
    if (parsed.hostname or "").casefold() not in adapter_type.hosts:
        raise ValueError(f"{provider} pilot target uses an unsupported host")
    return text


def _question_key(provider: str, field: Any) -> str:
    payload = f"{provider}|{field.name}|{field.field_type}|{field.label}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
    return f"live.{provider}.{digest}"


def _question(provider: str, target: str, field: Any) -> dict[str, Any]:
    key = _question_key(provider, field)
    options = [{"value": value, "text": text} for value, text in field.options]
    option_text = ", ".join(text or value for value, text in field.options if text or value)
    label = field.label
    if option_text:
        label = f"{label} [options: {option_text}]"[:300]
    context_sha = question_context_sha256(
        key,
        field.label,
        f"live:{field.field_type}",
        target,
        options,
    )
    return {
        "question_key": key,
        "label": label,
        "context_sha256": context_sha,
        "required": bool(field.required),
        "control_type": field.field_type,
        "options": options,
        "field_name": field.name,
    }


def _resume_field(field: Any) -> bool:
    text = f"{field.name} {field.label}".casefold()
    return bool(re.search(r"\b(?:resume|curriculum vitae|cv)\b", text))


class Phase9PilotApplicationJournal(Phase8ApplicationJournal):
    """Phase 8 journal plus an explicitly armed, one-worker real-pilot queue."""

    def recover_live_pre_submit(self) -> int:
        now = utc_now_text()
        with self.database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT id, state FROM application_attempts
                 WHERE controlled_fixture=0
                   AND state IN ('inspecting', 'filling', 'ready_to_submit')
                   AND package_id IS NOT NULL
                """
            ).fetchall()
            for row in rows:
                connection.execute(
                    """
                    UPDATE application_attempts
                       SET state='queued', lease_owner=NULL, next_retry_at=NULL,
                           last_reason='recovered pre-submit real pilot after interruption; per-launch activation required',
                           updated_at=?
                     WHERE id=?
                    """,
                    (now, row["id"]),
                )
                connection.execute(
                    """
                    INSERT INTO application_events(application_id, from_state, to_state, reason, created_at)
                    VALUES (?, ?, 'queued', 'recovered pre-submit real pilot after interruption; per-launch activation required', ?)
                    """,
                    (row["id"], row["state"], now),
                )
        return len(rows)

    def reset_live_queue_to_prepared(self, reason: str) -> int:
        """Rewind never-submitted queued live work so each launch/deactivation requires re-arming."""
        now = utc_now_text()
        text = " ".join(str(reason).split())[:1000]
        with self.database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT id FROM application_attempts
                 WHERE controlled_fixture=0 AND state='queued'
                   AND package_id IS NOT NULL AND target_url IS NOT NULL
                """
            ).fetchall()
            for row in rows:
                connection.execute(
                    """
                    UPDATE application_attempts
                       SET state='prepared', lease_owner=NULL, target_url=NULL,
                           next_retry_at=NULL, last_reason=?, updated_at=?
                     WHERE id=?
                    """,
                    (text, now, row["id"]),
                )
                connection.execute(
                    """
                    INSERT INTO application_events(application_id, from_state, to_state, reason, created_at)
                    VALUES (?, 'queued', 'prepared', ?, ?)
                    """,
                    (row["id"], text, now),
                )
        return len(rows)

    def queue_prepared_live(self, application_id: str) -> dict[str, Any]:
        application = self.attempt(application_id)
        if str(application["state"]) != ApplicationState.PREPARED.value or bool(application.get("controlled_fixture")):
            raise RuntimeError("only a prepared real-employer package can enter the pilot queue")
        stale = self.package_stale_reason(application_id)
        if stale:
            self.transition(application_id, ApplicationState.STALE, f"prepared package invalidated before pilot queue: {stale}")
            raise RuntimeError(f"prepared application is stale: {stale}")

        provider = str(application.get("provider") or "")
        target = _live_target(provider, application.get("live_apply_url"))
        inspection = _decoded(application.get("live_form_json"))
        blockers = list(inspection.get("blockers") or [])
        if not bool(inspection.get("read_only")):
            raise RuntimeError("run read-only live form inspection before arming the pilot application")
        if not bool(inspection.get("supported")) or blockers or int(inspection.get("submit_controls") or 0) != 1:
            detail = ", ".join(str(item) for item in blockers) or "unsupported live form shape"
            raise RuntimeError(f"live form is not eligible for pilot submission: {detail}")

        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT state, package_id FROM application_attempts WHERE id=?",
                (application_id,),
            ).fetchone()
            if row is None:
                raise KeyError(application_id)
            if str(row["state"]) != ApplicationState.PREPARED.value or not row["package_id"]:
                raise RuntimeError("pilot queue requires a fresh prepared application package")
            connection.execute(
                "UPDATE application_attempts SET target_url=?, controlled_fixture=0, updated_at=? WHERE id=?",
                (target, utc_now_text(), application_id),
            )
            self._transition_tx(
                connection,
                application_id,
                ApplicationState.QUEUED,
                "user explicitly armed one measured real-employer pilot submission",
            )
        return self.attempt(application_id)

    def claim_next_live(self, session_id: str, allowed_ids: set[str]) -> dict[str, Any] | None:
        allowed = {str(item) for item in allowed_ids if str(item)}
        if not allowed:
            return None
        while True:
            now = utc_now_text()
            placeholders = ",".join("?" for _ in allowed)
            params: tuple[object, ...] = (now, *sorted(allowed))
            with self.database._lock:
                row = self.database.connection.execute(
                    f"""
                    SELECT id FROM application_attempts
                     WHERE controlled_fixture=0 AND state='queued'
                       AND package_id IS NOT NULL AND target_url IS NOT NULL
                       AND (next_retry_at IS NULL OR next_retry_at<=?)
                       AND id IN ({placeholders})
                     ORDER BY COALESCE(created_at, updated_at), id
                     LIMIT 1
                    """,
                    params,
                ).fetchone()
            if row is None:
                return None

            application_id = str(row["id"])
            stale = self.package_stale_reason(application_id)
            if stale:
                self.transition(application_id, ApplicationState.STALE, f"pilot package invalidated before submit claim: {stale}")
                continue
            application = self.attempt(application_id)
            try:
                _live_target(str(application.get("provider") or ""), application.get("target_url"))
            except Exception as exc:
                self.transition(application_id, ApplicationState.BLOCKED, f"pilot target rejected before claim: {exc}")
                continue

            with self.database.transaction() as connection:
                updated = connection.execute(
                    """
                    UPDATE application_attempts
                       SET state='inspecting', lease_owner=?, next_retry_at=NULL,
                           last_reason='single worker claimed user-armed real pilot application', updated_at=?
                     WHERE id=? AND state='queued' AND controlled_fixture=0
                    """,
                    (session_id, now, application_id),
                ).rowcount
                if updated != 1:
                    continue
                connection.execute(
                    """
                    INSERT INTO application_events(application_id, from_state, to_state, reason, created_at)
                    VALUES (?, 'queued', 'inspecting', 'single worker claimed user-armed real pilot application', ?)
                    """,
                    (application_id, now),
                )
                claimed = connection.execute(
                    "SELECT * FROM application_attempts WHERE id=?", (application_id,)
                ).fetchone()
            return dict(claimed)

    def record_pilot_inspection(self, application_id: str, result: Mapping[str, Any]) -> dict[str, Any]:
        now = utc_now_text()
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT state, controlled_fixture FROM application_attempts WHERE id=?", (application_id,)
            ).fetchone()
            if row is None:
                raise KeyError(application_id)
            if str(row["state"]) != ApplicationState.INSPECTING.value or bool(row["controlled_fixture"]):
                raise RuntimeError("pilot reinspection is allowed only for a claimed real application")
            connection.execute(
                "UPDATE application_attempts SET live_form_json=?, live_form_checked_at=?, updated_at=? WHERE id=?",
                (json.dumps(dict(result), sort_keys=True, separators=(",", ":")), now, now, application_id),
            )
        return self.attempt(application_id)


class LiveHostedFormEngine:
    def __init__(
        self,
        paths: ManagedPaths,
        journal: Phase9PilotApplicationJournal,
        live_enabled: Callable[[], bool],
    ) -> None:
        self.paths = paths
        self.journal = journal
        self.live_enabled = live_enabled

    def _resume_path(self, application: Mapping[str, Any]) -> Path:
        run_id = str(application.get("tailoring_run_id") or "")
        run = self.journal.tailoring.store.get_run(run_id) if run_id else None
        if run is None:
            raise RuntimeError("pilot application has no current tailored resume")
        path = Path(str(run.get("pdf_path") or ""))
        if not path.is_file():
            raise RuntimeError("tailored resume PDF is unavailable for pilot upload")
        return path

    @staticmethod
    def _inspection_result(inspection: Any) -> dict[str, Any]:
        return {
            "supported": bool(inspection.supported),
            "fields": [
                {
                    "name": field.name,
                    "field_type": field.field_type,
                    "required": field.required,
                    "label": field.label,
                    "options": [{"value": value, "text": text} for value, text in field.options],
                }
                for field in inspection.fields
            ],
            "blockers": list(inspection.blockers),
            "submit_controls": int(inspection.submit_controls),
            "read_only": False,
            "pilot_reinspection": True,
        }

    def process(self, application: Mapping[str, Any], stop_event: threading.Event) -> None:
        application_id = str(application["id"])
        provider = str(application.get("provider") or "")
        adapter_type = _ADAPTERS.get(provider)
        if adapter_type is None:
            self.journal.transition(application_id, ApplicationState.BLOCKED, "pilot provider is unsupported")
            return
        if not self.live_enabled():
            self.journal.stop_pre_submit(application_id, "per-launch pilot activation is no longer active")
            return
        stale = self.journal.package_stale_reason(application_id)
        if stale:
            self.journal.transition(application_id, ApplicationState.STALE, f"pilot package invalidated before browser write: {stale}")
            return
        target = _live_target(provider, application.get("target_url"))

        from playwright.sync_api import sync_playwright

        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(self.paths.browsers))
        page: Any = None
        context: Any = None
        try:
            with sync_playwright() as playwright:
                context = playwright.chromium.launch_persistent_context(
                    str(self.paths.browser_profile),
                    headless=False,
                    accept_downloads=False,
                    service_workers="block",
                )
                context.set_default_timeout(5000)
                page = context.new_page()
                adapter = adapter_type(page, allow_live_submit=True)
                inspection = adapter.inspect(target)
                self.journal.record_pilot_inspection(application_id, self._inspection_result(inspection))
                if not inspection.supported:
                    detail = ", ".join(inspection.blockers) or "unsupported live form shape"
                    self.journal.transition(application_id, ApplicationState.BLOCKED, f"live pilot form stopped before write: {detail}")
                    return
                if stop_event.is_set() or not self.live_enabled():
                    self.journal.stop_pre_submit(application_id, "pilot stopped before live form filling")
                    return

                self.journal.transition(application_id, ApplicationState.FILLING, "supported live form re-inspected immediately before pilot fill")
                resume_path = self._resume_path(application)
                answers: dict[str, str] = {}
                missing: list[dict[str, Any]] = []
                required_questions: list[dict[str, Any]] = []
                for field in inspection.fields:
                    if field.field_type == "file":
                        if _resume_field(field):
                            answers[field.name] = str(resume_path)
                        elif field.required:
                            self.journal.transition(
                                application_id,
                                ApplicationState.BLOCKED,
                                f"unsupported required live file upload: {field.label}",
                            )
                            return
                        continue
                    question = _question(provider, target, field)
                    if field.required:
                        required_questions.append(question)
                    approved = self.journal.approved_answer(
                        str(question["question_key"]), str(question["context_sha256"])
                    )
                    if approved is None:
                        if field.required:
                            missing.append(question)
                        continue
                    answers[field.name] = approved

                if missing:
                    self.journal.require_review(
                        application_id,
                        missing,
                        "mandatory real-employer form answers require exact-context human approval",
                    )
                    return

                try:
                    adapter.fill(answers)
                except ValueError as exc:
                    if required_questions:
                        self.journal.require_review(
                            application_id,
                            required_questions,
                            f"approved live answer failed browser validation and must be reviewed again: {exc}",
                        )
                    else:
                        self.journal.transition(application_id, ApplicationState.BLOCKED, f"live form validation failed: {exc}")
                    return

                self.journal.transition(
                    application_id,
                    ApplicationState.READY_TO_SUBMIT,
                    "live form filled only with current tailored resume and exact-context approved answers",
                )
                if stop_event.is_set() or not self.live_enabled():
                    self.journal.stop_pre_submit(application_id, "pilot stopped at final pre-submit boundary")
                    return

                self.journal.transition(application_id, ApplicationState.SUBMITTING, "user-armed real pilot submit click started")
                try:
                    adapter.submit()
                except Exception as exc:
                    self.journal.transition(application_id, ApplicationState.UNCERTAIN, f"real pilot submit outcome ambiguous: {exc}")
                    return
                self.journal.transition(application_id, ApplicationState.CONFIRMING, "real pilot submit returned; awaiting explicit positive confirmation")
                confirmation = adapter.confirm()
                if not confirmation.confirmed:
                    self.journal.transition(application_id, ApplicationState.UNCERTAIN, "real pilot submission lacked explicit positive confirmation")
                    return
                evidence = " ".join(str(confirmation.evidence or "explicit success marker").split())[:400]
                self.journal.transition(
                    application_id,
                    ApplicationState.CONFIRMED,
                    f"explicit positive real-employer confirmation observed: {evidence}",
                )
        except Exception as exc:
            state = ApplicationState(str(self.journal.attempt(application_id)["state"]))
            if state in {ApplicationState.SUBMITTING, ApplicationState.CONFIRMING}:
                self.journal.transition(application_id, ApplicationState.UNCERTAIN, f"post-submit pilot exception: {str(exc)[:700]}")
            elif state in PRE_SUBMIT_STATES:
                self.journal.transition(application_id, ApplicationState.BLOCKED, f"real pilot stopped before submit: {str(exc)[:700]}")
            else:
                raise
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass


class PilotApplicationWorker(ApplicationWorker):
    """The existing single application worker, extended with an explicitly armed live lane."""

    def __init__(
        self,
        paths: ManagedPaths,
        journal: Phase9PilotApplicationJournal,
        session_id: str,
        live_enabled: Callable[[], bool],
        live_allowed_ids: Callable[[], set[str]],
    ) -> None:
        super().__init__(paths, journal, session_id)
        self.journal = journal
        self._live_enabled = live_enabled
        self._live_allowed_ids = live_allowed_ids

    def _run(self) -> None:
        try:
            while not self._stop.is_set():
                if self._paused.is_set():
                    self._stop.wait(0.1)
                    continue
                application = self.journal.claim_next(self.session_id)
                if application is None and self._live_enabled():
                    application = self.journal.claim_next_live(self.session_id, self._live_allowed_ids())
                if application is None:
                    self._stop.wait(0.1)
                    continue
                self._current_application_id = str(application["id"])
                if bool(application.get("controlled_fixture")):
                    with ControlledFormEngine(self.paths, self.journal) as engine:
                        engine.process(application, self._stop)
                else:
                    LiveHostedFormEngine(self.paths, self.journal, self._live_enabled).process(application, self._stop)
                self._current_application_id = None
        except Exception as exc:
            self._last_error = str(exc)[:1000]
        finally:
            self._current_application_id = None
