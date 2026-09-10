from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from jobpilot.domain.states import APPLICATION_MACHINE, ApplicationState


class MigrationError(RuntimeError):
    pass


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path, migrations_dir: Path) -> None:
        self.path = path
        self.migrations_dir = migrations_dir
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = FULL")
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except Exception:
            self.connection.execute("ROLLBACK")
            raise
        else:
            self.connection.execute("COMMIT")

    def apply_migrations(self) -> list[str]:
        applied = {row["version"] for row in self.connection.execute("SELECT version FROM schema_migrations")}
        newly_applied: list[str] = []
        for migration in sorted(self.migrations_dir.glob("*.sql")):
            version = migration.name
            if version in applied:
                continue
            sql = migration.read_text(encoding="utf-8")
            safe_version = version.replace("'", "''")
            safe_time = utc_now_text().replace("'", "''")
            script = "BEGIN IMMEDIATE;\n" + sql + f"\nINSERT INTO schema_migrations(version, applied_at) VALUES ('{safe_version}', '{safe_time}');\n" + "COMMIT;"
            try:
                self.connection.executescript(script)
            except sqlite3.DatabaseError as exc:
                if self.connection.in_transaction:
                    self.connection.execute("ROLLBACK")
                raise MigrationError(f"failed migration {version}: {exc}") from exc
            newly_applied.append(version)
        return newly_applied

    def journal_application_transition(self, application_id: str, target: ApplicationState, *, reason: str) -> None:
        with self.transaction() as connection:
            row = connection.execute("SELECT state FROM application_attempts WHERE id = ?", (application_id,)).fetchone()
            if row is None:
                raise KeyError(application_id)
            current = ApplicationState(row["state"])
            APPLICATION_MACHINE.require_transition(current, target)
            now = utc_now_text()
            submit_started = now if target is ApplicationState.SUBMITTING else None
            confirmed = now if target is ApplicationState.CONFIRMED else None
            connection.execute("UPDATE application_attempts SET state = ?, submit_started_at = COALESCE(submit_started_at, ?), confirmed_at = COALESCE(confirmed_at, ?), updated_at = ? WHERE id = ?", (target.value, submit_started, confirmed, now, application_id))
            connection.execute("INSERT INTO application_events(application_id, from_state, to_state, reason, created_at) VALUES (?, ?, ?, ?, ?)", (application_id, current.value, target.value, reason, now))

    def recover_interrupted_work(self) -> dict[str, int]:
        """Recover after an unclean process exit without retrying uncertain submits."""
        now = utc_now_text()
        with self.transaction() as connection:
            crashed_sessions = connection.execute("UPDATE runtime_sessions SET state = 'crashed', ended_at = ? WHERE ended_at IS NULL AND state <> 'exited'", (now,)).rowcount
            requeued_work = connection.execute("UPDATE work_items SET state = 'pending', lease_owner = NULL, updated_at = ? WHERE state = 'running'", (now,)).rowcount
            interrupted = connection.execute("SELECT id, state FROM application_attempts WHERE state IN ('submitting', 'confirming')").fetchall()
            for row in interrupted:
                connection.execute("UPDATE application_attempts SET state = 'uncertain', updated_at = ? WHERE id = ?", (now, row["id"]))
                connection.execute("INSERT INTO application_events(application_id, from_state, to_state, reason, created_at) VALUES (?, ?, 'uncertain', 'unclean shutdown after submit boundary', ?)", (row["id"], row["state"], now))
        return {"crashed_sessions": int(crashed_sessions), "requeued_work": int(requeued_work), "uncertain_applications": len(interrupted)}
