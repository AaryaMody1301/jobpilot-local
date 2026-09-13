from __future__ import annotations

from jobpilot.app.phase5_bridge import Phase5DesktopBridge
from jobpilot.app.phase6_controller import Phase6ApplicationController


class Phase6DesktopBridge(Phase5DesktopBridge):
    def __init__(self, controller: Phase6ApplicationController) -> None:
        super().__init__(controller)
        self._phase6 = controller

    def queue_controlled_application(self, job_identity: str, target_url: str) -> dict[str, object]:
        return self._phase6.queue_controlled_application(job_identity, target_url)

    def approve_application_question(self, question_id: str, answer: str) -> dict[str, object]:
        return self._phase6.approve_application_question(question_id, answer)
