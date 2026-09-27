"""Exclusive ownership of a local profile across desktop processes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO


class ProfileLock:
    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._file: BinaryIO = (root / ".jobpilot-profile.lock").open("a+b")
        try:
            if os.name == "nt":
                import msvcrt

                if self._file.seek(0, os.SEEK_END) == 0:
                    self._file.write(b"\0")
                    self._file.flush()
                self._file.seek(0)
                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            self._file.close()
            raise RuntimeError("this JobPilot profile is already open in another process; close it before opening a second instance or running a gate report") from exc

    def close(self) -> None:
        if self._file.closed:
            return
        self._file.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        self._file.close()
