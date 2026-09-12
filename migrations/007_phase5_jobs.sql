CREATE TABLE IF NOT EXISTS job_boards (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL CHECK(provider IN ('greenhouse', 'lever', 'ashby')),
    employer TEXT NOT NULL,
    board_token TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0, 1)),
    user_added INTEGER NOT NULL DEFAULT 0 CHECK(user_added IN (0, 1)),
    verification_source TEXT NOT NULL,
    verified_at TEXT NOT NULL,
    last_checked_at TEXT,
    last_error TEXT,
    UNIQUE(provider, board_token)
);

INSERT OR IGNORE INTO job_boards(id, provider, employer, board_token, enabled, user_added, verification_source, verified_at)
VALUES
    ('greenhouse:gitlabcrm', 'greenhouse', 'GitLab', 'gitlabcrm', 1, 0, 'GitLab public careers links + Greenhouse Job Board API', '2026-09-12T00:00:00Z'),
    ('lever:lever', 'lever', 'Lever', 'lever', 1, 0, 'Lever official Postings API documentation', '2026-09-12T00:00:00Z'),
    ('ashby:ashby', 'ashby', 'Ashby', 'Ashby', 1, 0, 'Ashby official public Job Postings API documentation', '2026-09-12T00:00:00Z');

CREATE TABLE IF NOT EXISTS discovered_jobs (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL CHECK(provider IN ('greenhouse', 'lever', 'ashby', 'manual')),
    board_id TEXT REFERENCES job_boards(id),
    board_token TEXT NOT NULL DEFAULT '',
    source_job_id TEXT NOT NULL,
    employer TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT NOT NULL,
    workplace_type TEXT,
    employment_type TEXT,
    source_url TEXT NOT NULL,
    apply_url TEXT,
    description TEXT NOT NULL,
    published_at TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    content_sha256 TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_discovered_jobs_last_seen ON discovered_jobs(last_seen_at DESC);
