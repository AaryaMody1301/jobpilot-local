from pathlib import Path

from jobpilot.domain.states import SessionState
from jobpilot.storage.database import Database

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"
ALL = [
    "001_phase0_runtime.sql",
    "002_phase1_foundation.sql",
    "003_phase2_resume_fact_bank.sql",
    "004_phase3_local_ai.sql",
    "005_phase4_tailoring.sql",
    "006_phase4_tailoring_safety.sql",
]


def test_phase1_settings_and_session_persist(tmp_path: Path) -> None:
    database_path = tmp_path / "jobpilot.sqlite3"
    with Database(database_path, MIGRATIONS) as db:
        assert db.apply_migrations() == ALL
        db.set_json_setting("targeting", {"notice_period_days": 30})
        db.create_runtime_session("session-1")
        db.set_runtime_session_state("session-1", SessionState.RUNNING)
        db.finish_runtime_session("session-1")
    with Database(database_path, MIGRATIONS) as db:
        assert db.apply_migrations() == []
        assert db.get_json_setting("targeting") == {"notice_period_days": 30}
        row = db.connection.execute("SELECT state, ended_at FROM runtime_sessions WHERE id = 'session-1'").fetchone()
        assert row["state"] == "exited"
        assert row["ended_at"] is not None


def test_sample_work_is_seeded_once_and_resettable(tmp_path: Path) -> None:
    with Database(tmp_path / "jobpilot.sqlite3", MIGRATIONS) as db:
        db.apply_migrations()
        db.seed_sample_work(); db.seed_sample_work()
        assert len(db.list_sample_work()) == 4
        db.create_runtime_session("session-1")
        assert db.claim_next_sample_work("session-1") is not None
        assert sum(item["state"] == "running" for item in db.list_sample_work()) == 1
        db.requeue_owned_sample_work("session-1")
        assert all(item["state"] == "pending" for item in db.list_sample_work())


def test_phase1_migration_upgrades_existing_phase0_database(tmp_path: Path) -> None:
    phase0_migrations = tmp_path / "phase0-migrations"
    phase0_migrations.mkdir()
    source = MIGRATIONS / "001_phase0_runtime.sql"
    (phase0_migrations / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    database_path = tmp_path / "jobpilot.sqlite3"
    with Database(database_path, phase0_migrations) as db:
        assert db.apply_migrations() == ["001_phase0_runtime.sql"]
        db.connection.execute("INSERT INTO work_items(id, kind, state, updated_at) VALUES ('old-work', 'phase0', 'pending', 'now')")
    with Database(database_path, MIGRATIONS) as db:
        assert db.apply_migrations() == [
            "002_phase1_foundation.sql",
            "003_phase2_resume_fact_bank.sql",
            "004_phase3_local_ai.sql",
            "005_phase4_tailoring.sql",
            "006_phase4_tailoring_safety.sql",
        ]
        columns = {row["name"] for row in db.connection.execute("PRAGMA table_info(work_items)")}
        assert {"label", "is_sample"}.issubset(columns)
        old = db.connection.execute("SELECT state, is_sample FROM work_items WHERE id = 'old-work'").fetchone()
        assert old["state"] == "pending"
        assert old["is_sample"] == 0
