from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from jobpilot.backup import BACKUP_FORMAT, BACKUP_FORMAT_VERSION, BackupManager
from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import Database

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def test_portable_backup_restore_roundtrip_preserves_machine_specific_state(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    archive = tmp_path / "portable.zip"
    with Database(paths.database_file, MIGRATIONS) as database:
        database.apply_migrations()
        manager = BackupManager(paths, MIGRATIONS)
        database.set_json_setting("phase9_test", {"value": "before"})
        (paths.master_documents / "resume.tex").write_text("immutable resume", encoding="utf-8")
        artifact = paths.application_artifacts / "fixture" / "manifest.json"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("{}", encoding="utf-8")
        manager.create(database, archive)
        database.set_json_setting("phase9_test", {"value": "after"})
        model = paths.models / "machine-specific.bin"
        model.write_bytes(b"keep-me")
        staged = manager.stage_restore(archive)
        assert staged["restart_required"] is True
        assert manager.status()["restore_pending"] is True

    restored = BackupManager.apply_pending_restore(paths, MIGRATIONS)
    assert restored is not None and restored["applied"] is True
    assert (paths.models / "machine-specific.bin").read_bytes() == b"keep-me"
    assert list(paths.backups.glob("pre-restore-*.zip"))
    with Database(paths.database_file, MIGRATIONS) as database:
        database.apply_migrations()
        assert database.get_json_setting("phase9_test") == {"value": "before"}
    assert (paths.master_documents / "resume.tex").read_text(encoding="utf-8") == "immutable resume"
    assert (paths.application_artifacts / "fixture" / "manifest.json").is_file()


def test_restore_rejects_machine_specific_payload(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    manager = BackupManager(paths, MIGRATIONS)
    archive = tmp_path / "unsafe.zip"
    manifest = {
        "format": BACKUP_FORMAT,
        "format_version": BACKUP_FORMAT_VERSION,
        "app_version": "future",
        "files": [{"path": "models/weights.bin", "bytes": 1, "sha256": "0" * 64}],
    }
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("manifest.json", json.dumps(manifest))
        bundle.writestr("payload/models/weights.bin", b"x")
    with pytest.raises(RuntimeError, match="machine-specific"):
        manager.stage_restore(archive)
