import os
from pathlib import Path

import pytest

from jobpilot.resume.tooling import (
    TECTONIC_ARCHIVE_SHA256,
    TECTONIC_ARCHIVE_SIZE,
    TECTONIC_VERSION,
    TectonicInstallService,
)
from jobpilot.runtime.paths import ManagedPaths


def test_tectonic_pin_is_explicit_and_status_is_offline(tmp_path: Path) -> None:
    paths = ManagedPaths(tmp_path / "JobPilotLocal")
    paths.create_all_roots()
    status = TectonicInstallService(paths).status()
    assert status["installed"] is False
    assert status["version"] == "0.17.0"
    assert TECTONIC_VERSION == "0.17.0"
    assert TECTONIC_ARCHIVE_SIZE == 21060223
    assert TECTONIC_ARCHIVE_SHA256 == "f61ce51f0b0ade1015b7de7ef368541c5424e9756ecbd0d7af97d6d48030845f"


def test_managed_tectonic_installer_refuses_non_windows_runtime(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("non-Windows guard is exercised on other CI hosts")
    with pytest.raises(RuntimeError):
        TectonicInstallService(ManagedPaths(tmp_path / "JobPilotLocal")).install()
