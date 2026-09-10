CREATE TABLE IF NOT EXISTS runtime_sessions (
    id TEXT PRIMARY KEY,
    state TEXT NOT NULL CHECK (state IN ('idle', 'running', 'paused', 'stopping', 'closing', 'exited', 'crashed')),
    started_at TEXT NOT NULL,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS work_items (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending', 'running', 'paused', 'done', 'failed', 'blocked')),
    lease_owner TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS application_attempts (
    id TEXT PRIMARY KEY,
    job_identity TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL,
    submit_started_at TEXT,
    confirmed_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS application_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id TEXT NOT NULL REFERENCES application_attempts(id) ON DELETE CASCADE,
    from_state TEXT,
    to_state TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_application_events_application
ON application_events(application_id, id);
