from __future__ import annotations

import hashlib
import json
import os
import shutil
import urllib.request
import threading
import zipfile
from pathlib import Path
from typing import Any

from jobpilot.runtime.paths import ManagedPaths

TECTONIC_VERSION = "0.17.0"
TECTONIC_ASSET_NAME = "tectonic-0.17.0-x86_64-pc-windows-msvc.zip"
TECTONIC_DOWNLOAD_URL = (
    "https://github.com/tectonic-typesetting/tectonic/releases/download/"
    "tectonic%400.17.0/tectonic-0.17.0-x86_64-pc-windows-msvc.zip"
)
TECTONIC_ARCHIVE_SHA256 = "f61ce51f0b0ade1015b7de7ef368541c5424e9756ecbd0d7af97d6d48030845f"
TECTONIC_ARCHIVE_SIZE = 21060223
MAX_TECTONIC_DOWNLOAD_BYTES = 24 * 1024 * 1024


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_tectonic_executable(paths: ManagedPaths) -> Path | None:
    candidate = paths.tectonic_executable
    return candidate if candidate.is_file() else None


class TectonicInstallService:
    """Explicit, checksum-pinned installer for the Windows x64 Tectonic binary."""

    def __init__(self, paths: ManagedPaths) -> None:
        self.paths = paths
        self._verified_signature: tuple[int, int, int] | None = None
        self._cached_status: dict[str, Any] | None = None

    def status(self) -> dict[str, Any]:
        executable = self.paths.tectonic_executable
        metadata_path = self.paths.tectonic_metadata
        if not executable.is_file() or not metadata_path.is_file():
            return {
                "installed": False,
                "managed": True,
                "version": TECTONIC_VERSION,
                "download_bytes": TECTONIC_ARCHIVE_SIZE,
                "integrity": "not installed",
            }
        try:
            executable_stat = executable.stat()
            metadata_stat = metadata_path.stat()
            signature = (executable_stat.st_size, executable_stat.st_mtime_ns, metadata_stat.st_mtime_ns)
            if self._verified_signature == signature and self._cached_status is not None:
                return dict(self._cached_status)
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self._verified_signature = None
            self._cached_status = None
            return {"installed": False, "managed": True, "version": TECTONIC_VERSION, "integrity": "metadata invalid"}
        digest = _sha256_file(executable)
        valid = (
            metadata.get("version") == TECTONIC_VERSION
            and metadata.get("archive_sha256") == TECTONIC_ARCHIVE_SHA256
            and metadata.get("executable_sha256") == digest
        )
        result = {
            "installed": bool(valid),
            "managed": True,
            "version": TECTONIC_VERSION,
            "path": str(executable) if valid else None,
            "integrity": "verified" if valid else "mismatch",
            "download_bytes": TECTONIC_ARCHIVE_SIZE,
        }
        self._verified_signature = signature if valid else None
        self._cached_status = dict(result) if valid else None
        return result

    def install(self, cancel_event: threading.Event | None = None) -> dict[str, Any]:
        if os.name != "nt":
            raise RuntimeError("the managed Tectonic package is pinned for Windows x64 only")
        current = self.status()
        if current.get("installed") and current.get("managed"):
            return current

        self._verified_signature = None
        self._cached_status = None
        self.paths.tectonic_tool_dir.mkdir(parents=True, exist_ok=True)
        download_dir = self.paths.runtime / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)
        archive = download_dir / f"{TECTONIC_ASSET_NAME}.partial"
        executable_tmp = self.paths.tectonic_tool_dir / "tectonic.exe.partial"
        for candidate in (archive, executable_tmp):
            candidate.unlink(missing_ok=True)

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        request = urllib.request.Request(TECTONIC_DOWNLOAD_URL, headers={"User-Agent": "jobpilot-local/phase2"})
        digest = hashlib.sha256()
        downloaded = 0
        try:
            with opener.open(request, timeout=10) as response, archive.open("xb") as output:
                declared = response.headers.get("Content-Length")
                if declared and int(declared) > MAX_TECTONIC_DOWNLOAD_BYTES:
                    raise RuntimeError("Tectonic download exceeded the pinned maximum size")
                while True:
                    if cancel_event is not None and cancel_event.is_set():
                        raise RuntimeError("Tectonic installation was cancelled")
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > MAX_TECTONIC_DOWNLOAD_BYTES:
                        raise RuntimeError("Tectonic download exceeded the pinned maximum size")
                    digest.update(chunk)
                    output.write(chunk)
            if downloaded != TECTONIC_ARCHIVE_SIZE:
                raise RuntimeError(f"Tectonic archive size mismatch: expected {TECTONIC_ARCHIVE_SIZE}, got {downloaded}")
            if digest.hexdigest() != TECTONIC_ARCHIVE_SHA256:
                raise RuntimeError("Tectonic archive SHA-256 mismatch")

            with zipfile.ZipFile(archive) as bundle:
                matches = [member for member in bundle.infolist() if Path(member.filename).name.lower() == "tectonic.exe" and not member.is_dir()]
                if len(matches) != 1:
                    raise RuntimeError("Tectonic archive did not contain exactly one tectonic.exe")
                with bundle.open(matches[0]) as source, executable_tmp.open("xb") as destination:
                    shutil.copyfileobj(source, destination)
            executable_digest = _sha256_file(executable_tmp)
            os.replace(executable_tmp, self.paths.tectonic_executable)
            metadata = {
                "version": TECTONIC_VERSION,
                "asset": TECTONIC_ASSET_NAME,
                "source": TECTONIC_DOWNLOAD_URL,
                "archive_sha256": TECTONIC_ARCHIVE_SHA256,
                "executable_sha256": executable_digest,
            }
            metadata_tmp = self.paths.tectonic_tool_dir / "install.json.partial"
            metadata_tmp.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
            os.replace(metadata_tmp, self.paths.tectonic_metadata)
        finally:
            archive.unlink(missing_ok=True)
            executable_tmp.unlink(missing_ok=True)
        result = self.status()
        if not result.get("installed"):
            raise RuntimeError("Tectonic installation did not pass post-install verification")
        return result
