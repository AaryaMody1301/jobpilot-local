from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN_RE = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;#]+)$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def read_exact_pins(path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = PIN_RE.fullmatch(line)
        if match is None:
            raise ValueError(f"{path.name}:{number} must be an exact name==version pin")
        name = normalize_name(match.group(1))
        if name in pins:
            raise ValueError(f"{path.name}:{number} duplicates {name}")
        pins[name] = match.group(2)
    return pins


def project_pins(path: Path) -> dict[str, str]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    values = [
        *data["project"].get("dependencies", []),
        *data["project"].get("optional-dependencies", {}).get("dev", []),
        *data["build-system"].get("requires", []),
    ]
    pins: dict[str, str] = {}
    for value in values:
        match = PIN_RE.fullmatch(str(value))
        if match is None:
            raise ValueError(f"pyproject dependency must be exactly pinned: {value}")
        pins[normalize_name(match.group(1))] = match.group(2)
    return pins


def verify_lock(
    lock_path: Path = ROOT / "pylock.toml",
    requirements_path: Path = ROOT / "requirements-lock.in",
    build_path: Path = ROOT / "requirements-build.in",
    project_path: Path = ROOT / "pyproject.toml",
) -> tuple[int, int]:
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("lock-version") != "1.0":
        raise ValueError("pylock.toml must use lock-version 1.0")

    direct = read_exact_pins(requirements_path)
    project = project_pins(project_path)
    if direct != project:
        missing = sorted(set(project) - set(direct))
        extra = sorted(set(direct) - set(project))
        changed = sorted(name for name in set(project) & set(direct) if project[name] != direct[name])
        raise ValueError(
            f"requirements-lock.in does not match pyproject.toml; missing={missing}, extra={extra}, changed={changed}"
        )

    build = read_exact_pins(build_path)
    if not build:
        raise ValueError("requirements-build.in must contain exact build dependency pins")

    packages: dict[str, str] = {}
    artifact_count = 0
    for package in lock.get("packages", []):
        name = normalize_name(str(package.get("name") or ""))
        version = str(package.get("version") or "")
        if not name or not version:
            raise ValueError("every locked package must have a name and version")
        if name in packages:
            raise ValueError(f"duplicate locked package: {name}")
        packages[name] = version

        artifacts = list(package.get("wheels") or [])
        sdist = package.get("sdist")
        if sdist:
            artifacts.append(sdist)
        if not artifacts:
            raise ValueError(f"locked package has no wheel or sdist: {name}")
        for artifact in artifacts:
            url = str(artifact.get("url") or "")
            digest = str((artifact.get("hashes") or {}).get("sha256") or "").lower()
            if not url.startswith("https://"):
                raise ValueError(f"locked artifact must use https: {name}")
            if SHA256_RE.fullmatch(digest) is None:
                raise ValueError(f"locked artifact is missing a valid sha256: {name}")
            artifact_count += 1

    mismatched = sorted(name for name, version in direct.items() if packages.get(name) != version)
    if mismatched:
        raise ValueError(f"pylock.toml does not contain the exact direct pin(s): {mismatched}")

    return len(packages), artifact_count


def main() -> int:
    try:
        packages, artifacts = verify_lock()
    except (KeyError, OSError, TypeError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"dependency lock verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"dependency lock verified: {packages} packages, {artifacts} hashed artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
