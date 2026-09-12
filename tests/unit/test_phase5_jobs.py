from jobpilot.jobs import assess_job, dedupe_jobs, normalize_manual_job, parse_board_payload
from jobpilot.settings import TargetingSettings


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
        "description": "Permanent full-time role. Required SQL and Python experience.",
    })
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

    overseas = assess_job({
        **job,
        "source_job_id": "overseas",
        "location": "London, United Kingdom",
        "description": "Permanent full-time role collaborating with teams in India. Visa sponsorship available. Required SQL experience.",
    }, targeting, facts)
    assert overseas["eligibility"] == "eligible"
