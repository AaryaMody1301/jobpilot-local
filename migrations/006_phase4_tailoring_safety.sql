ALTER TABLE tailored_resumes ADD COLUMN template_map_sha256 TEXT;
ALTER TABLE tailored_resumes ADD COLUMN baseline_sha256 TEXT;
ALTER TABLE tailored_resumes ADD COLUMN profile_sha256 TEXT;
ALTER TABLE tailored_resumes ADD COLUMN review_context_sha256 TEXT;
ALTER TABLE tailored_resumes ADD COLUMN manifest_relpath TEXT;
ALTER TABLE tailored_resumes ADD COLUMN manifest_sha256 TEXT;

ALTER TABLE model_review_gates ADD COLUMN review_context_sha256 TEXT;
