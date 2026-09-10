from datetime import datetime, timezone

from jobpilot.domain.states import ApplicationState
from jobpilot.runtime.shutdown import CONFIRMATION_GRACE_SECONDS, ShutdownPolicy


def test_close_before_submit_has_no_wait() -> None:
    policy = ShutdownPolicy()
    plan = policy.plan(ApplicationState.FILLING, now=datetime(2026, 9, 10, tzinfo=timezone.utc))
    assert plan.cancel_discovery
    assert plan.cancel_generation
    assert not plan.schedule_new_work
    assert not plan.waits_for_confirmation


def test_close_after_submit_gets_exact_bounded_confirmation_window() -> None:
    policy = ShutdownPolicy()
    now = datetime(2026, 9, 10, tzinfo=timezone.utc)
    plan = policy.plan(ApplicationState.SUBMITTING, now=now)
    assert plan.waits_for_confirmation
    assert int((plan.confirmation_deadline - now).total_seconds()) == CONFIRMATION_GRACE_SECONDS


def test_unresolved_post_submit_becomes_uncertain() -> None:
    policy = ShutdownPolicy()
    assert policy.unresolved_submission_outcome(ApplicationState.SUBMITTING) is ApplicationState.UNCERTAIN
    assert policy.unresolved_submission_outcome(ApplicationState.CONFIRMING) is ApplicationState.UNCERTAIN
    assert policy.unresolved_submission_outcome(ApplicationState.FILLING) is ApplicationState.FILLING
