# Data model contract

This document defines the durable entities and metadata that migrations must preserve.

## Candidate and evidence

- `candidate_profiles`: versioned targeting/profile snapshot.
- `source_documents`: immutable file hash, source type, path, import time.
- `fact_versions`: stable fact ID, version, typed value, source reference, approval status/time.
- `approved_answers`: normalized semantic question key, context constraints, fact references, value/version.

## Resume

- `master_resumes`: immutable LaTeX source hash/path, compiler baseline, page count.
- `template_mappings`: editable field IDs and immutable template anchors.
- `tailored_resumes`: job/profile/fact/model versions, source/PDF paths, validation state.
- `resume_edits`: field ID, before/after wording, cited fact IDs, validation result.
- `resume_reviews`: approval/rejection for first-five/model replacement gates.

## Models

- `model_catalogue`: source, license, expected checksum/size/context/backend compatibility.
- `model_installations`: managed path, verified checksum, install state.
- `model_evaluations`: hardware profile, speed/memory/schema/factual scores, pass/fail.
- `model_activations`: active model plus review-gate state; weight deletion never deletes metadata.

## Jobs

- `boards`: platform, verified identifier, source, enabled/version.
- `job_snapshots`: original source URL/payload hash/retrieval time.
- `jobs`: normalized employer/title/location/requisition/apply identity plus optional provider-supplied compensation and application deadline metadata.
- `eligibility_results`: hard conditions and unknown/review reasons.
- `requirements`: required/preferred evidence units.
- `match_evidence`: approved fact/skill references and explanations.
- `dedupe_links`: conservative duplicate relationships and reason.

## Applications

- `application_packages`: immutable manifest tying JD, tailored resume, profile/facts/model/answers to one attempt.
- `application_attempts`: state, idempotency identity, irreversible-submit timestamp, confirmation/outcome, plus user workspace metadata (`follow_up_at`, notes, next action) that never changes the state machine.
- `application_events`: append-only transition/reason evidence.
- `blocked_questions`: mandatory unfamiliar questions and resolution.
- Application workspace views may join the saved job snapshot, exact tailoring run and immutable package for presentation; those historical links are not rewritten by follow-up/notes edits.

## Runtime

- `runtime_sessions`: explicit Start/Stop/Close session journal.
- `work_items`: persistent queue/lease/checkpoint state.
- `schema_migrations`: migration ledger.

## Version/staleness rule

Prepared work is usable only if its recorded profile, fact-bank, approved-answer, model, resume-template, and validation versions remain current. A change does not rewrite historical packages; it marks incompatible prepared work stale.
