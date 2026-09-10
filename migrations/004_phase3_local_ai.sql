CREATE TABLE IF NOT EXISTS hardware_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    platform_json TEXT NOT NULL,
    memory_json TEXT NOT NULL,
    cpu_json TEXT NOT NULL,
    disk_json TEXT NOT NULL,
    gpu_json TEXT NOT NULL,
    budget_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_installs (
    id TEXT PRIMARY KEY,
    catalogue_id TEXT NOT NULL,
    version TEXT NOT NULL,
    backend TEXT NOT NULL,
    install_relpath TEXT NOT NULL,
    executable_relpath TEXT NOT NULL,
    artifact_sha256 TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('installed','failed','retired')),
    installed_at TEXT NOT NULL,
    last_verified_at TEXT NOT NULL,
    failure_message TEXT
);

CREATE TABLE IF NOT EXISTS model_installs (
    id TEXT PRIMARY KEY,
    catalogue_id TEXT NOT NULL,
    source_revision TEXT NOT NULL,
    model_relpath TEXT NOT NULL,
    artifact_sha256 TEXT NOT NULL,
    artifact_bytes INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('installed','evaluating','validated','failed','retired')),
    installed_at TEXT NOT NULL,
    last_verified_at TEXT NOT NULL,
    failure_message TEXT
);

CREATE TABLE IF NOT EXISTS model_evaluations (
    id TEXT PRIMARY KEY,
    model_install_id TEXT NOT NULL REFERENCES model_installs(id),
    runtime_install_id TEXT NOT NULL REFERENCES runtime_installs(id),
    suite_version TEXT NOT NULL,
    backend TEXT NOT NULL,
    context_tokens INTEGER NOT NULL,
    elapsed_ms INTEGER NOT NULL,
    peak_rss_bytes INTEGER,
    structured_pass INTEGER NOT NULL CHECK(structured_pass IN (0,1)),
    factual_pass INTEGER NOT NULL CHECK(factual_pass IN (0,1)),
    tailoring_pass INTEGER NOT NULL CHECK(tailoring_pass IN (0,1)),
    resource_pass INTEGER NOT NULL CHECK(resource_pass IN (0,1)),
    overall_pass INTEGER NOT NULL CHECK(overall_pass IN (0,1)),
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS model_state (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    selected_model_install_id TEXT REFERENCES model_installs(id),
    selected_runtime_install_id TEXT REFERENCES runtime_installs(id),
    auto_tailoring_model_install_id TEXT REFERENCES model_installs(id),
    previous_auto_model_install_id TEXT REFERENCES model_installs(id),
    cleanup_pending_relpath TEXT,
    last_catalogue_check_at TEXT,
    last_catalogue_check_json TEXT,
    updated_at TEXT NOT NULL
);

INSERT OR IGNORE INTO model_state(id, updated_at)
VALUES (1, CURRENT_TIMESTAMP);

CREATE INDEX IF NOT EXISTS idx_model_evaluations_model_created
ON model_evaluations(model_install_id, created_at DESC);
