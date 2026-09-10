CREATE TABLE source_documents (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('master_resume', 'supporting')),
    original_name TEXT NOT NULL,
    stored_relpath TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL,
    byte_size INTEGER NOT NULL CHECK (byte_size > 0),
    media_type TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    integrity_status TEXT NOT NULL DEFAULT 'verified' CHECK (integrity_status IN ('verified', 'mismatch', 'missing')),
    UNIQUE(kind, sha256)
);

CREATE UNIQUE INDEX source_documents_one_active_master
    ON source_documents(kind)
    WHERE kind = 'master_resume' AND active = 1;

CREATE TABLE template_maps (
    document_id TEXT PRIMARY KEY REFERENCES source_documents(id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (status IN ('candidate', 'confirmed')),
    confirmed_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE template_regions (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL CHECK (ordinal > 0),
    section_name TEXT NOT NULL,
    line_start INTEGER NOT NULL CHECK (line_start > 0),
    line_end INTEGER NOT NULL CHECK (line_end >= line_start),
    raw_sha256 TEXT NOT NULL,
    display_text TEXT NOT NULL,
    editable INTEGER NOT NULL DEFAULT 0 CHECK (editable IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(document_id, ordinal)
);

CREATE TABLE resume_baselines (
    document_id TEXT PRIMARY KEY REFERENCES source_documents(id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'compiled', 'failed')),
    compiler_version TEXT,
    page_count INTEGER,
    page_sizes_json TEXT,
    pdf_relpath TEXT,
    pdf_sha256 TEXT,
    text_sha256 TEXT,
    source_metrics_json TEXT,
    compile_log_relpath TEXT,
    compile_error TEXT,
    offline_verified INTEGER NOT NULL DEFAULT 0 CHECK (offline_verified IN (0, 1)),
    last_compile_used_network INTEGER NOT NULL DEFAULT 0 CHECK (last_compile_used_network IN (0, 1)),
    compiled_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE facts (
    id TEXT PRIMARY KEY,
    current_version INTEGER NOT NULL CHECK (current_version > 0),
    current_status TEXT NOT NULL CHECK (current_status IN ('candidate', 'approved', 'rejected')),
    current_category TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE fact_versions (
    fact_id TEXT NOT NULL REFERENCES facts(id) ON DELETE RESTRICT,
    version INTEGER NOT NULL CHECK (version > 0),
    value_text TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('candidate', 'approved', 'rejected')),
    source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE RESTRICT,
    source_ref_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(fact_id, version)
);

CREATE TABLE fact_bank_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    revision INTEGER NOT NULL CHECK (revision >= 0),
    updated_at TEXT NOT NULL
);

INSERT INTO fact_bank_state(id, revision, updated_at)
VALUES (1, 0, CURRENT_TIMESTAMP);
