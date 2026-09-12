from __future__ import annotations

from typing import Any, Mapping

from jobpilot.app.phase4_bridge import Phase4DesktopBridge
from jobpilot.app.phase5_controller import Phase5ApplicationController


class Phase5DesktopBridge(Phase4DesktopBridge):
    def __init__(self, controller: Phase5ApplicationController) -> None:
        super().__init__(controller)
        self._phase5 = controller

    def import_manual_job(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        return self._phase5.import_manual_job(raw)

    def add_verified_job_board(self, provider: str, employer: str, token: str) -> dict[str, Any]:
        return self._phase5.add_verified_job_board(provider, employer, token)

    def set_job_board_enabled(self, board_id: str, enabled: bool) -> dict[str, Any]:
        return self._phase5.set_job_board_enabled(board_id, bool(enabled))

    def discover_jobs(self) -> dict[str, Any]:
        return self._phase5.discover_jobs()
