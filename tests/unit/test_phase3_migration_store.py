from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from jobpilot.model.catalogue import get_model
from jobpilot.model.downloads import sha256_file, write_install_metadata
from jobpilot.model.manager import ModelManager
from jobpilot.model.store import ModelStore
from jobpilot.model.tooling import RuntimeInstallService
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import Database

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def test_phase3_migration_upgrades_phase2_database_without_losing_phase4_additions(tmp_path: Path) -> None:
    phase2 = tmp_path / "phase2-migrations"; phase2.mkdir()
    for name in ("001_phase0_runtime.sql", "002_phase1_foundation.sql", "003_phase2_resume_fact_bank.sql"):
        (phase2 / name).write_text((MIGRATIONS / name).read_text(encoding="utf-8"), encoding="utf-8")
    database_path = tmp_path / "jobpilot.sqlite3"
    with Database(database_path, phase2) as db:
        assert db.apply_migrations() == ["001_phase0_runtime.sql", "002_phase1_foundation.sql", "003_phase2_resume_fact_bank.sql"]
        db.set_json_setting("targeting", {"notice_period_days": 30})
    with Database(database_path, MIGRATIONS) as db:
        assert db.apply_migrations() == ["004_phase3_local_ai.sql", "005_phase4_tailoring.sql", "006_phase4_tailoring_safety.sql"]
        tables = {row[0] for row in db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {
            "hardware_snapshots", "runtime_installs", "model_installs", "model_evaluations",
            "model_state", "model_review_gates", "model_review_approvals",
        }.issubset(tables)
        assert db.get_json_setting("targeting") == {"notice_period_days": 30}
        state = db.connection.execute("SELECT auto_tailoring_model_install_id, selected_device_id FROM model_state WHERE id=1").fetchone()
        assert state[0] is None and state[1] is None


def test_model_manager_snapshot_never_downloads_or_enables_auto_tailoring(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal"); paths.create_all_roots()
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations(); manager = ModelManager(paths, db); state = manager.snapshot()
        assert state["catalogue"]["models"] and state["catalogue"]["runtimes"]
        assert state["model_installs"] == [] and state["runtime_installs"] == []
        assert state["auto_tailoring_enabled"] is False
        assert state["phase4_review_gate_required"] is True
        assert state["review_gate"] is None
        assert not any(paths.models.iterdir())


def test_selection_requires_passing_evaluation(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal"); paths.create_all_roots()
    artifact = get_model("qwen3-4b-q4_k_m")
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations(); store = ModelStore(db); manager = ModelManager(paths, db)
        store.upsert_model_install(install_id=artifact.install_id, catalogue_id=artifact.id, source_revision=artifact.source_revision, model_relpath="models/test/model.gguf", artifact_sha256="0" * 64, artifact_bytes=1, status="installed")
        store.upsert_runtime_install(install_id="llama-b10809-win-cpu-x64", catalogue_id="llama-b10809-win-cpu-x64", version="0.4.0", backend="cpu", install_relpath="tools/llama.cpp/test", executable_relpath="tools/llama.cpp/test/llama-server.exe", artifact_sha256="1" * 64, status="installed")
        with pytest.raises(RuntimeError, match="validated"):
            manager.select_for_phase4_review(artifact.install_id)


def _install_fake_model(paths: ManagedPaths, store: ModelStore, install_id: str, revision: str, *, app_managed: bool = True) -> Path:
    model_dir = paths.models / "logical-model" / revision
    model_dir.mkdir(parents=True)
    model_path = model_dir / "model.gguf"
    model_path.write_bytes(install_id.encode())
    store.upsert_model_install(
        install_id=install_id,
        catalogue_id="qwen3-4b-q4_k_m",
        source_revision=revision,
        model_relpath=str(model_path.relative_to(paths.root)),
        artifact_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
        artifact_bytes=model_path.stat().st_size,
        status="validated",
        app_managed=app_managed,
    )
    return model_path


def _install_fake_runtime(paths: ManagedPaths, store: ModelStore) -> None:
    runtime_root = paths.tools / "llama.cpp" / "runtime"
    executable = runtime_root / "bin" / "llama-server.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"controlled-runtime")
    runtime_digest = sha256_file(executable)
    write_install_metadata(runtime_root / "install.json", {"executable_sha256": runtime_digest})
    store.upsert_runtime_install(
        install_id="runtime", catalogue_id="llama-b10809-win-cpu-x64", version="0.4.0", backend="cpu",
        install_relpath=str(runtime_root.relative_to(paths.root)), executable_relpath=str(executable.relative_to(paths.root)),
        artifact_sha256="c" * 64, status="installed",
    )


def _passing_eval(store: ModelStore, model_id: str, *, evaluation_id: str, tps: float = 10.0, runtime: str = "runtime", device: str = "none") -> None:
    store.record_evaluation({
        "id": evaluation_id, "model_install_id": model_id, "runtime_install_id": runtime,
        "suite_version": "test", "backend": "cpu" if device == "none" else "vulkan", "device_id": device,
        "context_tokens": 4096, "elapsed_ms": 1000, "peak_rss_bytes": 1,
        "generation_tokens_per_second": tps, "prompt_tokens_per_second": 20.0,
        "structured_pass": True, "factual_pass": True, "tailoring_pass": True, "resource_pass": True,
        "overall_pass": True, "configuration": {"device_id": device}, "pressure": {"worst_pressure": "normal"}, "details": {},
    })


def _approve_five(store: ModelStore, model_id: str) -> None:
    for index in range(5):
        store.record_review_approval(model_id, f"resume-{index}")


def test_review_gate_counts_distinct_resume_approvals_and_cannot_be_boolean_bypassed(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal"); paths.create_all_roots()
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations(); store = ModelStore(db); manager = ModelManager(paths, db)
        old_path = _install_fake_model(paths, store, "old", "old-revision")
        new_path = _install_fake_model(paths, store, "new", "new-revision")
        _install_fake_runtime(paths, store)
        _passing_eval(store, "new", evaluation_id="eval-new", tps=11.0)

        _approve_five(store, "old")
        store.activate_after_review_gate("old")
        store.select_for_review("new", "runtime", "none")
        store.record_review_approval("new", "same-resume")
        store.record_review_approval("new", "same-resume")
        assert store.review_gate("new")["approved_distinct_resumes"] == 1
        with pytest.raises(RuntimeError, match="five-distinct-resume"):
            manager.finalize_after_phase4_review_gate("new", delete_previous_app_managed_weights=True)
        assert old_path.is_file() and new_path.is_file()

        for index in range(2, 6):
            store.record_review_approval("new", f"resume-{index}")
        assert store.review_gate("new")["complete"] is True
        manager.finalize_after_phase4_review_gate("new", delete_previous_app_managed_weights=True)
        assert not old_path.parent.exists() and new_path.is_file()
        assert store.model_state()["auto_tailoring_model_install_id"] == "new"
        assert store.model_install("old")["status"] == "retired"


def test_shared_or_non_app_managed_weights_are_never_deleted(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal"); paths.create_all_roots()
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations(); store = ModelStore(db); manager = ModelManager(paths, db)
        shared = _install_fake_model(paths, store, "shared", "shared-revision", app_managed=False)
        _install_fake_model(paths, store, "replacement", "replacement-revision")
        _install_fake_runtime(paths, store)
        _passing_eval(store, "replacement", evaluation_id="eval-replacement")
        _approve_five(store, "shared"); store.activate_after_review_gate("shared")
        store.select_for_review("replacement", "runtime", "none"); _approve_five(store, "replacement")
        with pytest.raises(RuntimeError, match="not app-managed"):
            manager.finalize_after_phase4_review_gate("replacement", delete_previous_app_managed_weights=True)
        assert shared.is_file()


def test_fastest_passing_evaluation_is_selected_by_measured_generation_speed(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal"); paths.create_all_roots()
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations(); store = ModelStore(db)
        _install_fake_model(paths, store, "model", "revision")
        for runtime in ("cpu", "vulkan"):
            store.upsert_runtime_install(install_id=runtime, catalogue_id="llama-b10809-win-cpu-x64", version="0.4.0", backend="cpu", install_relpath=f"tools/{runtime}", executable_relpath=f"tools/{runtime}/server.exe", artifact_sha256="d" * 64, status="installed")
        _passing_eval(store, "model", evaluation_id="slow", runtime="cpu", tps=8.0)
        _passing_eval(store, "model", evaluation_id="fast", runtime="vulkan", device="Vulkan0", tps=21.0)
        best = store.best_passing_evaluation("model")
        assert best is not None
        assert best["id"] == "fast" and best["device_id"] == "Vulkan0"


def test_rollback_restores_previous_validated_weights_without_deleting_failed_candidate(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal"); paths.create_all_roots()
    with Database(paths.database_file, MIGRATIONS) as db:
        db.apply_migrations(); store = ModelStore(db); manager = ModelManager(paths, db)
        stable = _install_fake_model(paths, store, "stable", "stable-revision")
        candidate = _install_fake_model(paths, store, "candidate", "candidate-revision")
        _approve_five(store, "stable"); store.activate_after_review_gate("stable")
        _approve_five(store, "candidate"); store.activate_after_review_gate("candidate")
        result = manager.rollback_after_activation_failure("candidate")
        assert result["restored_model_install_id"] == "stable"
        assert store.model_state()["auto_tailoring_model_install_id"] == "stable"
        assert stable.is_file() and candidate.is_file()


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
