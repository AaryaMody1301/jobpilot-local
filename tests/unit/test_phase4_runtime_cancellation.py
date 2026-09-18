from __future__ import annotations

import threading

import pytest

from jobpilot.model.phase4 import Phase4ModelManager


def test_phase4_source_distinguishes_user_and_pressure_cancellation() -> None:
    source = __import__("inspect").getsource(Phase4ModelManager.infer_selected_structured)
    assert 'if cancel_event.is_set()' in source
    assert 'if watcher.critical' in source
    assert 'resume tailoring cancelled' in source
    assert 'memory pressure became critical' in source
