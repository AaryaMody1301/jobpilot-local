from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from jobpilot.model.downloads import sha256_file, write_install_metadata
from jobpilot.model.manager import ModelManager
from jobpilot.model.store import ModelStore
from jobpilot.model.tooling import RuntimeInstallService
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import Database

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def test_phase3_migration_upgrades_phase2_database(tmp_path: Path) -> None:
    phase2 = tmp_path / "phase2-migrations"; phase2.mkdir()
    for name in ("001_phase0_runtime.sql", "002_phase1_foundation.sql", "003_phase2_resume_fact_bank.sql"):
        (phase2 / name).write_text((MIGRATIONS / name).read_text(encoding="utf-8"), encoding="utf-8")
    database_path = tmp_path / "jobpilot.sqlite3"
    with Database(database_path, phase2) as db:
        assert db.apply_migrations() == ["001_phase0_runtime.sql", "002_phase1_foundation.sql", "003_phase2_resume_fact_bank.sql"]
        db.set_json_setting("targeting", {"notice_period_days": 30})
    with Database(database_path, MIGRATIONS) as db:
        assert db.apply_migrations() == ["004_phase3_local_ai.sql"]
        tables = {row[0] for row in db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"hardware_snapshots", "runtime_installs", "model_installs", "model_evaluations", "model_state"}.issubset(tables)
        assert db.get_json_setting("targeting") == {"notice_period_days": 30}
        assert db.connection.execute("SELECT auto_tailoring_model_install_id FROM model_state WHERE id=1").fetchone()[0] is None


def test_model_manager_snapshot_never_downloads_or_enables_auto_tailoring(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal"); paths.create_all_roots()
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations(); manager = ModelManager(paths, db); state = manager.snapshot()
        assert state["catalogue"]["models"] and state["catalogue"]["runtimes"]
        assert state["model_installs"] == [] and state["runtime_installs"] == []
        assert state["auto_tailoring_enabled"] is False
        assert state["phase4_review_gate_required"] is True
        assert not any(paths.models.iterdir())


def test_selection_requires_passing_evaluation(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal"); paths.create_all_roots()
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations(); store = ModelStore(db); manager = ModelManager(paths, db)
        store.upsert_model_install(install_id="qwen3.5-0.8b-q4_0", catalogue_id="qwen3.5-0.8b-q4_0", source_revision="test", model_relpath="models/qwen3.5-0.8b-q4_0/model.gguf", artifact_sha256="0" * 64, artifact_bytes=1, status="installed")
        store.upsert_runtime_install(install_id="llama-b10809-win-cpu-x64", catalogue_id="llama-b10809-win-cpu-x64", version="0.4.0", backend="cpu", install_relpath="tools/llama.cpp/test", executable_relpath="tools/llama.cpp/test/llama-server.exe", artifact_sha256="1" * 64, status="installed")
        with pytest.raises(RuntimeError, match="validated"):
            manager.select_for_phase4_review("qwen3.5-0.8b-q4_0", "llama-b10809-win-cpu-x64")


def test_replacement_cleanup_stays_inside_app_model_root_and_review_gate_is_mandatory(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal"); paths.create_all_roots()
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations(); store = ModelStore(db); manager = ModelManager(paths, db)
        for model_id in ("old", "new"):
            model_dir = paths.models / model_id; model_dir.mkdir(); model_path = model_dir / "model.gguf"; model_path.write_bytes(model_id.encode())
            store.upsert_model_install(install_id=model_id, catalogue_id="qwen3.5-0.8b-q4_0", source_revision="test", model_relpath=str(model_path.relative_to(paths.root)), artifact_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(), artifact_bytes=model_path.stat().st_size, status="validated")
        runtime_root = paths.tools / "llama.cpp" / "runtime"; executable = runtime_root / "bin" / "llama-server.exe"; executable.parent.mkdir(parents=True); executable.write_bytes(b"controlled-runtime")
        runtime_digest = sha256_file(executable); write_install_metadata(runtime_root / "install.json", {"executable_sha256": runtime_digest})
        store.upsert_runtime_install(install_id="runtime", catalogue_id="llama-b10809-win-cpu-x64", version="0.4.0", backend="cpu", install_relpath=str(runtime_root.relative_to(paths.root)), executable_relpath=str(executable.relative_to(paths.root)), artifact_sha256="c" * 64, status="installed")
        store.record_evaluation({"id":"eval-new","model_install_id":"new","runtime_install_id":"runtime","suite_version":"test","backend":"cpu","context_tokens":4096,"elapsed_ms":1,"peak_rss_bytes":1,"structured_pass":True,"factual_pass":True,"tailoring_pass":True,"resource_pass":True,"overall_pass":True,"details":{}})
        store.activate_after_review_gate("old")
        with pytest.raises(RuntimeError, match="five-resume"):
            manager.finalize_after_phase4_review_gate("new", review_gate_passed=False, delete_previous_app_managed_weights=True)
        assert (paths.models / "old").is_dir()
        manager.finalize_after_phase4_review_gate("new", review_gate_passed=True, delete_previous_app_managed_weights=True)
        assert not (paths.models / "old").exists() and (paths.models / "new").is_dir()
        assert store.model_state()["auto_tailoring_model_install_id"] == "new"
        assert store.model_install("old")["status"] == "retired"


def test_rollback_restores_previous_validated_weights_without_deleting_failed_candidate(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal"); paths.create_all_roots()
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations(); store = ModelStore(db); manager = ModelManager(paths, db)
        for model_id in ("stable", "candidate"):
            model_dir = paths.models / model_id; model_dir.mkdir(); model_path = model_dir / "model.gguf"; model_path.write_bytes(model_id.encode())
            store.upsert_model_install(install_id=model_id, catalogue_id="qwen3.5-0.8b-q4_0", source_revision="test", model_relpath=str(model_path.relative_to(paths.root)), artifact_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(), artifact_bytes=model_path.stat().st_size, status="validated")
        store.activate_after_review_gate("stable"); store.activate_after_review_gate("candidate")
        result = manager.rollback_after_activation_failure("candidate")
        assert result["restored_model_install_id"] == "stable"
        assert store.model_state()["auto_tailoring_model_install_id"] == "stable"
        assert (paths.models / "candidate" / "model.gguf").is_file()


def test_runtime_executable_integrity_is_rechecked_before_use(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal"); paths.create_all_roots()
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations(); store = ModelStore(db); service = RuntimeInstallService(paths, store)
        runtime_root = paths.tools / "llama.cpp" / "integrity-test"; executable = runtime_root / "bin" / "llama-server.exe"; executable.parent.mkdir(parents=True); executable.write_bytes(b"controlled-runtime")
        digest = sha256_file(executable); write_install_metadata(runtime_root / "install.json", {"executable_sha256": digest})
        store.upsert_runtime_install(install_id="integrity-test", catalogue_id="llama-b10809-win-cpu-x64", version="0.4.0", backend="cpu", install_relpath=str(runtime_root.relative_to(paths.root)), executable_relpath=str(executable.relative_to(paths.root)), artifact_sha256="a" * 64, status="installed")
        assert service.status("integrity-test", verify_hash=True)["integrity"] == "verified"
        executable.write_bytes(b"tampered-runtime")
        assert service.status("integrity-test", verify_hash=True)["integrity"] == "failed"
        with pytest.raises(RuntimeError, match="integrity"):
            service.require_verified_executable("integrity-test")
