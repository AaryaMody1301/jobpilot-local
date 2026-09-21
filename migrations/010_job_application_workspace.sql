ALTER TABLE discovered_jobs ADD COLUMN compensation_text TEXT;
ALTER TABLE discovered_jobs ADD COLUMN application_deadline TEXT;

ALTER TABLE application_attempts ADD COLUMN follow_up_at TEXT;
ALTER TABLE application_attempts ADD COLUMN notes TEXT NOT NULL DEFAULT '';
ALTER TABLE application_attempts ADD COLUMN next_action TEXT NOT NULL DEFAULT '';
ALTER TABLE application_attempts ADD COLUMN workspace_updated_at TEXT;

CREATE INDEX IF NOT EXISTS idx_application_attempts_follow_up
ON application_attempts(follow_up_at, state);
