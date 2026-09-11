from __future__ import annotations

from typing import Any

from jobpilot.app.bridge import DesktopBridge
from jobpilot.app.phase3_controller import Phase3ApplicationController


class Phase3DesktopBridge(DesktopBridge):
    def __init__(self, controller: Phase3ApplicationController) -> None:
        super().__init__(controller)
        self._phase3 = controller

    def refresh_model_hardware(self) -> dict[str, Any]:
        return self._phase3.refresh_model_hardware()

    def install_model_runtime(self, runtime_id: str) -> dict[str, Any]:
        self._phase3.install_model_runtime(runtime_id)
        return self._phase3.snapshot()

    def install_local_model(self, model_id: str) -> dict[str, Any]:
        self._phase3.install_local_model(model_id)
        return self._phase3.snapshot()

    def evaluate_local_model(
        self,
        model_install_id: str,
        runtime_install_id: str,
        device_id: str | None = None,
    ) -> dict[str, Any]:
        self._phase3.evaluate_local_model(model_install_id, runtime_install_id, device_id)
        return self._phase3.snapshot()

    def select_model_for_phase4_review(self, model_install_id: str) -> dict[str, Any]:
        return self._phase3.select_model_for_phase4_review(model_install_id)

    def check_model_updates(self) -> dict[str, Any]:
        self._phase3.check_model_updates()
        return self._phase3.snapshot()
