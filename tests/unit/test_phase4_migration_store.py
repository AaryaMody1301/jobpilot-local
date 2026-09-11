from __future__ import annotations

from pathlib import Path

import pytest

from jobpilot.resume.jd import normalize_job_description
from jobpilot.resume.tailoring_store import TailoringStore
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import Database

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def test_phase4_migration_upgrades_phase3_database_and_preserves_state(tmp_path: Path) -> None:
    phase3 = tmp_path / "phase3-migrations"
    phase3.mkdir()
    for name in (
        "001_phase0_runtime.sql",
        "002_phase1_foundation.sql",
        "003_phase2_resume_fact_bank.sql",
        "004_phase3_local_ai.sql",
    ):
        (phase3 / name).write_text((MIGRATIONS / name).read_text(encoding="utf-8"), encoding="utf-8")
    database_path = tmp_path / "jobpilot.sqlite3"
    with Database(database_path, phase3) as db:
        assert db.apply_migrations() == [
            "001_phase0_runtime.sql",
            "002_phase1_foundation.sql",
            "003_phase2_resume_fact_bank.sql",
            "004_phase3_local_ai.sql",
        ]
        db.set_json_setting("targeting", {"notice_period_days": 30})
    with Database(database_path, MIGRATIONS) as db:
        assert db.apply_migrations() == ["005_phase4_tailoring.sql", "006_phase4_tailoring_safety.sql"]
        tables = {row[0] for row in db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"manual_job_descriptions", "tailored_resumes"}.issubset(tables)
        tailored_columns = {row["name"] for row in db.connection.execute("PRAGMA table_info(tailored_resumes)")}
        assert {
            "template_map_sha256", "baseline_sha256", "profile_sha256", "review_context_sha256",
            "manifest_relpath", "manifest_sha256",
        }.issubset(tailored_columns)
        gate_columns = {row["name"] for row in db.connection.execute("PRAGMA table_info(model_review_gates)")}
        assert "review_context_sha256" in gate_columns
        assert db.get_json_setting("targeting") == {"notice_period_days": 30}
        state = db.connection.execute("SELECT auto_tailoring_model_install_id FROM model_state WHERE id=1").fetchone()
        assert state[0] is None


def test_tailoring_store_deduplicates_jd_and_refuses_paths_outside_app_root(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    paths.create_all_roots()
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations()
        store = TailoringStore(db, paths.root)
        jd = normalize_job_description("SQL data engineer role")
        first = store.register_jd(jd)
        second = store.register_jd(jd)
        assert first["id"] == second["id"]
        assert len(store.list_jds()) == 1
        with pytest.raises(ValueError, match="escaped"):
            store.absolute_path("../outside.pdf")
