from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from threading import Event
from typing import Any

from jobpilot.model.catalogue import ModelArtifact, RuntimeArtifact
from jobpilot.model.downloads import download_verified, extract_zip_verified, sha256_file, write_install_metadata
from jobpilot.model.store import ModelStore
from jobpilot.runtime.paths import ManagedPaths

_DEVICE_RE = re.compile(
    r"^(?P<id>[A-Za-z][A-Za-z0-9_-]*\d+):\s*(?P<name>.+?)\s*\((?P<total>\d+)\s+MiB,\s*(?P<free>\d+)\s+MiB\s+free\)\s*$"
)
_MIB = 1024**2


def parse_llama_devices(raw: str) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for original in raw.splitlines():
        line = original.strip()
        match = _DEVICE_RE.match(line)
        if not match:
            continue
        devices.append(
            {
                "id": match.group("id"),
                "name": match.group("name").strip(),
                "total_memory_bytes": int(match.group("total")) * _MIB,
                "free_memory_bytes": int(match.group("free")) * _MIB,
                "evidence": line,
            }
        )
    return devices


class RuntimeInstallService:
    def __init__(self, paths: ManagedPaths, store: ModelStore) -> None:
        self.paths = paths
        self.store = store

    def install(self, artifact: RuntimeArtifact, cancel_event: Event) -> dict[str, Any]:
        if os.name != "nt":
            raise RuntimeError("llama.cpp managed runtime installation is supported on Windows x64 only")
        if artifact.platform != "windows-x64":
            raise RuntimeError(f"unsupported runtime platform: {artifact.platform}")
        root = self.paths.require_tool_descendant(self.paths.tools / "llama.cpp" / artifact.id)
        archive = self.paths.cache / "downloads" / artifact.archive_name
        install_dir = root / "bin"
        try:
            download_verified(
                url=artifact.url,
                destination=archive,
                expected_sha256=artifact.sha256,
                expected_bytes=artifact.bytes,
                cancel_event=cancel_event,
            )
            if cancel_event.is_set():
                raise RuntimeError("runtime installation cancelled")
            extract_zip_verified(archive, install_dir)
            executable = next(install_dir.rglob(artifact.executable_name), None)
            if executable is None or not executable.is_file():
                raise RuntimeError(f"verified runtime archive did not contain {artifact.executable_name}")
            executable_sha256 = sha256_file(executable)
            metadata = {
                "catalogue_id": artifact.id,
                "version": artifact.version,
                "build": artifact.build,
                "backend": artifact.backend,
                "archive_sha256": artifact.sha256,
                "archive_bytes": artifact.bytes,
                "executable_sha256": executable_sha256,
                "source_url": artifact.url,
                "license": artifact.license,
            }
            write_install_metadata(root / "install.json", metadata)
            install_id = artifact.id
            self.store.upsert_runtime_install(
                install_id=install_id,
                catalogue_id=artifact.id,
                version=artifact.version,
                backend=artifact.backend,
                install_relpath=str(self.paths.relative_to_root(root)),
                executable_relpath=str(self.paths.relative_to_root(executable)),
                artifact_sha256=artifact.sha256,
                status="installed",
            )
            return self.status(install_id, verify_hash=True)
        except Exception as exc:
            if root.exists():
                self.paths.delete_tool_path(root)
            self.store.upsert_runtime_install(
                install_id=artifact.id,
                catalogue_id=artifact.id,
                version=artifact.version,
                backend=artifact.backend,
                install_relpath=str(self.paths.relative_to_root(root)),
                executable_relpath=str(self.paths.relative_to_root(root / "bin" / artifact.executable_name)),
                artifact_sha256=artifact.sha256,
                status="failed",
                failure_message=str(exc)[-1000:],
            )
            raise

    def status(self, install_id: str, *, verify_hash: bool = False) -> dict[str, Any]:
        row = self.store.runtime_install(install_id)
        if row is None:
            raise KeyError(install_id)
        executable = self.paths.root / row["executable_relpath"]
        result = dict(row)
        result["present"] = executable.is_file()
        result["executable"] = str(executable) if executable.is_file() else None
        if verify_hash and executable.is_file():
            metadata_path = self.paths.root / row["install_relpath"] / "install.json"
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                expected = str(metadata["executable_sha256"])
                result["integrity"] = "verified" if sha256_file(executable) == expected else "failed"
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                result["integrity"] = "failed"
        else:
            result["integrity"] = "not_checked" if executable.is_file() else "missing"
        return result

    def require_verified_executable(self, install_id: str) -> Path:
        status = self.status(install_id, verify_hash=True)
        if status["status"] != "installed" or not status["present"] or status["integrity"] != "verified":
            raise RuntimeError("llama.cpp runtime failed local integrity verification")
        return Path(str(status["executable"]))

    def list_devices(self, install_id: str) -> dict[str, Any]:
        status = self.status(install_id, verify_hash=True)
        if not status["present"] or status["integrity"] != "verified":
            raise RuntimeError("runtime executable is missing")
        executable = str(status["executable"])
        try:
            result = subprocess.run(
                [executable, "--list-devices"],
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return {"ok": False, "devices": [], "raw": str(exc)}
        raw = (result.stdout + "\n" + result.stderr).strip()
        return {
            "ok": result.returncode == 0,
            "devices": parse_llama_devices(raw),
            "raw": raw[-6000:],
        }


class ModelInstallService:
    def __init__(self, paths: ManagedPaths, store: ModelStore) -> None:
        self.paths = paths
        self.store = store

    def install(self, artifact: ModelArtifact, cancel_event: Event) -> dict[str, Any]:
        install_id = artifact.install_id
        root = self.paths.require_model_descendant(
            self.paths.models / artifact.id / artifact.source_revision[:12]
        )
        model_path = root / artifact.filename
        try:
            written = download_verified(
                url=artifact.url,
                destination=model_path,
                expected_sha256=artifact.sha256,
                expected_bytes=artifact.bytes,
                cancel_event=cancel_event,
            )
            if cancel_event.is_set():
                raise RuntimeError("model installation cancelled")
            metadata = {
                "install_id": install_id,
                "catalogue_id": artifact.id,
                "display_name": artifact.display_name,
                "source_repo": artifact.source_repo,
                "source_revision": artifact.source_revision,
                "filename": artifact.filename,
                "sha256": artifact.sha256,
                "artifact_bytes": written,
                "quantization": artifact.quantization,
                "license": artifact.license,
                "tested_context_tokens": artifact.tested_context_tokens,
                "app_managed": True,
            }
            write_install_metadata(root / "install.json", metadata)
            self.store.upsert_model_install(
                install_id=install_id,
                catalogue_id=artifact.id,
                source_revision=artifact.source_revision,
                model_relpath=str(self.paths.relative_to_root(model_path)),
                artifact_sha256=artifact.sha256,
                artifact_bytes=written,
                status="installed",
                app_managed=True,
            )
            return self.status(install_id, verify_hash=True)
        except Exception as exc:
            if root.exists():
                self.paths.delete_model_path(root)
            self.store.upsert_model_install(
                install_id=install_id,
                catalogue_id=artifact.id,
                source_revision=artifact.source_revision,
                model_relpath=str(self.paths.relative_to_root(model_path)),
                artifact_sha256=artifact.sha256,
                artifact_bytes=0,
                status="failed",
                failure_message=str(exc)[-1000:],
                app_managed=True,
            )
            raise

    def status(self, install_id: str, *, verify_hash: bool = False) -> dict[str, Any]:
        row = self.store.model_install(install_id)
        if row is None:
            raise KeyError(install_id)
        path = self.paths.root / row["model_relpath"]
        result = dict(row)
        result["app_managed"] = bool(result.get("app_managed", 0))
        result["present"] = path.is_file()
        if verify_hash and path.is_file():
            result["integrity"] = "verified" if sha256_file(path) == row["artifact_sha256"] else "failed"
        else:
            result["integrity"] = "not_checked" if path.is_file() else "missing"
        result["model_path"] = str(path) if path.is_file() else None
        return result

    def require_verified_path(self, install_id: str) -> Path:
        status = self.status(install_id, verify_hash=True)
        if not status["present"] or status["integrity"] != "verified":
            raise RuntimeError("model file failed local integrity verification")
        return self.paths.require_model_descendant(Path(str(status["model_path"])))
