from __future__ import annotations

from typing import Any

from jobpilot.app.phase6_bridge import Phase6DesktopBridge
from jobpilot.app.phase8_controller import Phase8ApplicationController


class Phase8DesktopBridge(Phase6DesktopBridge):
    def __init__(self, controller: Phase8ApplicationController) -> None:
        super().__init__(controller)
        self._phase8 = controller

    def resolve_application_eligibility(self, application_id: str, eligible: bool, note: str) -> dict[str, Any]:
        return self._phase8.resolve_application_eligibility(application_id, bool(eligible), note)

    def retry_application_tailoring(self, application_id: str) -> dict[str, Any]:
        return self._phase8.retry_application_tailoring(application_id)

    def queue_prepared_controlled_application(self, application_id: str, target_url: str) -> dict[str, Any]:
        return self._phase8.queue_prepared_controlled_application(application_id, target_url)

    def inspect_prepared_application(self, application_id: str) -> dict[str, Any]:
        return self._phase8.inspect_prepared_application(application_id)
