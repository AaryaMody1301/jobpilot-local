from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from jobpilot.version import __version__  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the verified JobPilot Windows distribution archive")
    parser.add_argument("--app-dir", type=Path, default=ROOT / "dist" / "jobpilot-local")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args(argv)

    app_dir = args.app_dir.resolve(strict=True)
    if not (app_dir / "jobpilot-local.exe").is_file():
        raise SystemExit(f"packaged executable is missing from {app_dir}")
    output_dir = args.output_dir.resolve(strict=False)
    output_dir.mkdir(parents=True, exist_ok=True)
    release_name = f"JobPilotLocal-{__version__}-win-x64"
    release_root = output_dir / release_name
    if release_root.exists():
        shutil.rmtree(release_root)
    release_root.mkdir()
    shutil.copytree(app_dir, release_root / "app")

    for source, target in (
        (ROOT / "packaging" / "install.ps1", release_root / "install.ps1"),
        (ROOT / "packaging" / "setup.cmd", release_root / "setup.cmd"),
        (ROOT / "packaging" / "BROWSER_NOTICES.md", release_root / "BROWSER_NOTICES.md"),
        (ROOT / "LICENSE", release_root / "LICENSE"),
        (ROOT / "THIRD_PARTY_NOTICES.md", release_root / "THIRD_PARTY_NOTICES.md"),
    ):
        shutil.copy2(source, target)

    (release_root / "README.txt").write_text(
        "JobPilot Local for Windows 10/11 x64\n"
        "\n"
        "1. Close any running JobPilot Local instance.\n"
        "2. Run setup.cmd. Installation is per-user and does not require administrator access.\n"
        "3. Future versions use the same setup command to upgrade program files while preserving %LOCALAPPDATA%\\JobPilotLocal.\n"
        "\n"
        "The real-employer application pilot is intentionally disabled in this distribution stage.\n",
        encoding="utf-8",
    )

    files: list[dict[str, object]] = []
    for path in sorted(release_root.rglob("*")):
        if path.is_symlink():
            raise SystemExit(f"distribution must not contain symbolic links: {path}")
        if path.is_file():
            files.append({
                "path": path.relative_to(release_root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    digest = hashlib.sha256()
    for item in files:
        digest.update(f"{item['path']}\0{item['bytes']}\0{item['sha256']}\n".encode("utf-8"))
    manifest = {
        "format": "jobpilot-windows-distribution",
        "format_version": 1,
        "app_version": __version__,
        "platform": "windows",
        "architecture": "x64",
        "install_scope": "per-user",
        "user_data_root": "%LOCALAPPDATA%\\JobPilotLocal",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "archive_payload_sha256": digest.hexdigest(),
        "files": files,
    }
    (release_root / "distribution-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    archive = output_dir / f"{release_name}.zip"
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in sorted(release_root.rglob("*")):
            if path.is_file():
                bundle.write(path, f"{release_name}/{path.relative_to(release_root).as_posix()}")
    archive_hash = sha256(archive)
    (output_dir / f"{release_name}.sha256").write_text(f"{archive_hash}  {archive.name}\n", encoding="ascii")
    print(json.dumps({"archive": str(archive), "sha256": archive_hash, "bytes": archive.stat().st_size}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
