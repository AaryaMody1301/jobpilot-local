from __future__ import annotations

import json
import os
import platform
import shutil
import sys

from jobpilot.runtime.paths import ManagedPaths


def main() -> int:
    managed = ManagedPaths.default()
    result = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "is_windows": os.name == "nt",
        "managed_root": str(managed.root),
        "external_binaries": {
            "tectonic": shutil.which("tectonic"),
            "llama-server": shutil.which("llama-server") or shutil.which("llama-server.exe"),
        },
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
