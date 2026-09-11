from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from threading import Event
from typing import Callable


class DownloadCancelled(RuntimeError):
    pass


class ArtifactIntegrityError(RuntimeError):
    pass


ProgressCallback = Callable[[int, int | None], None]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_verified(
    *,
    url: str,
    destination: Path,
    expected_sha256: str,
    expected_bytes: int | None,
    cancel_event: Event,
    progress: ProgressCallback | None = None,
) -> int:
    if destination.exists():
        current_size = destination.stat().st_size
        if (expected_bytes is None or current_size == expected_bytes) and sha256_file(destination) == expected_sha256:
            if progress:
                progress(current_size, expected_bytes or current_size)
            return current_size

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.unlink(missing_ok=True)
    digest = hashlib.sha256()
    written = 0
    request = urllib.request.Request(url, headers={"User-Agent": "jobpilot-local/phase3"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response, partial.open("wb") as output:
            content_length = response.headers.get("Content-Length")
            total = int(content_length) if content_length and content_length.isdigit() else expected_bytes
            while True:
                if cancel_event.is_set():
                    raise DownloadCancelled("download cancelled")
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                written += len(chunk)
                if progress:
                    progress(written, total)
        if expected_bytes is not None and written != expected_bytes:
            raise ArtifactIntegrityError(f"artifact size mismatch: expected {expected_bytes}, got {written}")
        actual = digest.hexdigest()
        if actual != expected_sha256:
            raise ArtifactIntegrityError(f"artifact SHA-256 mismatch: expected {expected_sha256}, got {actual}")
        os.replace(partial, destination)
        return written
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def _zip_member_is_symlink(member: zipfile.ZipInfo) -> bool:
    unix_mode = (member.external_attr >> 16) & 0xFFFF
    return bool(unix_mode and stat.S_ISLNK(unix_mode))


def extract_zip_verified(archive: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="extract-", dir=str(destination.parent)))
    try:
        root = temp_dir.resolve()
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                if _zip_member_is_symlink(member):
                    raise ArtifactIntegrityError(f"symbolic-link archive entry is not allowed: {member.filename}")
                target = (temp_dir / member.filename).resolve()
                try:
                    target.relative_to(root)
                except ValueError as exc:
                    raise ArtifactIntegrityError(f"unsafe archive path: {member.filename}") from exc
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
        if destination.exists():
            shutil.rmtree(destination)
        os.replace(temp_dir, destination)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


def write_install_metadata(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)
