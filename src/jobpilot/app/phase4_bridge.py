from __future__ import annotations

from typing import Any

from jobpilot.app.phase3_bridge import Phase3DesktopBridge
from jobpilot.app.phase4_controller import Phase4ApplicationController


class Phase4DesktopBridge(Phase3DesktopBridge):
    def __init__(self, controller: Phase4ApplicationController) -> None:
        super().__init__(controller)
        self._phase4 = controller

    def import_manual_job_description(self, text: str, source_url: str | None = None) -> dict[str, Any]:
        return self._phase4.import_manual_job_description(text, source_url)

    def generate_tailored_resume(self, jd_id: str) -> dict[str, Any]:
        self._phase4.generate_tailored_resume(jd_id)
        return self._phase4.snapshot()

    def approve_tailored_resume(self, run_id: str, note: str | None = None) -> dict[str, Any]:
        return self._phase4.approve_tailored_resume(run_id, note)

    def reject_tailored_resume(self, run_id: str, note: str | None = None) -> dict[str, Any]:
        return self._phase4.reject_tailored_resume(run_id, note)

    def enable_automatic_tailoring(self, delete_previous_app_managed_weights: bool = False) -> dict[str, Any]:
        return self._phase4.enable_automatic_tailoring(
            delete_previous_app_managed_weights=bool(delete_previous_app_managed_weights)
        )

    def tailored_pdf_data_uri(self, run_id: str) -> str:
        return self._phase4.tailored_pdf_data_uri(run_id)
