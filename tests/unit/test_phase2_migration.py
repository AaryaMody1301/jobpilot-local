from pathlib import Path

from jobpilot.storage.database import Database

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def test_phase2_migration_upgrades_phase1_database_without_losing_later_additive_migrations(tmp_path: Path) -> None:
    phase1 = tmp_path / "phase1-migrations"
    phase1.mkdir()
    for name in ("001_phase0_runtime.sql", "002_phase1_foundation.sql"):
        (phase1 / name).write_text((MIGRATIONS / name).read_text(encoding="utf-8"), encoding="utf-8")
    database_path = tmp_path / "jobpilot.sqlite3"
    with Database(database_path, phase1) as db:
        assert db.apply_migrations() == ["001_phase0_runtime.sql", "002_phase1_foundation.sql"]
        db.set_json_setting("targeting", {"notice_period_days": 30})
    with Database(database_path, MIGRATIONS) as db:
        assert db.apply_migrations() == [
            "003_phase2_resume_fact_bank.sql",
            "004_phase3_local_ai.sql",
            "005_phase4_tailoring.sql",
            "006_phase4_tailoring_safety.sql",
            "007_phase5_jobs.sql",
            "008_phase6_applications.sql",
        ]
        tables = {row[0] for row in db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"source_documents", "resume_baselines", "template_maps", "template_regions", "facts", "fact_versions", "fact_bank_state"}.issubset(tables)
        assert db.get_json_setting("targeting") == {"notice_period_days": 30}
        assert db.connection.execute("SELECT revision FROM fact_bank_state WHERE id = 1").fetchone()[0] == 0


def test_phase2_baseline_requires_explicit_offline_verification_columns(tmp_path: Path) -> None:
    with Database(tmp_path / "jobpilot.sqlite3", MIGRATIONS) as db:
        db.apply_migrations()
        columns = {row["name"] for row in db.connection.execute("PRAGMA table_info(resume_baselines)")}
        assert {"offline_verified", "last_compile_used_network"}.issubset(columns)
