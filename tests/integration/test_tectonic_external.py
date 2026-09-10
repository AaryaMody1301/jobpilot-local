from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from jobpilot.resume.tectonic import TectonicCompiler


pytestmark = pytest.mark.external
ROOT = Path(__file__).resolve().parents[2]


def test_controlled_cached_tectonic_compile(tmp_path: Path) -> None:
    configured = os.environ.get("JOBPILOT_TECTONIC_EXE")
    executable = Path(configured) if configured else None
    if executable is None or not executable.is_file():
        found = shutil.which("tectonic")
        executable = Path(found) if found else None
    if executable is None:
        pytest.skip("set JOBPILOT_TECTONIC_EXE to an approved Tectonic executable")

    source = tmp_path / "minimal.tex"
    source.write_text((ROOT / "tests" / "fixtures" / "minimal.tex.txt").read_text(), encoding="utf-8")
    cache = Path(os.environ.get("JOBPILOT_TECTONIC_CACHE", tmp_path / "tectonic-cache"))
    compiler = TectonicCompiler(executable, cache)
    outdir = tmp_path / "out"
    outdir.mkdir()
    completed = subprocess.run(
        compiler.build_command(source, outdir, allow_package_downloads=False),
        cwd=source.parent,
        env=compiler.environment(),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    output = completed.stdout + completed.stderr
    if completed.returncode != 0 and "only cached" in output.lower():
        pytest.skip("approved Tectonic cache has not been populated")
    assert completed.returncode == 0, output
    assert (outdir / "minimal.pdf").is_file()
