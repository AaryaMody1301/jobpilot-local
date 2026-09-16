from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from jobpilot.runtime.paths import ManagedPaths
from jobpilot.storage.database import Database
from jobpilot.version import __version__

BACKUP_FORMAT = "jobpilot-portable-backup"
BACKUP_FORMAT_VERSION = 1
PORTABLE_ROOTS = ("db", "documents", "artifacts")
MAX_RESTORE_FILES = 50_000
MAX_RESTORE_BYTES = 8 * 1024**3


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _copy_regular_tree(source: Path, destination: Path) -> None:
    if not source.exists():
        destination.mkdir(parents=True, exist_ok=True)
        return
    destination.mkdir(parents=True, exist_ok=True)
    for item in sorted(source.rglob("*")):
        if item.is_symlink():
            raise RuntimeError(f"backup source contains a symbolic link: {item}")
        relative = item.relative_to(source)
        target = destination / relative
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


class BackupManager:
    """Portable user-data backup and restart-boundary restore.

    Models, tools, browser binaries/profile, caches, runtime files and logs are
    deliberately excluded because they are machine-specific or reproducible.
    """

    def __init__(self, paths: ManagedPaths, migrations_dir: Path) -> None:
        self.paths = paths
        self.migrations_dir = migrations_dir
        self.paths.create_all_roots()

    @property
    def request_file(self) -> Path:
        return self.paths.runtime / "restore-request.json"

    def status(self) -> dict[str, Any]:
        backups = sorted(self.paths.backups.glob("*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
        return {
            "format_version": BACKUP_FORMAT_VERSION,
            "backup_directory": str(self.paths.backups),
            "restore_pending": self.request_file.is_file(),
            "local_backups": len(backups),
            "latest_backup": str(backups[0]) if backups else None,
            "portable_roots": list(PORTABLE_ROOTS),
            "excluded_machine_specific": ["models", "tools", "browsers", "browser-profile", "tectonic", "cache", "runtime", "logs"],
        }

    def create(self, database: Database, destination: Path) -> dict[str, Any]:
        destination = destination.expanduser().resolve(strict=False)
        if destination.suffix.lower() != ".zip":
            destination = destination.with_suffix(".zip")
        for root_name in PORTABLE_ROOTS:
            portable_root = (self.paths.root / root_name).resolve(strict=False)
            if _is_relative_to(destination, portable_root):
                raise ValueError("backup destination cannot be inside portable JobPilot data")
        destination.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="backup-build-", dir=self.paths.backups) as temp_dir:
            stage = Path(temp_dir)
            payload = stage / "payload"
            self._snapshot_database(database.connection, payload / "db" / "jobpilot.sqlite3", lock=database._lock)
            _copy_regular_tree(self.paths.documents, payload / "documents")
            _copy_regular_tree(self.paths.artifacts, payload / "artifacts")
            manifest = self._manifest(payload)
            archive = stage / "backup.zip"
            self._write_archive(archive, payload, manifest)
            temporary_destination = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
            shutil.copy2(archive, temporary_destination)
            os.replace(temporary_destination, destination)

        return {
            "path": str(destination),
            "sha256": _sha256(destination),
            "bytes": destination.stat().st_size,
            "created_at": manifest["created_at"],
            "format_version": BACKUP_FORMAT_VERSION,
        }

    def stage_restore(self, archive: Path) -> dict[str, Any]:
        archive = archive.expanduser().resolve(strict=True)
        if self.request_file.exists():
            raise RuntimeError("a restore is already staged; restart JobPilot before staging another")
        restore_root = self.paths.runtime / "restore"
        restore_root.mkdir(parents=True, exist_ok=True)
        stage = restore_root / f"staged-{uuid.uuid4().hex}"
        stage.mkdir(parents=True)
        try:
            manifest = self._extract_verified(archive, stage)
            self._validate_database(stage / "payload" / "db" / "jobpilot.sqlite3")
            request = {
                "format": BACKUP_FORMAT,
                "format_version": BACKUP_FORMAT_VERSION,
                "staged_relpath": stage.relative_to(self.paths.root).as_posix(),
                "archive_sha256": _sha256(archive),
                "source_app_version": manifest.get("app_version"),
                "staged_at": _utc_now(),
            }
            temporary = self.request_file.with_suffix(".tmp")
            temporary.write_text(json.dumps(request, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, self.request_file)
        except Exception:
            shutil.rmtree(stage, ignore_errors=True)
            raise
        return {
            "staged": True,
            "source_app_version": manifest.get("app_version"),
            "restart_required": True,
            "archive_sha256": request["archive_sha256"],
        }

    @classmethod
    def apply_pending_restore(cls, paths: ManagedPaths, migrations_dir: Path) -> dict[str, Any] | None:
        paths.create_all_roots()
        manager = cls(paths, migrations_dir)
        if not manager.request_file.is_file():
            return None
        request = json.loads(manager.request_file.read_text(encoding="utf-8"))
        if request.get("format") != BACKUP_FORMAT or int(request.get("format_version", -1)) != BACKUP_FORMAT_VERSION:
            raise RuntimeError("pending restore request has an unsupported format")
        staged_relative = PurePosixPath(str(request.get("staged_relpath") or ""))
        if staged_relative.is_absolute() or ".." in staged_relative.parts:
            raise RuntimeError("pending restore path is unsafe")
        stage = (paths.root / Path(*staged_relative.parts)).resolve(strict=False)
        restore_root = (paths.runtime / "restore").resolve(strict=False)
        if not _is_relative_to(stage, restore_root) or not stage.is_dir():
            raise RuntimeError("pending restore staging directory is missing or outside the managed runtime root")
        manifest_path = stage / "manifest.json"
        payload = stage / "payload"
        manifest = manager._validate_extracted(payload, manifest_path)
        manager._validate_database(payload / "db" / "jobpilot.sqlite3")

        safety_backup: Path | None = None
        if paths.database_file.is_file():
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            safety_backup = paths.backups / f"pre-restore-{stamp}-{uuid.uuid4().hex[:8]}.zip"
            manager._create_offline(safety_backup)

        rollback = paths.runtime / f"restore-rollback-{uuid.uuid4().hex}"
        rollback.mkdir(parents=True)
        installed: list[str] = []
        moved: list[str] = []
        try:
            for root_name in PORTABLE_ROOTS:
                current = paths.root / root_name
                replacement = payload / root_name
                replacement.mkdir(parents=True, exist_ok=True)
                if current.exists():
                    os.replace(current, rollback / root_name)
                    moved.append(root_name)
                os.replace(replacement, current)
                installed.append(root_name)
        except Exception:
            for root_name in reversed(installed):
                current = paths.root / root_name
                if current.exists():
                    shutil.rmtree(current) if current.is_dir() else current.unlink()
            for root_name in reversed(moved):
                previous = rollback / root_name
                if previous.exists():
                    os.replace(previous, paths.root / root_name)
            raise
        else:
            shutil.rmtree(rollback, ignore_errors=True)
            shutil.rmtree(stage, ignore_errors=True)
            manager.request_file.unlink(missing_ok=True)

        return {
            "applied": True,
            "source_app_version": manifest.get("app_version"),
            "safety_backup": str(safety_backup) if safety_backup else None,
            "applied_at": _utc_now(),
        }

    def _create_offline(self, destination: Path) -> None:
        with tempfile.TemporaryDirectory(prefix="pre-restore-", dir=self.paths.backups) as temp_dir:
            stage = Path(temp_dir)
            payload = stage / "payload"
            source = sqlite3.connect(self.paths.database_file)
            try:
                self._snapshot_database(source, payload / "db" / "jobpilot.sqlite3")
            finally:
                source.close()
            _copy_regular_tree(self.paths.documents, payload / "documents")
            _copy_regular_tree(self.paths.artifacts, payload / "artifacts")
            manifest = self._manifest(payload)
            self._write_archive(destination, payload, manifest)

    @staticmethod
    def _snapshot_database(source: sqlite3.Connection, destination: Path, *, lock: Any | None = None) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        target = sqlite3.connect(destination)
        try:
            if lock is None:
                source.backup(target)
            else:
                with lock:
                    source.backup(target)
        finally:
            target.close()

    def _manifest(self, payload: Path) -> dict[str, Any]:
        files: list[dict[str, Any]] = []
        for path in sorted(payload.rglob("*")):
            if path.is_symlink():
                raise RuntimeError(f"backup payload contains a symbolic link: {path}")
            if not path.is_file():
                continue
            relative = path.relative_to(payload).as_posix()
            files.append({"path": relative, "bytes": path.stat().st_size, "sha256": _sha256(path)})
        database = payload / "db" / "jobpilot.sqlite3"
        migrations = self._database_migrations(database)
        return {
            "format": BACKUP_FORMAT,
            "format_version": BACKUP_FORMAT_VERSION,
            "app_version": __version__,
            "created_at": _utc_now(),
            "portable_roots": list(PORTABLE_ROOTS),
            "schema_migrations": migrations,
            "files": files,
        }

    @staticmethod
    def _write_archive(archive: Path, payload: Path, manifest: dict[str, Any]) -> None:
        archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
            bundle.writestr("manifest.json", json.dumps(manifest, sort_keys=True, indent=2) + "\n")
            for item in manifest["files"]:
                bundle.write(payload / item["path"], f"payload/{item['path']}")

    def _extract_verified(self, archive: Path, stage: Path) -> dict[str, Any]:
        with zipfile.ZipFile(archive, "r") as bundle:
            infos = bundle.infolist()
            files = [info for info in infos if not info.is_dir()]
            if len(files) > MAX_RESTORE_FILES:
                raise RuntimeError("backup contains too many files")
            if sum(info.file_size for info in files) > MAX_RESTORE_BYTES:
                raise RuntimeError("backup expands beyond the restore size limit")
            for info in infos:
                self._validate_zip_name(info)
            try:
                manifest_info = bundle.getinfo("manifest.json")
            except KeyError as exc:
                raise RuntimeError("backup manifest is missing") from exc
            if manifest_info.file_size > 4 * 1024 * 1024:
                raise RuntimeError("backup manifest is unexpectedly large")
            manifest = json.loads(bundle.read(manifest_info).decode("utf-8"))
            entries = self._validate_manifest(manifest)
            actual = {info.filename for info in files if info.filename != "manifest.json"}
            expected = {f"payload/{path}" for path in entries}
            if actual != expected:
                raise RuntimeError("backup file list does not match its manifest")

            payload = stage / "payload"
            for relative, entry in entries.items():
                info = bundle.getinfo(f"payload/{relative}")
                target = (payload / Path(*PurePosixPath(relative).parts)).resolve(strict=False)
                if not _is_relative_to(target, payload.resolve(strict=False)):
                    raise RuntimeError("backup member escaped the restore payload")
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                written = 0
                with bundle.open(info, "r") as source, target.open("wb") as output:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        output.write(chunk)
                        digest.update(chunk)
                        written += len(chunk)
                if written != int(entry["bytes"]) or digest.hexdigest() != entry["sha256"]:
                    raise RuntimeError(f"backup member failed integrity verification: {relative}")
            (stage / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            return manifest

    def _validate_extracted(self, payload: Path, manifest_path: Path) -> dict[str, Any]:
        if not payload.is_dir() or not manifest_path.is_file():
            raise RuntimeError("staged restore is incomplete")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = self._validate_manifest(manifest)
        actual: set[str] = set()
        for path in payload.rglob("*"):
            if path.is_symlink():
                raise RuntimeError("staged restore contains a symbolic link")
            if path.is_file():
                actual.add(path.relative_to(payload).as_posix())
        if actual != set(entries):
            raise RuntimeError("staged restore file list changed after verification")
        for relative, entry in entries.items():
            path = payload / Path(*PurePosixPath(relative).parts)
            if path.stat().st_size != int(entry["bytes"]) or _sha256(path) != entry["sha256"]:
                raise RuntimeError(f"staged restore failed integrity verification: {relative}")
        return manifest

    @staticmethod
    def _validate_zip_name(info: zipfile.ZipInfo) -> None:
        name = info.filename
        path = PurePosixPath(name)
        mode = (info.external_attr >> 16) & 0o170000
        if path.is_absolute() or ".." in path.parts or "\\" in name or mode == stat.S_IFLNK:
            raise RuntimeError(f"unsafe backup member: {name}")

    @staticmethod
    def _validate_manifest(manifest: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(manifest, dict) or manifest.get("format") != BACKUP_FORMAT:
            raise RuntimeError("backup format is not JobPilot portable backup")
        if int(manifest.get("format_version", -1)) != BACKUP_FORMAT_VERSION:
            raise RuntimeError("backup format version is unsupported")
        raw_files = manifest.get("files")
        if not isinstance(raw_files, list):
            raise RuntimeError("backup manifest file list is invalid")
        entries: dict[str, dict[str, Any]] = {}
        for entry in raw_files:
            if not isinstance(entry, dict):
                raise RuntimeError("backup manifest contains an invalid file entry")
            relative = str(entry.get("path") or "")
            posix = PurePosixPath(relative)
            if posix.is_absolute() or ".." in posix.parts or "\\" in relative or not posix.parts:
                raise RuntimeError("backup manifest contains an unsafe path")
            if posix.parts[0] not in PORTABLE_ROOTS:
                raise RuntimeError("backup contains machine-specific or unknown data")
            if relative in entries:
                raise RuntimeError("backup manifest contains a duplicate path")
            digest = str(entry.get("sha256") or "")
            size = entry.get("bytes")
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest) or not isinstance(size, int) or size < 0:
                raise RuntimeError("backup manifest contains invalid integrity metadata")
            entries[relative] = entry
        if "db/jobpilot.sqlite3" not in entries:
            raise RuntimeError("backup database snapshot is missing")
        return entries

    def _validate_database(self, database_path: Path) -> None:
        if not database_path.is_file():
            raise RuntimeError("backup database snapshot is missing")
        connection = sqlite3.connect(database_path)
        try:
            check = connection.execute("PRAGMA quick_check").fetchone()
            if check is None or str(check[0]).lower() != "ok":
                raise RuntimeError("backup database integrity check failed")
            migrations = {str(row[0]) for row in connection.execute("SELECT version FROM schema_migrations")}
        except sqlite3.DatabaseError as exc:
            raise RuntimeError("backup database is not a valid JobPilot database") from exc
        finally:
            connection.close()
        known = {path.name for path in self.migrations_dir.glob("*.sql")}
        unknown = sorted(migrations - known)
        if unknown:
            raise RuntimeError(f"backup was created by a newer incompatible schema: {', '.join(unknown)}")

    @staticmethod
    def _database_migrations(database_path: Path) -> list[str]:
        connection = sqlite3.connect(database_path)
        try:
            return [str(row[0]) for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
        finally:
            connection.close()
