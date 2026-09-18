from __future__ import annotations

import threading

from jobpilot.model.phase4 import _runtime_cancellation_reason


class _Watcher:
    def __init__(self, critical: bool) -> None:
        self.critical = critical


def test_phase4_runtime_cancellation_reason_prefers_explicit_cancel() -> None:
    cancel = threading.Event()
    cancel.set()
    assert _runtime_cancellation_reason(cancel, _Watcher(True)) == "resume tailoring cancelled"


def test_phase4_runtime_cancellation_reason_reports_memory_pressure() -> None:
    cancel = threading.Event()
    assert _runtime_cancellation_reason(cancel, _Watcher(True)) == (
        "local inference was cancelled because memory pressure became critical"
    )


def test_phase4_runtime_cancellation_reason_preserves_other_runtime_errors() -> None:
    cancel = threading.Event()
    assert _runtime_cancellation_reason(cancel, _Watcher(False)) is None
