CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS foundation_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_foundation_activity_session
ON foundation_activity(session_id, id);

ALTER TABLE work_items ADD COLUMN label TEXT;
ALTER TABLE work_items ADD COLUMN is_sample INTEGER NOT NULL DEFAULT 0 CHECK (is_sample IN (0, 1));
