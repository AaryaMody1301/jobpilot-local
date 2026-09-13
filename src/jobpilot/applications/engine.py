from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from jobpilot.domain.states import APPLICATION_MACHINE, ApplicationState
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import Database, utc_now_text

QUESTION_KEY_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")
PRE_SUBMIT_STATES = {
    ApplicationState.INSPECTING,
    ApplicationState.FILLING,
    ApplicationState.READY_TO_SUBMIT,
}
CLEAR_LEASE_STATES = {
    ApplicationState.QUEUED,
    ApplicationState.NEEDS_REVIEW,
    ApplicationState.BLOCKED,
    ApplicationState.FAILED,
    ApplicationState.CONFIRMED,
    ApplicationState.UNCERTAIN,
    ApplicationState.STALE,
}


class ControlledFixtureViolation(ValueError):
    pass


def _is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    if host.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _is_explicit_external_http_url(value: object) -> bool:
    parsed = urlparse(str(value or ""))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and not _is_loopback_host(parsed.hostname)


def require_controlled_fixture_url(value: object) -> str:
    text = str(value or "").strip()
    if not 1 <= len(text) <= 2000:
        raise ControlledFixtureViolation("controlled fixture URL must contain 1-2000 characters")
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ControlledFixtureViolation("controlled fixture URL must be absolute HTTP(S)")
    if parsed.username or parsed.password:
        raise ControlledFixtureViolation("controlled fixture URL cannot contain credentials")
    if not _is_loopback_host(parsed.hostname):
        raise ControlledFixtureViolation("Phase 6 permits localhost/loopback fixtures only; real employer targets are disabled")
    return text


def question_context_sha256(
    question_key: str,
    label: str,
    control_type: str,
    context: str = "",
    options: Sequence[Mapping[str, str]] = (),
) -> str:
    payload = {
        "question_key": question_key,
        "label": label,
        "control_type": control_type,
        "context": context,
        "options": [dict(item) for item in options],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _after(seconds: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


class ApplicationJournal:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _transition_tx(
        connection: Any,
        application_id: str,
        target: ApplicationState,
        reason: str,
        *,
        next_retry_at: str | None = None,
        retry_count: int | None = None,
    ) -> None:
        row = connection.execute(
            "SELECT state, lease_owner, retry_count FROM application_attempts WHERE id=?",
            (application_id,),
        ).fetchone()
        if row is None:
            raise KeyError(application_id)
        current = ApplicationState(str(row["state"]))
        APPLICATION_MACHINE.require_transition(current, target)
        now = utc_now_text()
        lease_owner = None if target in CLEAR_LEASE_STATES else row["lease_owner"]
        submit_started = now if target is ApplicationState.SUBMITTING else None
        confirmed = now if target is ApplicationState.CONFIRMED else None
        connection.execute(
            """
            UPDATE application_attempts
               SET state=?, lease_owner=?, next_retry_at=?,
                   retry_count=?, last_reason=?,
                   submit_started_at=COALESCE(submit_started_at, ?),
                   confirmed_at=COALESCE(confirmed_at, ?), updated_at=?
             WHERE id=?
            """,
            (
                target.value,
                lease_owner,
                next_retry_at,
                int(row["retry_count"] if retry_count is None else retry_count),
                reason[:1000],
                submit_started,
                confirmed,
                now,
                application_id,
            ),
        )
        connection.execute(
            "INSERT INTO application_events(application_id, from_state, to_state, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (application_id, current.value, target.value, reason[:1000], now),
        )

    def queue_controlled(self, job_identity: str, target_url: str) -> dict[str, Any]:
        identity = str(job_identity or "").strip()
        if not 1 <= len(identity) <= 300:
            raise ValueError("controlled fixture job identity must contain 1-300 characters")
        url = require_controlled_fixture_url(target_url)
        now = utc_now_text()
        with self.database.transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM application_attempts WHERE job_identity=?",
                (identity,),
            ).fetchone()
            if existing is not None:
                return dict(existing)
            application_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO application_attempts(
                    id, job_identity, state, target_url, controlled_fixture, lease_owner,
                    retry_count, next_retry_at, last_reason, created_at, updated_at
                ) VALUES (?, ?, 'queued', ?, 1, NULL, 0, NULL, 'controlled fixture queued', ?, ?)
                """,
                (application_id, identity, url, now, now),
            )
            connection.execute(
                "INSERT INTO application_events(application_id, from_state, to_state, reason, created_at) VALUES (?, NULL, 'queued', 'controlled fixture queued', ?)",
                (application_id, now),
            )
            row = connection.execute("SELECT * FROM application_attempts WHERE id=?", (application_id,)).fetchone()
        return dict(row)

    def attempt(self, application_id: str) -> dict[str, Any]:
        with self.database._lock:
            row = self.database.connection.execute(
                "SELECT * FROM application_attempts WHERE id=?",
                (application_id,),
            ).fetchone()
        if row is None:
            raise KeyError(application_id)
        return dict(row)

    def attempts(self, limit: int = 200) -> list[dict[str, Any]]:
        with self.database._lock:
            rows = self.database.connection.execute(
                """
                SELECT * FROM application_attempts
                 WHERE controlled_fixture=1
                 ORDER BY COALESCE(created_at, updated_at) DESC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def open_questions(self) -> list[dict[str, Any]]:
        with self.database._lock:
            rows = self.database.connection.execute(
                """
                SELECT q.*, a.job_identity
                  FROM application_questions q
                  JOIN application_attempts a ON a.id=q.application_id
                 WHERE q.state='review'
                 ORDER BY q.created_at, q.id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def approved_answer(self, question_key: str, context_sha256: str) -> str | None:
        with self.database._lock:
            row = self.database.connection.execute(
                "SELECT answer FROM approved_application_answers WHERE question_key=? AND context_sha256=?",
                (question_key, context_sha256),
            ).fetchone()
        return None if row is None else str(row["answer"])

    def claim_next(self, session_id: str) -> dict[str, Any] | None:
        now = utc_now_text()
        with self.database.transaction() as connection:
            row = connection.execute(
                """
                SELECT * FROM application_attempts
                 WHERE controlled_fixture=1 AND state='queued'
                   AND (next_retry_at IS NULL OR next_retry_at<=?)
                 ORDER BY COALESCE(created_at, updated_at), id
                 LIMIT 1
                """,
                (now,),
            ).fetchone()
            if row is None:
                return None
            updated = connection.execute(
                """
                UPDATE application_attempts
                   SET state='inspecting', lease_owner=?, next_retry_at=NULL,
                       last_reason='single worker claimed controlled fixture', updated_at=?
                 WHERE id=? AND state='queued'
                """,
                (session_id, now, row["id"]),
            ).rowcount
            if updated != 1:
                return None
            connection.execute(
                "INSERT INTO application_events(application_id, from_state, to_state, reason, created_at) VALUES (?, 'queued', 'inspecting', 'single worker claimed controlled fixture', ?)",
                (row["id"], now),
            )
            claimed = connection.execute("SELECT * FROM application_attempts WHERE id=?", (row["id"],)).fetchone()
        return dict(claimed)

    def transition(self, application_id: str, target: ApplicationState, reason: str) -> dict[str, Any]:
        with self.database.transaction() as connection:
            self._transition_tx(connection, application_id, target, reason)
        return self.attempt(application_id)

    def require_review(self, application_id: str, questions: Sequence[Mapping[str, Any]], reason: str) -> dict[str, Any]:
        now = utc_now_text()
        with self.database.transaction() as connection:
            for question in questions:
                key = str(question["question_key"])
                context_sha = str(question["context_sha256"])
                question_id = hashlib.sha256(f"{application_id}|{key}|{context_sha}".encode()).hexdigest()
                connection.execute(
                    """
                    INSERT INTO application_questions(
                        id, application_id, question_key, context_sha256, label,
                        required, state, answer_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'review', NULL, ?, ?)
                    ON CONFLICT(application_id, question_key, context_sha256) DO UPDATE SET
                        label=excluded.label, required=excluded.required, state='review',
                        answer_id=NULL, updated_at=excluded.updated_at
                    """,
                    (
                        question_id,
                        application_id,
                        key,
                        context_sha,
                        str(question["label"])[:300],
                        int(bool(question.get("required", True))),
                        now,
                        now,
                    ),
                )
            self._transition_tx(connection, application_id, ApplicationState.NEEDS_REVIEW, reason)
        return self.attempt(application_id)

    def resolve_question(self, question_id: str, answer: str) -> dict[str, Any]:
        value = str(answer or "").strip()
        if not 1 <= len(value) <= 4000:
            raise ValueError("approved answer must contain 1-4000 characters")
        now = utc_now_text()
        with self.database.transaction() as connection:
            question = connection.execute(
                "SELECT * FROM application_questions WHERE id=?",
                (question_id,),
            ).fetchone()
            if question is None:
                raise KeyError(question_id)
            answer_id = hashlib.sha256(
                f"{question['question_key']}|{question['context_sha256']}".encode()
            ).hexdigest()
            connection.execute(
                """
                INSERT INTO approved_application_answers(id, question_key, context_sha256, label, answer, approved_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(question_key, context_sha256) DO UPDATE SET
                    label=excluded.label, answer=excluded.answer, approved_at=excluded.approved_at
                """,
                (
                    answer_id,
                    question["question_key"],
                    question["context_sha256"],
                    question["label"],
                    value,
                    now,
                ),
            )
            connection.execute(
                "UPDATE application_questions SET state='answered', answer_id=?, updated_at=? WHERE id=?",
                (answer_id, now, question_id),
            )
            remaining = connection.execute(
                "SELECT COUNT(*) FROM application_questions WHERE application_id=? AND state='review'",
                (question["application_id"],),
            ).fetchone()[0]
            if int(remaining) == 0:
                app = connection.execute(
                    "SELECT state FROM application_attempts WHERE id=?",
                    (question["application_id"],),
                ).fetchone()
                if app is not None and str(app["state"]) == ApplicationState.NEEDS_REVIEW.value:
                    self._transition_tx(
                        connection,
                        str(question["application_id"]),
                        ApplicationState.QUEUED,
                        "all mandatory controlled-form questions approved",
                    )
        return self.attempt(str(question["application_id"]))

    def retry_pre_submit(self, application_id: str, reason: str, *, max_retries: int = 3) -> dict[str, Any]:
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT state, retry_count FROM application_attempts WHERE id=?",
                (application_id,),
            ).fetchone()
            if row is None:
                raise KeyError(application_id)
            current = ApplicationState(str(row["state"]))
            if current not in PRE_SUBMIT_STATES:
                raise RuntimeError(f"cannot retry application from {current.value}")
            retry_count = int(row["retry_count"]) + 1
            if retry_count >= max_retries:
                self._transition_tx(
                    connection,
                    application_id,
                    ApplicationState.FAILED,
                    f"pre-submit controlled fixture failed after {retry_count} attempts: {reason}",
                    retry_count=retry_count,
                )
            else:
                # ponytail: fixed tiny local-fixture backoff is sufficient in Phase 6;
                # Phase 7 upgrades this to provider-aware rate-limit/backoff handling.
                delay = 0.25 * (2 ** (retry_count - 1))
                self._transition_tx(
                    connection,
                    application_id,
                    ApplicationState.QUEUED,
                    f"safe pre-submit retry {retry_count}: {reason}",
                    next_retry_at=_after(delay),
                    retry_count=retry_count,
                )
        return self.attempt(application_id)

    def stop_pre_submit(self, application_id: str, reason: str) -> dict[str, Any]:
        with self.database.transaction() as connection:
            self._transition_tx(connection, application_id, ApplicationState.QUEUED, reason)
        return self.attempt(application_id)

    def recover_pre_submit(self) -> int:
        now = utc_now_text()
        with self.database.transaction() as connection:
            rows = connection.execute(
                """
                SELECT id, state FROM application_attempts
                 WHERE controlled_fixture=1 AND state IN ('inspecting', 'filling', 'ready_to_submit')
                """
            ).fetchall()
            for row in rows:
                connection.execute(
                    """
                    UPDATE application_attempts
                       SET state='queued', lease_owner=NULL, next_retry_at=NULL,
                           last_reason='recovered pre-submit controlled fixture after interruption', updated_at=?
                     WHERE id=?
                    """,
                    (now, row["id"]),
                )
                connection.execute(
                    "INSERT INTO application_events(application_id, from_state, to_state, reason, created_at) VALUES (?, ?, 'queued', 'recovered pre-submit controlled fixture after interruption', ?)",
                    (row["id"], row["state"], now),
                )
            connection.execute(
                """
                UPDATE application_attempts SET lease_owner=NULL
                 WHERE controlled_fixture=1
                   AND state IN ('queued', 'needs_review', 'blocked', 'failed', 'confirmed', 'uncertain', 'stale')
                """
            )
        return len(rows)

    def summary(self) -> dict[str, Any]:
        attempts = self.attempts()
        counts: dict[str, int] = {}
        for attempt in attempts:
            state = str(attempt["state"])
            counts[state] = counts.get(state, 0) + 1
        with self.database._lock:
            approved = int(self.database.connection.execute("SELECT COUNT(*) FROM approved_application_answers").fetchone()[0])
        return {
            "attempts": attempts,
            "counts": counts,
            "open_questions": self.open_questions(),
            "approved_answers": approved,
        }


class ControlledFormEngine:
    def __init__(self, paths: ManagedPaths, journal: ApplicationJournal) -> None:
        self.paths = paths
        self.journal = journal
        self._playwright: Any = None
        self._context: Any = None

    def __enter__(self) -> "ControlledFormEngine":
        from playwright.sync_api import sync_playwright

        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(self.paths.browsers))
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            str(self.paths.browser_profile),
            headless=True,
            accept_downloads=False,
            service_workers="block",
        )
        self._context.set_default_timeout(5000)
        self._context.route("**/*", self._guard_route)
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._context is not None:
            self._context.close()
        if self._playwright is not None:
            self._playwright.stop()
        self._context = None
        self._playwright = None

    @staticmethod
    def _guard_route(route: Any) -> None:
        parsed = urlparse(str(route.request.url))
        if parsed.scheme in {"http", "https"} and not _is_loopback_host(parsed.hostname):
            route.abort()
            return
        route.continue_()

    @staticmethod
    def _question(locator: Any) -> dict[str, Any]:
        key = str(locator.get_attribute("data-jobpilot-key") or "").strip()
        label = str(locator.get_attribute("data-jobpilot-label") or "").strip()
        context = str(locator.get_attribute("data-jobpilot-context") or "").strip()
        if not QUESTION_KEY_RE.fullmatch(key):
            raise ControlledFixtureViolation("controlled form question key is missing or invalid")
        if not 1 <= len(label) <= 300 or len(context) > 300:
            raise ControlledFixtureViolation("controlled form question label/context is invalid")
        tag = str(locator.evaluate("el => el.tagName.toLowerCase()"))
        input_type = str(locator.get_attribute("type") or "text").casefold()
        options: list[dict[str, str]] = []
        if tag == "select":
            options = locator.locator("option").evaluate_all(
                "els => els.map(el => ({value: el.value, text: (el.textContent || '').trim()}))"
            )
            control_type = "select"
        elif tag == "textarea":
            control_type = "textarea"
        elif tag == "input" and input_type in {"text", "email", "tel", "url", "number", "date", "checkbox"}:
            control_type = f"input:{input_type}"
        else:
            raise ControlledFixtureViolation(f"unsupported controlled form field: {tag}:{input_type}")
        required = locator.get_attribute("required") is not None or str(locator.get_attribute("data-jobpilot-required") or "").casefold() == "true"
        return {
            "question_key": key,
            "label": label,
            "context_sha256": question_context_sha256(key, label, control_type, context, options),
            "required": required,
            "control_type": control_type,
            "options": options,
        }

    @staticmethod
    def _fill(locator: Any, question: Mapping[str, Any], answer: str) -> bool:
        control_type = str(question["control_type"])
        try:
            if control_type == "select":
                try:
                    locator.select_option(value=answer)
                except Exception:
                    locator.select_option(label=answer)
            elif control_type == "input:checkbox":
                normalized = answer.strip().casefold()
                if normalized in {"true", "yes", "1", "on"}:
                    locator.check()
                elif normalized in {"false", "no", "0", "off"}:
                    locator.uncheck()
                else:
                    return False
            else:
                locator.fill(answer)
            return bool(locator.evaluate("el => el.checkValidity()"))
        except Exception:
            return False

    def process(self, application: Mapping[str, Any], stop_event: threading.Event) -> None:
        application_id = str(application["id"])
        if self._context is None:
            raise RuntimeError("controlled browser context is not open")
        page = self._context.new_page()
        try:
            if stop_event.is_set():
                self.journal.stop_pre_submit(application_id, "Stop requested before controlled form inspection")
                return
            target_url = require_controlled_fixture_url(application["target_url"])
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=8000)
            except Exception as exc:
                if _is_explicit_external_http_url(page.url):
                    self.journal.transition(application_id, ApplicationState.BLOCKED, "controlled fixture attempted to leave loopback")
                    return
                self.journal.retry_pre_submit(application_id, f"navigation failed: {exc}")
                return
            try:
                require_controlled_fixture_url(page.url)
            except ControlledFixtureViolation:
                self.journal.transition(application_id, ApplicationState.BLOCKED, "controlled fixture redirected outside loopback")
                return

            block = page.locator("[data-jobpilot-block]")
            if block.count():
                kind = str(block.first.get_attribute("data-jobpilot-block") or "challenge")[:80]
                self.journal.transition(application_id, ApplicationState.BLOCKED, f"controlled form stopped on {kind}")
                return
            if page.locator(":required:not([data-jobpilot-key])").count():
                self.journal.transition(application_id, ApplicationState.BLOCKED, "controlled form contains an unsupported required field")
                return

            self.journal.transition(application_id, ApplicationState.FILLING, "controlled form contract inspected")
            review: list[dict[str, Any]] = []
            fields = page.locator("[data-jobpilot-key]")
            for index in range(fields.count()):
                locator = fields.nth(index)
                try:
                    question = self._question(locator)
                except ControlledFixtureViolation as exc:
                    self.journal.transition(application_id, ApplicationState.BLOCKED, str(exc))
                    return
                answer = self.journal.approved_answer(str(question["question_key"]), str(question["context_sha256"]))
                if answer is None:
                    if bool(question["required"]):
                        review.append(question)
                    continue
                if not self._fill(locator, question, answer):
                    review.append(question)
            if review:
                self.journal.require_review(application_id, review, "mandatory controlled-form answer needs explicit review")
                return

            submit = page.locator("[data-jobpilot-submit]")
            if submit.count() != 1:
                self.journal.transition(application_id, ApplicationState.BLOCKED, "controlled form requires exactly one supported submit control")
                return
            self.journal.transition(application_id, ApplicationState.READY_TO_SUBMIT, "controlled form filled with exact-context approved answers")
            if stop_event.is_set():
                self.journal.stop_pre_submit(application_id, "Stop requested before submit boundary")
                return

            self.journal.transition(application_id, ApplicationState.SUBMITTING, "controlled fixture submit click started")
            try:
                submit.first.click(timeout=5000)
            except Exception as exc:
                self.journal.transition(application_id, ApplicationState.UNCERTAIN, f"submit click outcome ambiguous: {exc}")
                return
            self.journal.transition(application_id, ApplicationState.CONFIRMING, "submit click returned; awaiting explicit positive confirmation")
            try:
                page.wait_for_selector('[data-jobpilot-confirmation="success"]', state="attached", timeout=3000)
            except Exception as exc:
                self.journal.transition(application_id, ApplicationState.UNCERTAIN, f"explicit post-submit confirmation not observed: {exc}")
                return
            self.journal.transition(application_id, ApplicationState.CONFIRMED, "explicit positive controlled-fixture confirmation observed")
        except ControlledFixtureViolation as exc:
            state = ApplicationState(str(self.journal.attempt(application_id)["state"]))
            target = ApplicationState.UNCERTAIN if state in {ApplicationState.SUBMITTING, ApplicationState.CONFIRMING} else ApplicationState.BLOCKED
            self.journal.transition(application_id, target, str(exc))
        except Exception as exc:
            state = ApplicationState(str(self.journal.attempt(application_id)["state"]))
            if state in {ApplicationState.SUBMITTING, ApplicationState.CONFIRMING}:
                self.journal.transition(application_id, ApplicationState.UNCERTAIN, f"post-submit exception: {exc}")
            elif state in PRE_SUBMIT_STATES:
                self.journal.retry_pre_submit(application_id, f"pre-submit exception: {exc}")
            else:
                raise
        finally:
            page.close()


class ApplicationWorker:
    def __init__(self, paths: ManagedPaths, journal: ApplicationJournal, session_id: str) -> None:
        self.paths = paths
        self.journal = journal
        self.session_id = session_id
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread: threading.Thread | None = None
        self._current_application_id: str | None = None
        self._last_error: str | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            self._paused.clear()
            return
        self._stop.clear()
        self._paused.clear()
        self._thread = threading.Thread(target=self._run, name="jobpilot-application-worker", daemon=True)
        self._thread.start()

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def stop(self, timeout: float = 60.0) -> bool:
        self._stop.set()
        self._paused.clear()
        thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        if thread.is_alive() and self._current_application_id:
            attempt = self.journal.attempt(self._current_application_id)
            state = ApplicationState(str(attempt["state"]))
            if state in {ApplicationState.SUBMITTING, ApplicationState.CONFIRMING}:
                self.journal.transition(self._current_application_id, ApplicationState.UNCERTAIN, "confirmation window expired during Stop/Close")
            elif state in PRE_SUBMIT_STATES:
                self.journal.stop_pre_submit(self._current_application_id, "Stop/Close interrupted pre-submit work")
        return not thread.is_alive()

    def status(self) -> dict[str, Any]:
        thread = self._thread
        return {
            "alive": bool(thread and thread.is_alive()),
            "paused": self._paused.is_set(),
            "current_application_id": self._current_application_id,
            "last_error": self._last_error,
        }

    def _run(self) -> None:
        try:
            with ControlledFormEngine(self.paths, self.journal) as engine:
                while not self._stop.is_set():
                    if self._paused.is_set():
                        self._stop.wait(0.1)
                        continue
                    application = self.journal.claim_next(self.session_id)
                    if application is None:
                        self._stop.wait(0.1)
                        continue
                    self._current_application_id = str(application["id"])
                    engine.process(application, self._stop)
                    self._current_application_id = None
        except Exception as exc:
            self._last_error = str(exc)[:1000]
        finally:
            self._current_application_id = None
