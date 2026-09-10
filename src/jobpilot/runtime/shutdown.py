from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from jobpilot.domain.states import ApplicationState


CONFIRMATION_GRACE_SECONDS = 60


@dataclass(frozen=True, slots=True)
class ShutdownPlan:
    cancel_discovery: bool
    cancel_generation: bool
    schedule_new_work: bool
    confirmation_deadline: datetime | None

    @property
    def waits_for_confirmation(self) -> bool:
        return self.confirmation_deadline is not None


class ShutdownPolicy:
    """Pure lifecycle policy shared by Stop and Close."""

    def plan(self, application_state: ApplicationState | None, *, now: datetime | None = None) -> ShutdownPlan:
        current_time = now or datetime.now(timezone.utc)
        wait = application_state in {ApplicationState.SUBMITTING, ApplicationState.CONFIRMING}
        return ShutdownPlan(
            cancel_discovery=True,
            cancel_generation=True,
            schedule_new_work=False,
            confirmation_deadline=(current_time + timedelta(seconds=CONFIRMATION_GRACE_SECONDS) if wait else None),
        )

    @staticmethod
    def unresolved_submission_outcome(application_state: ApplicationState | None) -> ApplicationState | None:
        if application_state in {ApplicationState.SUBMITTING, ApplicationState.CONFIRMING}:
            return ApplicationState.UNCERTAIN
        return application_state
