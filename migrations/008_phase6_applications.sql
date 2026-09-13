ALTER TABLE application_attempts ADD COLUMN target_url TEXT;
ALTER TABLE application_attempts ADD COLUMN controlled_fixture INTEGER NOT NULL DEFAULT 0 CHECK(controlled_fixture IN (0, 1));
ALTER TABLE application_attempts ADD COLUMN lease_owner TEXT;
ALTER TABLE application_attempts ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE application_attempts ADD COLUMN next_retry_at TEXT;
ALTER TABLE application_attempts ADD COLUMN last_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE application_attempts ADD COLUMN created_at TEXT;

CREATE TABLE IF NOT EXISTS approved_application_answers (
    id TEXT PRIMARY KEY,
    question_key TEXT NOT NULL,
    context_sha256 TEXT NOT NULL,
    label TEXT NOT NULL,
    answer TEXT NOT NULL,
    approved_at TEXT NOT NULL,
    UNIQUE(question_key, context_sha256)
);

CREATE TABLE IF NOT EXISTS application_questions (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES application_attempts(id) ON DELETE CASCADE,
    question_key TEXT NOT NULL,
    context_sha256 TEXT NOT NULL,
    label TEXT NOT NULL,
    required INTEGER NOT NULL CHECK(required IN (0, 1)),
    state TEXT NOT NULL CHECK(state IN ('review', 'answered')),
    answer_id TEXT REFERENCES approved_application_answers(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(application_id, question_key, context_sha256)
);

CREATE INDEX IF NOT EXISTS idx_application_attempts_phase6_queue
ON application_attempts(controlled_fixture, state, next_retry_at, created_at);

CREATE INDEX IF NOT EXISTS idx_application_questions_review
ON application_questions(state, application_id);
