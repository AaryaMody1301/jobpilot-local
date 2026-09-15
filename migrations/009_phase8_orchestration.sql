ALTER TABLE application_attempts ADD COLUMN discovered_job_id TEXT;
ALTER TABLE application_attempts ADD COLUMN tailoring_run_id TEXT;
ALTER TABLE application_attempts ADD COLUMN package_id TEXT;
ALTER TABLE application_attempts ADD COLUMN provider TEXT;
ALTER TABLE application_attempts ADD COLUMN live_apply_url TEXT;
ALTER TABLE application_attempts ADD COLUMN eligibility_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE application_attempts ADD COLUMN eligibility_resolution TEXT CHECK(eligibility_resolution IN ('approved','rejected'));
ALTER TABLE application_attempts ADD COLUMN eligibility_note TEXT;
ALTER TABLE application_attempts ADD COLUMN eligibility_resolved_at TEXT;
ALTER TABLE application_attempts ADD COLUMN orchestration_context_sha256 TEXT;
ALTER TABLE application_attempts ADD COLUMN live_form_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE application_attempts ADD COLUMN live_form_checked_at TEXT;

CREATE TABLE IF NOT EXISTS application_packages (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES application_attempts(id) ON DELETE CASCADE,
    discovered_job_id TEXT NOT NULL,
    tailoring_run_id TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    answers_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_application_packages_application_created
ON application_packages(application_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_application_attempts_phase8_job
ON application_attempts(discovered_job_id, state, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_application_attempts_phase8_history
ON application_attempts(updated_at DESC, state);
