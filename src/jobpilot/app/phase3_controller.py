from __future__ import annotations

from typing import Any

from jobpilot.app.controller import ApplicationController
from jobpilot.model.manager import ModelManager
from jobpilot.domain.states import SessionState


class Phase3ApplicationController(ApplicationController):
    """Phase 2 controller plus local hardware/model lifecycle. No tailoring is enabled."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.models = ModelManager(self.paths, self.database)
        self.models.refresh_hardware()
        self.database.record_foundation_activity(
            self.session_id,
            "phase3_hardware",
            "Captured local hardware/resource budget; no model download or inference started",
        )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = super().snapshot()
            state["phase"] = 3
            state["model"] = self.models.snapshot()
            return state

    def refresh_model_hardware(self) -> dict[str, Any]:
        with self._lock:
            self._require_open()
            if self._state is not SessionState.IDLE:
                raise RuntimeError("hardware refresh is allowed only while the session is idle")
            self.models.refresh_hardware()
            self.database.record_foundation_activity(self.session_id, "phase3_hardware", "Refreshed local hardware/resource budget")
            return self.snapshot()

    def install_model_runtime(self, runtime_id: str) -> dict[str, Any]:
        with self._lock:
            cancel = self._begin_onboarding_operation("llama.cpp runtime installation")
        try:
            result = self.models.install_runtime(runtime_id, cancel)
            with self._lock:
                self._require_open()
                self.database.record_foundation_activity(
                    self.session_id,
                    "model_runtime_install",
                    f"Installed checksum-verified local runtime {runtime_id}",
                )
            return result
        finally:
            with self._lock:
                self._end_onboarding_operation()

    def install_local_model(self, model_id: str) -> dict[str, Any]:
        with self._lock:
            cancel = self._begin_onboarding_operation("local model installation")
        try:
            result = self.models.install_model(model_id, cancel)
            with self._lock:
                self._require_open()
                self.database.record_foundation_activity(
                    self.session_id,
                    "model_install",
                    f"Installed checksum-verified local model {model_id}; not yet validated",
                )
            return result
        finally:
            with self._lock:
                self._end_onboarding_operation()

    def evaluate_local_model(self, model_install_id: str, runtime_install_id: str) -> dict[str, Any]:
        with self._lock:
            cancel = self._begin_onboarding_operation("local model evaluation")
        try:
            result = self.models.evaluate(model_install_id, runtime_install_id, cancel)
            with self._lock:
                self._require_open()
                outcome = "passed" if result["overall_pass"] else "failed"
                self.database.record_foundation_activity(
                    self.session_id,
                    "model_evaluation",
                    f"Controlled local model evaluation {outcome}: {model_install_id} on {runtime_install_id}",
                )
            return result
        finally:
            with self._lock:
                self._end_onboarding_operation()

    def select_model_for_phase4_review(self, model_install_id: str, runtime_install_id: str) -> dict[str, Any]:
        with self._lock:
            self._require_idle_onboarding()
            result = self.models.select_for_phase4_review(model_install_id, runtime_install_id)
            self.database.record_foundation_activity(
                self.session_id,
                "model_selected_for_review",
                f"Selected validated model {model_install_id} for future Phase 4 five-resume review; auto-tailoring remains disabled",
            )
            return result

    def check_model_updates(self) -> dict[str, Any]:
        with self._lock:
            cancel = self._begin_onboarding_operation("weekly model catalogue update check")
        try:
            if cancel.is_set():
                raise RuntimeError("update check cancelled")
            result = self.models.check_for_updates()
            with self._lock:
                self._require_open()
                self.database.record_foundation_activity(self.session_id, "model_update_check", "Checked configured local runtime/model sources; no download started")
            return result
        finally:
            with self._lock:
                self._end_onboarding_operation()

    def close(self) -> None:
        with self._lock:
            cancel = self._onboarding_cancel
            if cancel is not None:
                cancel.set()
        self.models.cancel_current()
        super().close()
