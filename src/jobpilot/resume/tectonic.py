from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TectonicCompiler:
    """Builds safe Tectonic invocations; execution is owned by ProcessSupervisor."""

    executable: Path
    cache_dir: Path

    def build_command(self, source: Path, outdir: Path, *, allow_package_downloads: bool = False) -> list[str]:
        command = [str(self.executable), "-X", "compile", "--untrusted", "--keep-logs", "--outdir", str(outdir)]
        if not allow_package_downloads:
            command.append("--only-cached")
        command.append(str(source))
        return command

    def environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env["TECTONIC_CACHE_DIR"] = str(self.cache_dir.resolve())
        env["TECTONIC_UNTRUSTED_MODE"] = "1"
        return env
