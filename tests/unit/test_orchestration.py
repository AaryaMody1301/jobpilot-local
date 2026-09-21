from __future__ import annotations

from pathlib import Path

import pytest

from jobpilot.jobs import JobStore, normalize_manual_job
from jobpilot.orchestration import Phase8ApplicationJournal
from jobpilot.storage.database import Database, utc_now_text

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


class _FakeTailoringStore:
    def __init__(self) -> None:
        self.run: dict[str, object] | None = None

    def get_run(self, run_id: str) -> dict[str, object] | None:
        if self.run and self.run["id"] == run_id:
            return dict(self.run)
        return None


class _FakeTailoring:
    def __init__(self) -> None:
        self.store = _FakeTailoringStore()
        self.stale_reason: str | None = None

    def _stale_reason(self, run: object) -> str | None:
        return self.stale_reason

    def _verify_run_artifacts(self, run: object) -> None:
        return

    def auto_tailoring_is_current(self) -> bool:
        return True


def _job(store: JobStore, suffix: str) -> dict[str, object]:
    store.upsert(normalize_manual_job({
        "employer": "Phase 8 Fixture Co",
        "title": "Data Analyst",
        "location": "Surat, India",
        "workplace_type": "onsite",
        "employment_type": "permanent_full_time",
        "source_url": f"https://example.invalid/jobs/{suffix}",
        "apply_url": f"https://example.invalid/jobs/{suffix}/apply",
        "description": "Permanent full-time data analyst role in Surat.",
    }))
    return next(item for item in store.jobs() if str(item["source_url"]).endswith(f"/{suffix}"))


def test_phase8_eligibility_review_and_package_staleness_are_transactional(tmp_path: Path) -> None:
    with Database(tmp_path / "jobpilot.sqlite3", MIGRATIONS) as db:
        db.apply_migrations()
        jobs = JobStore(db)
        tailoring = _FakeTailoring()
        journal = Phase8ApplicationJournal(db, tailoring)  # type: ignore[arg-type]

        review_job = _job(jobs, "review")
        review = journal.register_discovered_job(review_job, {
            **review_job,
            "eligibility": "review",
            "hard_reasons": [],
            "review_reasons": ["work authorization requires review"],
        })
        assert review["state"] == "needs_review"
        with pytest.raises(ValueError, match="requires a note"):
            journal.resolve_eligibility(str(review["id"]), True, "   ")
        resolved = journal.resolve_eligibility(str(review["id"]), True, "candidate confirmed the mandatory condition")
        assert resolved["state"] == "eligible"
        assert resolved["eligibility_resolution"] == "approved"

        operational_updated_at = resolved["updated_at"]
        workspace = journal.update_workspace(
            str(review["id"]),
            follow_up_at="2026-10-01",
            notes="Recruiter asked for a follow-up after the screening call.",
            next_action="Send follow-up",
        )
        assert workspace["updated_at"] == operational_updated_at
        assert workspace["workspace_updated_at"] is not None
        assert workspace["follow_up_at"] == "2026-10-01"
        assert workspace["notes"].startswith("Recruiter asked")
        assert workspace["next_action"] == "Send follow-up"
        history_item = next(item for item in journal.history() if item["id"] == review["id"])
        assert history_item["follow_up_at"] == "2026-10-01"
        with pytest.raises(ValueError, match="ISO-8601"):
            journal.update_workspace(str(review["id"]), follow_up_at="not-a-date", notes="", next_action="")

        package_job = _job(jobs, "package")
        application = journal.register_discovered_job(package_job, {
            **package_job,
            "eligibility": "eligible",
            "hard_reasons": [],
            "review_reasons": [],
        })
        journal.begin_tailoring(str(application["id"]))
        tailoring.store.run = {
            "id": "tailored-run-1",
            "status": "approved",
            "validation": {"overall_pass": True},
            "manifest_sha256": "a" * 64,
            "pdf_sha256": "b" * 64,
            "master_sha256": "c" * 64,
            "fact_bank_revision": 7,
            "model_install_id": "model-1",
            "runtime_install_id": "runtime-1",
            "device_id": "none",
            "review_context_sha256": "d" * 64,
        }
        journal.set_tailoring_run(str(application["id"]), "tailored-run-1")
        prepared = journal.finish_tailoring(str(application["id"]), tailoring.store.run)
        assert prepared["state"] == "prepared"
        assert prepared["package_id"]
        journal.queue_prepared_controlled(str(application["id"]), "http://127.0.0.1:8000/form")

        now = utc_now_text()
        with db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO approved_application_answers(
                    id, question_key, context_sha256, label, answer, approved_at
                ) VALUES ('answer-1', 'notice', ?, 'Notice period', '30 days', ?)
                """,
                ("e" * 64, now),
            )

        assert journal.claim_next("session-1") is None
        stale = journal.attempt(str(application["id"]))
        assert stale["state"] == "stale"
        assert "approved application answers changed" in stale["last_reason"]
        assert journal.daily_progress()["confirmed_real"] == 0
        assert journal.daily_progress()["target_confirmed"] == 50
