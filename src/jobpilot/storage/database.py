from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from jobpilot.domain.states import APPLICATION_MACHINE, ApplicationState, SessionState


class MigrationError(RuntimeError):
    pass


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    """Single local SQLite connection serialized for pywebview/background threads."""

    def __init__(self, path: Path, migrations_dir: Path) -> None:
        self.path = path
        self.migrations_dir = migrations_dir
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(
            self.path,
            isolation_level=None,
            check_same_thread=False,
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = FULL")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield self.connection
            except Exception:
                self.connection.execute("ROLLBACK")
                raise
            else:
                self.connection.execute("COMMIT")

    def apply_migrations(self) -> list[str]:
        with self._lock:
            applied = {
                row["version"]
                for row in self.connection.execute("SELECT version FROM schema_migrations")
            }
            newly_applied: list[str] = []
            for migration in sorted(self.migrations_dir.glob("*.sql")):
                version = migration.name
                if version in applied:
                    continue
                sql = migration.read_text(encoding="utf-8")
                safe_version = version.replace("'", "''")
                safe_time = utc_now_text().replace("'", "''")
                script = (
                    "BEGIN IMMEDIATE;\n"
                    + sql
                    + f"\nINSERT INTO schema_migrations(version, applied_at) VALUES ('{safe_version}', '{safe_time}');\n"
                    + "COMMIT;"
                )
                try:
                    self.connection.executescript(script)
                except sqlite3.DatabaseError as exc:
                    if self.connection.in_transaction:
                        self.connection.execute("ROLLBACK")
                    raise MigrationError(f"failed migration {version}: {exc}") from exc
                newly_applied.append(version)
            return newly_applied

    def get_json_setting(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.connection.execute(
                "SELECT value_json FROM app_settings WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        value = json.loads(row["value_json"])
        if not isinstance(value, dict):
            raise ValueError(f"setting {key!r} must contain a JSON object")
        return value

    def set_json_setting(self, key: str, value: Mapping[str, Any]) -> None:
        encoded = json.dumps(dict(value), sort_keys=True, separators=(",", ":"))
        now = utc_now_text()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO app_settings(key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key, encoded, now),
            )

    def create_runtime_session(self, session_id: str) -> None:
        now = utc_now_text()
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO runtime_sessions(id, state, started_at) VALUES (?, 'idle', ?)",
                (session_id, now),
            )

    def set_runtime_session_state(self, session_id: str, state: SessionState) -> None:
        with self.transaction() as connection:
            updated = connection.execute(
                "UPDATE runtime_sessions SET state = ? WHERE id = ? AND ended_at IS NULL",
                (state.value, session_id),
            ).rowcount
            if updated != 1:
                raise KeyError(session_id)

    def finish_runtime_session(self, session_id: str) -> None:
        now = utc_now_text()
        with self.transaction() as connection:
            updated = connection.execute(
                "UPDATE runtime_sessions SET state = 'exited', ended_at = ? WHERE id = ? AND ended_at IS NULL",
                (now, session_id),
            ).rowcount
            if updated != 1:
                raise KeyError(session_id)

    def seed_sample_work(self) -> None:
        now = utc_now_text()
        rows = (
            ("sample-001", "SAMPLE - verify local lifecycle state"),
            ("sample-002", "SAMPLE - verify settings persistence"),
            ("sample-003", "SAMPLE - verify pause and resume"),
            ("sample-004", "SAMPLE - verify clean stop"),
        )
        with self.transaction() as connection:
            for work_id, label in rows:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO work_items(
                        id, kind, state, lease_owner, updated_at, label, is_sample
                    ) VALUES (?, 'phase1_sample', 'pending', NULL, ?, ?, 1)
                    """,
                    (work_id, now, label),
                )

    def list_sample_work(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT id, label, state, lease_owner, updated_at
                  FROM work_items
                 WHERE is_sample = 1
                 ORDER BY id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def claim_next_sample_work(self, session_id: str) -> dict[str, Any] | None:
        now = utc_now_text()
        with self.transaction() as connection:
            row = connection.execute(
                """
                SELECT id, label FROM work_items
                 WHERE is_sample = 1 AND state = 'pending'
                 ORDER BY id LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            updated = connection.execute(
                """
                UPDATE work_items
                   SET state = 'running', lease_owner = ?, updated_at = ?
                 WHERE id = ? AND state = 'pending'
                """,
                (session_id, now, row["id"]),
            ).rowcount
            if updated != 1:
                return None
            return {"id": row["id"], "label": row["label"]}

    def complete_sample_work(self, work_id: str, session_id: str) -> None:
        now = utc_now_text()
        with self.transaction() as connection:
            updated = connection.execute(
                """
                UPDATE work_items
                   SET state = 'done', lease_owner = NULL, updated_at = ?
                 WHERE id = ? AND state = 'running' AND lease_owner = ? AND is_sample = 1
                """,
                (now, work_id, session_id),
            ).rowcount
            if updated != 1:
                raise KeyError(work_id)

    def requeue_owned_sample_work(self, session_id: str) -> int:
        now = utc_now_text()
        with self.transaction() as connection:
            return int(
                connection.execute(
                    """
                    UPDATE work_items
                       SET state = 'pending', lease_owner = NULL, updated_at = ?
                     WHERE state = 'running' AND lease_owner = ? AND is_sample = 1
                    """,
                    (now, session_id),
                ).rowcount
            )

    def reset_sample_work(self) -> None:
        now = utc_now_text()
        with self.transaction() as connection:
            connection.execute(
                """
                UPDATE work_items
                   SET state = 'pending', lease_owner = NULL, updated_at = ?
                 WHERE is_sample = 1
                """,
                (now,),
            )

    def record_foundation_activity(self, session_id: str, event_type: str, message: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO foundation_activity(session_id, event_type, message, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, event_type, message, utc_now_text()),
            )

    def recent_foundation_activity(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT session_id, event_type, message, created_at
                  FROM foundation_activity
                 ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def journal_application_transition(
        self,
        application_id: str,
        target: ApplicationState,
        *,
        reason: str,
    ) -> None:
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT state FROM application_attempts WHERE id = ?",
                (application_id,),
            ).fetchone()
            if row is None:
                raise KeyError(application_id)
            current = ApplicationState(row["state"])
            APPLICATION_MACHINE.require_transition(current, target)
            now = utc_now_text()
            submit_started = now if target is ApplicationState.SUBMITTING else None
            confirmed = now if target is ApplicationState.CONFIRMED else None
            connection.execute(
                """
                UPDATE application_attempts
                   SET state = ?,
                       submit_started_at = COALESCE(submit_started_at, ?),
                       confirmed_at = COALESCE(confirmed_at, ?),
                       updated_at = ?
                 WHERE id = ?
                """,
                (target.value, submit_started, confirmed, now, application_id),
            )
            connection.execute(
                """
                INSERT INTO application_events(
                    application_id, from_state, to_state, reason, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (application_id, current.value, target.value, reason, now),
            )

    def recover_interrupted_work(self) -> dict[str, int]:
        """Recover after an unclean process exit without retrying uncertain submits."""
        now = utc_now_text()
        with self.transaction() as connection:
            crashed_sessions = connection.execute(
                """
                UPDATE runtime_sessions
                   SET state = 'crashed', ended_at = ?
                 WHERE ended_at IS NULL AND state <> 'exited'
                """,
                (now,),
            ).rowcount
            requeued_work = connection.execute(
                """
                UPDATE work_items
                   SET state = 'pending', lease_owner = NULL, updated_at = ?
                 WHERE state = 'running'
                """,
                (now,),
            ).rowcount
            interrupted = connection.execute(
                """
                SELECT id, state FROM application_attempts
                 WHERE state IN ('submitting', 'confirming')
                """
            ).fetchall()
            for row in interrupted:
                connection.execute(
                    "UPDATE application_attempts SET state = 'uncertain', updated_at = ? WHERE id = ?",
                    (now, row["id"]),
                )
                connection.execute(
                    """
                    INSERT INTO application_events(
                        application_id, from_state, to_state, reason, created_at
                    ) VALUES (?, ?, 'uncertain', 'unclean shutdown after submit boundary', ?)
                    """,
                    (row["id"], row["state"], now),
                )
        return {
            "crashed_sessions": int(crashed_sessions),
            "requeued_work": int(requeued_work),
            "uncertain_applications": len(interrupted),
        }
