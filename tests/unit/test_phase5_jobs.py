from pathlib import Path

import jobpilot.jobs as jobs_module
from jobpilot.jobs import JobStore, assess_job, dedupe_jobs, fetch_job_metadata, normalize_manual_job, parse_board_payload
from jobpilot.settings import TargetingSettings
from jobpilot.storage.database import Database

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "migrations"


def test_supported_board_payloads_normalize_to_one_job_shape() -> None:
    payloads = {
        "greenhouse": {
            "jobs": [{
                "id": 10,
                "title": "Data Engineer",
                "location": {"name": "Surat, India"},
                "content": "&lt;p&gt;Required SQL and Python experience.&lt;/p&gt;",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/10",
                "updated_at": "2026-09-12T00:00:00Z",
            }]
        },
        "lever": [{
            "id": "abc",
            "text": "Data Engineer",
            "categories": {"location": "Surat, India", "commitment": "Full-time"},
            "descriptionPlain": "Required SQL and Python experience.",
            "hostedUrl": "https://jobs.lever.co/acme/abc",
            "applyUrl": "https://jobs.lever.co/acme/abc/apply",
            "workplaceType": "on-site",
            "salaryRange": {"currency": "INR", "min": 1800000, "max": 2400000, "interval": "per-year-salary"},
        }],
        "ashby": {
            "jobs": [{
                "id": "job-1",
                "title": "Data Engineer",
                "location": "Surat, India",
                "descriptionPlain": "Required SQL and Python experience.",
                "workplaceType": "OnSite",
                "employmentType": "FullTime",
                "jobUrl": "https://jobs.ashbyhq.com/acme/job-1",
                "applyUrl": "https://jobs.ashbyhq.com/acme/job-1/application",
                "compensation": {"scrapeableCompensationSalarySummary": "INR 18L - 24L"},
                "isListed": True,
            }]
        },
    }
    for provider, payload in payloads.items():
        jobs = parse_board_payload(provider, "Acme", "acme", payload)
        assert len(jobs) == 1
        assert jobs[0]["provider"] == provider
        assert jobs[0]["title"] == "Data Engineer"
        assert jobs[0]["source_url"].startswith("https://")
        assert jobs[0]["description"] == "Required SQL and Python experience."
        if provider == "lever":
            assert jobs[0]["compensation_text"] == "INR 1800000 - 2400000 (per-year-salary)"
        if provider == "ashby":
            assert jobs[0]["compensation_text"] == "INR 18L - 24L"


def test_matching_is_conservative_explainable_and_deduplicated() -> None:
    targeting = TargetingSettings()
    facts = [{"value_text": "Built production SQL and Python data pipelines."}]
    job = normalize_manual_job({
        "employer": "Acme Analytics",
        "title": "Data Engineer",
        "location": "Surat, India",
        "workplace_type": "onsite",
        "employment_type": "permanent_full_time",
        "source_url": "https://example.invalid/jobs/1",
        "compensation_text": "INR 18L - 24L",
        "application_deadline": "2026-10-15",
        "description": "Permanent full-time role. Required SQL and Python experience.",
    })
    assert job["compensation_text"] == "INR 18L - 24L"
    assert job["application_deadline"] == "2026-10-15"
    assessed = assess_job(job, targeting, facts)
    assert assessed["eligibility"] == "eligible"
    assert assessed["matched_required"] == ["Required SQL and Python experience."]
    assert assessed["score"] > 0 and assessed["score_reasons"]["required_evidence"] > 0
    assert len(dedupe_jobs([job, dict(job)])) == 1

    excluded = assess_job({**job, "employer": "Brentwood Industries"}, targeting, facts)
    assert excluded["eligibility"] == "ineligible"
    assert any("excluded" in reason for reason in excluded["hard_reasons"])

    remote_us = assess_job({
        **job,
        "source_job_id": "remote-us",
        "location": "Remote",
        "workplace_type": "remote",
        "description": "Remote U.S. only. Required SQL experience.",
    }, targeting, facts)
    assert remote_us["eligibility"] == "ineligible"
    assert any("United States" in reason for reason in remote_us["hard_reasons"])

    preferred_seniority = assess_job({
        **job,
        "source_job_id": "preferred-seniority",
        "description": "Permanent full-time role. 7 years of experience preferred. Required SQL experience.",
    }, targeting, facts)
    assert preferred_seniority["eligibility"] == "eligible"
    assert not any("minimum experience" in reason for reason in preferred_seniority["hard_reasons"])

    unsupported_years = assess_job({
        **job,
        "source_job_id": "required-years",
        "description": "Permanent full-time role. Required 5 years of SQL experience.",
    }, targeting, facts)
    assert unsupported_years["eligibility"] == "eligible"
    assert unsupported_years["matched_required"] == []

    work_auth = assess_job({
        **job,
        "source_job_id": "work-auth",
        "location": "Remote, India",
        "workplace_type": "remote",
        "description": "Remote from India. Must be authorized to work in the United States. Required SQL experience.",
    }, targeting, facts)
    assert work_auth["eligibility"] == "review"
    assert any("work-authorization" in reason for reason in work_auth["review_reasons"])

    overseas = assess_job({
        **job,
        "source_job_id": "overseas",
        "location": "London, United Kingdom",
        "description": "Permanent full-time role collaborating with teams in India. Visa sponsorship available. Required SQL experience.",
    }, targeting, facts)
    assert overseas["eligibility"] == "eligible"


def test_board_refresh_hides_jobs_removed_from_the_current_feed(tmp_path: Path) -> None:
    with Database(tmp_path / "jobpilot.sqlite3", MIGRATIONS) as db:
        db.apply_migrations()
        store = JobStore(db)
        board = store.add_board("lever", "Acme", "acme", verification_source="test")
        payload = [
            {
                "id": "keep",
                "text": "Data Engineer",
                "categories": {"location": "Surat, India", "commitment": "Full-time"},
                "descriptionPlain": "Required SQL experience.",
                "hostedUrl": "https://jobs.lever.co/acme/keep",
            },
            {
                "id": "gone",
                "text": "Data Analyst",
                "categories": {"location": "Surat, India", "commitment": "Full-time"},
                "descriptionPlain": "Required SQL experience.",
                "hostedUrl": "https://jobs.lever.co/acme/gone",
            },
        ]
        store.replace_board_jobs(str(board["id"]), parse_board_payload("lever", "Acme", "acme", payload))
        store.replace_board_jobs(str(board["id"]), parse_board_payload("lever", "Acme", "acme", payload[:1]))
        assert [job["source_job_id"] for job in store.jobs()] == ["keep"]
        inactive = db.connection.execute("SELECT active FROM discovered_jobs WHERE source_job_id='gone'").fetchone()
        assert inactive is not None and inactive["active"] == 0


def test_greenhouse_detail_refresh_extracts_deadline_and_pay_without_board_crawl(monkeypatch) -> None:
    monkeypatch.setattr(
        jobs_module,
        "_json_get",
        lambda url: {
            "application_deadline": "2026-10-31T23:59:59Z",
            "pay_input_ranges": [{
                "min_cents": 5000000,
                "max_cents": 7500000,
                "currency_type": "USD",
                "title": "Salary Range",
            }],
        },
    )
    metadata = fetch_job_metadata({
        "provider": "greenhouse",
        "board_token": "acme",
        "source_job_id": "12345",
        "compensation_text": None,
        "application_deadline": None,
    })
    assert metadata["application_deadline"] == "2026-10-31T23:59:59Z"
    assert metadata["compensation_text"] == "Salary Range: USD 50000 - 75000"
