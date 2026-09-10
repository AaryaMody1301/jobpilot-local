from pathlib import Path

from jobpilot.resume.tectonic import TectonicCompiler


def test_normal_compile_is_cached_and_untrusted(tmp_path: Path) -> None:
    compiler = TectonicCompiler(tmp_path / "tectonic", tmp_path / "cache")
    command = compiler.build_command(tmp_path / "resume.tex", tmp_path / "out")
    assert "--only-cached" in command
    assert "--untrusted" in command
    assert compiler.environment()["TECTONIC_UNTRUSTED_MODE"] == "1"
    assert compiler.environment()["TECTONIC_CACHE_DIR"] == str((tmp_path / "cache").resolve())


def test_package_fetch_requires_explicit_flag(tmp_path: Path) -> None:
    compiler = TectonicCompiler(tmp_path / "tectonic", tmp_path / "cache")
    command = compiler.build_command(tmp_path / "resume.tex", tmp_path / "out", allow_package_downloads=True)
    assert "--only-cached" not in command
    assert "--untrusted" in command
