from pathlib import Path

import pytest

from scripts.verify_dependency_lock import verify_lock


ROOT = Path(__file__).resolve().parents[2]


def test_committed_dependency_lock_matches_project_inputs_and_hashes() -> None:
    packages, artifacts = verify_lock()
    assert packages >= 8
    assert artifacts >= packages


def test_dependency_lock_verifier_rejects_drifted_direct_inputs(tmp_path: Path) -> None:
    project = tmp_path / "pyproject.toml"
    project.write_text(
        """
[build-system]
requires = ["setuptools==84.0.0"]
build-backend = "setuptools.build_meta"

[project]
name = "fixture"
version = "1.0.0"
dependencies = ["example==1.0.0"]

[project.optional-dependencies]
dev = []
""".strip(),
        encoding="utf-8",
    )
    requirements = tmp_path / "requirements-lock.in"
    requirements.write_text("example==2.0.0\nsetuptools==84.0.0\n", encoding="utf-8")
    build = tmp_path / "requirements-build.in"
    build.write_text("setuptools==84.0.0\n", encoding="utf-8")
    lock = tmp_path / "pylock.toml"
    lock.write_text(
        """
lock-version = "1.0"
created-by = "pip"

[[packages]]
name = "example"
version = "2.0.0"
[[packages.wheels]]
name = "example-2.0.0-py3-none-any.whl"
url = "https://files.pythonhosted.org/example.whl"
[packages.wheels.hashes]
sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

[[packages]]
name = "setuptools"
version = "84.0.0"
[[packages.wheels]]
name = "setuptools-84.0.0-py3-none-any.whl"
url = "https://files.pythonhosted.org/setuptools.whl"
[packages.wheels.hashes]
sha256 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not match pyproject"):
        verify_lock(lock, requirements, build, project)


def test_ci_installer_never_resolves_a_new_lock() -> None:
    installer = (ROOT / "scripts" / "install_ci_dependencies.ps1").read_text(encoding="utf-8")
    assert "pip lock" not in installer
    assert "scripts/verify_dependency_lock.py" in installer
    assert "-r pylock.toml" in installer
