import pytest

from jobpilot.domain.states import APPLICATION_MACHINE, SESSION_MACHINE, ApplicationState, InvalidTransition, SessionState


def test_launch_session_can_only_start_or_close() -> None:
    assert SESSION_MACHINE.can_transition(SessionState.IDLE, SessionState.RUNNING)
    assert SESSION_MACHINE.can_transition(SessionState.IDLE, SessionState.CLOSING)
    assert not SESSION_MACHINE.can_transition(SessionState.IDLE, SessionState.PAUSED)


def test_uncertain_is_terminal_and_never_retryable() -> None:
    for target in ApplicationState:
        assert not APPLICATION_MACHINE.can_transition(ApplicationState.UNCERTAIN, target)


def test_submit_boundary_cannot_transition_to_retryable_failure() -> None:
    assert APPLICATION_MACHINE.can_transition(ApplicationState.SUBMITTING, ApplicationState.CONFIRMING)
    assert APPLICATION_MACHINE.can_transition(ApplicationState.SUBMITTING, ApplicationState.UNCERTAIN)
    assert not APPLICATION_MACHINE.can_transition(ApplicationState.SUBMITTING, ApplicationState.FAILED)
    assert not APPLICATION_MACHINE.can_transition(ApplicationState.SUBMITTING, ApplicationState.QUEUED)


def test_invalid_transition_raises() -> None:
    with pytest.raises(InvalidTransition):
        APPLICATION_MACHINE.require_transition(ApplicationState.CONFIRMING, ApplicationState.QUEUED)
