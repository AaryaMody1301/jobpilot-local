from pathlib import Path

import pytest

from jobpilot.domain.states import ApplicationState, InvalidTransition
from jobpilot.storage.database import Database, utc_now_text

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def _seed(db: Database) -> None:
    now = utc_now_text()
    with db.transaction() as connection:
        connection.execute("INSERT INTO runtime_sessions(id, state, started_at) VALUES ('session-1', 'running', ?)", (now,))
        connection.execute("INSERT INTO work_items(id, kind, state, lease_owner, updated_at) VALUES ('work-1', 'generation', 'running', 'session-1', ?)", (now,))
        for app_id, identity, state in (("app-submit", "job-submit", "submitting"), ("app-confirm", "job-confirm", "confirming"), ("app-fill", "job-fill", "filling")):
            connection.execute("INSERT INTO application_attempts(id, job_identity, state, updated_at) VALUES (?, ?, ?, ?)", (app_id, identity, state, now))


def test_migration_is_idempotent_and_enables_safety_pragmas(tmp_path: Path) -> None:
    with Database(tmp_path / "db.sqlite3", MIGRATIONS) as db:
        assert db.apply_migrations() == [
            "001_phase0_runtime.sql",
            "002_phase1_foundation.sql",
            "003_phase2_resume_fact_bank.sql",
            "004_phase3_local_ai.sql",
            "005_phase4_tailoring.sql",
            "006_phase4_tailoring_safety.sql",
        ]
        assert db.apply_migrations() == []
        assert db.connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert db.connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert db.connection.execute("PRAGMA synchronous").fetchone()[0] == 2


def test_unclean_recovery_requeues_only_pre_submit_work(tmp_path: Path) -> None:
    with Database(tmp_path / "db.sqlite3", MIGRATIONS) as db:
        db.apply_migrations()
        _seed(db)
        assert db.recover_interrupted_work() == {"crashed_sessions": 1, "requeued_work": 1, "uncertain_applications": 2}
        assert db.connection.execute("SELECT state FROM work_items WHERE id = 'work-1'").fetchone()[0] == "pending"
        assert db.connection.execute("SELECT state FROM application_attempts WHERE id = 'app-submit'").fetchone()[0] == "uncertain"
        assert db.connection.execute("SELECT state FROM application_attempts WHERE id = 'app-confirm'").fetchone()[0] == "uncertain"
        assert db.connection.execute("SELECT state FROM application_attempts WHERE id = 'app-fill'").fetchone()[0] == "filling"


def test_database_state_transition_rejects_retry_after_uncertain(tmp_path: Path) -> None:
    with Database(tmp_path / "db.sqlite3", MIGRATIONS) as db:
        db.apply_migrations()
        now = utc_now_text()
        db.connection.execute("INSERT INTO application_attempts(id, job_identity, state, updated_at) VALUES ('app-1', 'job-1', 'uncertain', ?)", (now,))
        with pytest.raises(InvalidTransition):
            db.journal_application_transition("app-1", ApplicationState.QUEUED, reason="must never auto-retry uncertain")
