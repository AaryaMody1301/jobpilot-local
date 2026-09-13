from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import AbstractSet, Mapping


class InvalidTransition(ValueError):
    pass


class SessionState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    CLOSING = "closing"
    EXITED = "exited"


SESSION_TRANSITIONS: Mapping[SessionState, AbstractSet[SessionState]] = {
    SessionState.IDLE: {SessionState.RUNNING, SessionState.CLOSING},
    SessionState.RUNNING: {SessionState.PAUSED, SessionState.STOPPING, SessionState.CLOSING},
    SessionState.PAUSED: {SessionState.RUNNING, SessionState.STOPPING, SessionState.CLOSING},
    SessionState.STOPPING: {SessionState.IDLE, SessionState.CLOSING},
    SessionState.CLOSING: {SessionState.EXITED},
    SessionState.EXITED: set(),
}


class ApplicationState(StrEnum):
    DISCOVERED = "discovered"
    ELIGIBILITY_CHECK = "eligibility_check"
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    NEEDS_REVIEW = "needs_review"
    TAILORING = "tailoring"
    REVIEW_REQUIRED = "review_required"
    PREPARED = "prepared"
    QUEUED = "queued"
    INSPECTING = "inspecting"
    FILLING = "filling"
    READY_TO_SUBMIT = "ready_to_submit"
    SUBMITTING = "submitting"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    BLOCKED = "blocked"
    FAILED = "failed"
    STALE = "stale"
    DUPLICATE = "duplicate"
    UNCERTAIN = "uncertain"


APPLICATION_TRANSITIONS: Mapping[ApplicationState, AbstractSet[ApplicationState]] = {
    ApplicationState.DISCOVERED: {ApplicationState.ELIGIBILITY_CHECK, ApplicationState.DUPLICATE},
    ApplicationState.ELIGIBILITY_CHECK: {ApplicationState.ELIGIBLE, ApplicationState.INELIGIBLE, ApplicationState.NEEDS_REVIEW, ApplicationState.BLOCKED},
    ApplicationState.ELIGIBLE: {ApplicationState.TAILORING, ApplicationState.STALE},
    ApplicationState.INELIGIBLE: set(),
    ApplicationState.NEEDS_REVIEW: {ApplicationState.ELIGIBILITY_CHECK, ApplicationState.QUEUED, ApplicationState.BLOCKED},
    ApplicationState.TAILORING: {ApplicationState.REVIEW_REQUIRED, ApplicationState.PREPARED, ApplicationState.NEEDS_REVIEW, ApplicationState.FAILED, ApplicationState.STALE},
    ApplicationState.REVIEW_REQUIRED: {ApplicationState.PREPARED, ApplicationState.TAILORING, ApplicationState.BLOCKED, ApplicationState.STALE},
    ApplicationState.PREPARED: {ApplicationState.QUEUED, ApplicationState.STALE},
    ApplicationState.QUEUED: {ApplicationState.INSPECTING, ApplicationState.STALE, ApplicationState.BLOCKED},
    ApplicationState.INSPECTING: {ApplicationState.FILLING, ApplicationState.NEEDS_REVIEW, ApplicationState.QUEUED, ApplicationState.BLOCKED, ApplicationState.FAILED, ApplicationState.STALE},
    ApplicationState.FILLING: {ApplicationState.READY_TO_SUBMIT, ApplicationState.NEEDS_REVIEW, ApplicationState.BLOCKED, ApplicationState.FAILED, ApplicationState.STALE, ApplicationState.QUEUED},
    ApplicationState.READY_TO_SUBMIT: {ApplicationState.SUBMITTING, ApplicationState.BLOCKED, ApplicationState.FAILED, ApplicationState.STALE, ApplicationState.QUEUED},
    ApplicationState.SUBMITTING: {ApplicationState.CONFIRMING, ApplicationState.UNCERTAIN},
    ApplicationState.CONFIRMING: {ApplicationState.CONFIRMED, ApplicationState.UNCERTAIN},
    ApplicationState.CONFIRMED: set(),
    ApplicationState.BLOCKED: set(),
    ApplicationState.FAILED: set(),
    ApplicationState.STALE: set(),
    ApplicationState.DUPLICATE: set(),
    ApplicationState.UNCERTAIN: set(),
}


@dataclass(frozen=True, slots=True)
class StateMachine:
    transitions: Mapping[StrEnum, AbstractSet[StrEnum]]

    def can_transition(self, current: StrEnum, target: StrEnum) -> bool:
        return target in self.transitions.get(current, set())

    def require_transition(self, current: StrEnum, target: StrEnum) -> None:
        if not self.can_transition(current, target):
            raise InvalidTransition(f"invalid transition: {current.value} -> {target.value}")


SESSION_MACHINE = StateMachine(SESSION_TRANSITIONS)
APPLICATION_MACHINE = StateMachine(APPLICATION_TRANSITIONS)


def is_irreversible_submission_state(state: ApplicationState) -> bool:
    return state in {ApplicationState.SUBMITTING, ApplicationState.CONFIRMING, ApplicationState.CONFIRMED, ApplicationState.UNCERTAIN}
