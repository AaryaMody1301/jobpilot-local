from __future__ import annotations

import threading

from jobpilot.model.phase4 import (
    MAX_INFERENCE_TIMEOUT_SECONDS,
    MIN_INFERENCE_TIMEOUT_SECONDS,
    _inference_timeout_seconds,
    _runtime_cancellation_reason,
)


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


def test_phase4_inference_timeout_scales_for_slow_cpu_prompt_and_generation() -> None:
    timeout = _inference_timeout_seconds(
        3724,
        1000,
        {
            "prompt_tokens_per_second": 25.95,
            "generation_tokens_per_second": 8.6,
        },
    )
    assert 540 <= timeout <= 560
    assert timeout > 120


def test_phase4_inference_timeout_has_safe_floor_and_cap() -> None:
    assert _inference_timeout_seconds(
        10,
        10,
        {"prompt_tokens_per_second": 1000, "generation_tokens_per_second": 1000},
    ) == MIN_INFERENCE_TIMEOUT_SECONDS
    assert _inference_timeout_seconds(
        4095,
        1000,
        {"prompt_tokens_per_second": None, "generation_tokens_per_second": 0},
    ) == MAX_INFERENCE_TIMEOUT_SECONDS
