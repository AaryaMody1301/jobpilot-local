from __future__ import annotations

from pathlib import Path

import pytest

from jobpilot.applications import (
    ApplicationJournal,
    ControlledFixtureViolation,
    question_context_sha256,
)
from jobpilot.domain.states import ApplicationState, InvalidTransition
from jobpilot.storage.database import Database

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def test_phase6_journal_is_transactional_context_bound_and_crash_safe(tmp_path: Path) -> None:
    database_path = tmp_path / "jobpilot.sqlite3"
    with Database(database_path, MIGRATIONS) as db:
        db.apply_migrations()
        journal = ApplicationJournal(db)
        with pytest.raises(ControlledFixtureViolation):
            journal.queue_controlled("real-employer", "https://example.com/apply")

        first = journal.queue_controlled("fixture-1", "http://127.0.0.1:8000/form")
        duplicate = journal.queue_controlled("fixture-1", "http://localhost:8000/form")
        assert duplicate["id"] == first["id"]
        assert len(journal.attempts()) == 1

        claimed = journal.claim_next("session-1")
        assert claimed and claimed["id"] == first["id"]
        journal.transition(first["id"], ApplicationState.FILLING, "controlled form inspected")
        context = question_context_sha256("notice", "Notice period", "input:text", "candidate-v1")
        journal.require_review(first["id"], [{
            "question_key": "notice", "label": "Notice period", "context_sha256": context, "required": True,
        }], "mandatory answer missing")
        question = journal.open_questions()[0]
        journal.resolve_question(question["id"], "30 days")
        assert journal.attempt(first["id"])["state"] == "queued"
        assert journal.approved_answer("notice", context) == "30 days"
        changed_context = question_context_sha256("notice", "Notice period", "input:text", "different-context")
        assert journal.approved_answer("notice", changed_context) is None

        journal.claim_next("session-1")
        journal.transition(first["id"], ApplicationState.FILLING, "fill again")
        journal.transition(first["id"], ApplicationState.READY_TO_SUBMIT, "ready")
        assert journal.recover_pre_submit() == 1
        assert journal.attempt(first["id"])["state"] == "queued"

        second = journal.queue_controlled("fixture-2", "http://127.0.0.1:8000/form")
        journal.claim_next("session-1")
        journal.transition(second["id"], ApplicationState.FILLING, "fill")
        journal.transition(second["id"], ApplicationState.READY_TO_SUBMIT, "ready")
        journal.transition(second["id"], ApplicationState.SUBMITTING, "clicked")

    with Database(database_path, MIGRATIONS) as db:
        assert db.apply_migrations() == []
        db.recover_interrupted_work()
        journal = ApplicationJournal(db)
        journal.recover_pre_submit()
        assert journal.attempt(second["id"])["state"] == "uncertain"
        with pytest.raises(InvalidTransition):
            journal.transition(second["id"], ApplicationState.QUEUED, "UNCERTAIN must never auto-retry")
