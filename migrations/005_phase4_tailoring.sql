CREATE TABLE IF NOT EXISTS manual_job_descriptions (
    id TEXT PRIMARY KEY,
    source_url TEXT,
    jd_sha256 TEXT NOT NULL,
    jd_text TEXT NOT NULL,
    instruction_like INTEGER NOT NULL DEFAULT 0 CHECK(instruction_like IN (0,1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_manual_job_descriptions_sha
ON manual_job_descriptions(jd_sha256, created_at DESC);

CREATE TABLE IF NOT EXISTS tailored_resumes (
    id TEXT PRIMARY KEY,
    jd_id TEXT NOT NULL REFERENCES manual_job_descriptions(id),
    master_document_id TEXT NOT NULL REFERENCES source_documents(id),
    master_sha256 TEXT NOT NULL,
    fact_bank_revision INTEGER NOT NULL,
    model_install_id TEXT NOT NULL REFERENCES model_installs(id),
    runtime_install_id TEXT NOT NULL REFERENCES runtime_installs(id),
    device_id TEXT NOT NULL,
    resume_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'generating','needs_review','approved','rejected','auto_validated','blocked','stale','failed'
    )),
    source_relpath TEXT,
    pdf_relpath TEXT,
    source_sha256 TEXT,
    pdf_sha256 TEXT,
    diff_json TEXT NOT NULL DEFAULT '[]',
    keyword_mapping_json TEXT NOT NULL DEFAULT '[]',
    fact_refs_json TEXT NOT NULL DEFAULT '[]',
    validation_json TEXT NOT NULL DEFAULT '{}',
    model_usage_json TEXT NOT NULL DEFAULT '{}',
    failure_message TEXT,
    review_note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    reviewed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_tailored_resumes_jd_created
ON tailored_resumes(jd_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tailored_resumes_model_created
ON tailored_resumes(model_install_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tailored_resumes_status
ON tailored_resumes(status, updated_at DESC);
