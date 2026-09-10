# Product specification

Status: agreed for v1 unless superseded by an explicit approved entry in `DECISIONS.md`.

## Product boundary

`jobpilot-local` is a personal Windows 10/11 x64 desktop application using Python orchestration, pywebview with bundled HTML/CSS/JavaScript, SQLite migrations, app-owned local folders, llama.cpp, psutil plus supported GPU detection, Playwright, Tectonic, and pytest.

Everything runs locally. Network access is limited to job discovery, employer application sites, and explicitly approved software/model downloads. No cloud AI, hosted databases, paid APIs, paid proxies, CAPTCHA-solving services, telemetry, remote scripts, cloud sign-in, Docker requirement, vector database, or autonomous multi-agent framework.

## Session lifecycle

- No startup service or hidden scheduler.
- Launch shows the dashboard and does not schedule work.
- Start begins or resumes work.
- Pause stops scheduling new work.
- Stop keeps the app open, immediately stops discovery/generation/pre-submit work, and schedules nothing new.
- Close immediately stops discovery and generation.
- If submission may already have started, Stop or Close allows up to 60 seconds for explicit confirmation.
- An unresolved post-submit outcome becomes `UNCERTAIN`.
- `UNCERTAIN` is never automatically retried.
- Progress survives shutdown, sleep, network loss, and crashes.
- Only app-owned processes may be terminated.

## Daily objective

Target 50 confirmed, well-matched applications per local calendar day. This is not a ceiling. Continue beyond 50 while eligible work exists and the explicit desktop session is running. Eligibility, factual quality, or review requirements are never weakened to reach the target.

## Targeting defaults

- Roles: data analyst, data engineer, analytics engineer.
- Target seniority: approximately 2-5 years; actual experience always comes from approved facts.
- Office/hybrid in India: Surat only.
- Office/hybrid outside India: relocation acceptable and employer visa sponsorship required.
- Remote: only roles where working from Surat, India is permitted.
- Salary: no minimum.
- Notice period: 30 days.
- Employment: permanent full-time only.
- Exclude Brentwood Industries and normalized employer-name variants from discovery/submission.
- Preserve Brentwood Industries accurately in employment history.
- Unknown mandatory location, sponsorship, work-authorization, or other eligibility conditions require review.
- Settings are editable in the UI.

## Discovery and matching

- Public company-board discovery: Greenhouse, Lever, Ashby using verified board identifiers and documented public interfaces.
- Ship a versioned starter board registry and permit user-added verified boards.
- Manual JD/URL import for other portals.
- Direct LinkedIn, Indeed, and Naukri bots are out of v1 scope.
- Preserve source URL and retrieval time.
- Conservative deduplication by requisition identity and employer/title/location evidence.
- Separate hard eligibility, required/preferred requirements, evidence-backed matching, and ranking.
- Explanations show evidence and missing requirements; never call keyword coverage an ATS score or interview probability.

## Verified fact bank

- User supplies LaTeX resume and may supply supporting documents.
- Candidate facts retain stable ID, source reference, approval status, and version.
- Automatic tailoring may use only approved facts.
- Exact employers, titles, dates, metrics, qualifications, and skill provenance are protected.
- JD text is untrusted data and never becomes an instruction source.
- Never invent or inflate skills, tools, experience, responsibilities, leadership, employers, titles, dates, qualifications, metrics, work authorization, sponsorship, notice period, or salary answers.

## Resume tailoring

- Immutable master LaTeX source.
- Onboarding compiles the original, records page/layout baseline, maps editable wording fields, and caches required packages.
- If Tectonic cannot preserve the template, report the exact incompatibility and ask before any compiler/layout change.
- Model returns structured content edits with fact IDs, never arbitrary executable LaTeX.
- Preserve section order, bullet count, page count, margins, fonts, dates, titles, and template commands.
- No hidden text, keyword stuffing, or unsupported skills.
- Deterministic validation protects factual values, evidence references, PDF text, missing content, overflow, and page count. Model verification is supplementary only.
- Save a per-application audit package with JD snapshot/source, LaTeX/PDF, wording diff, fact-bank version/references, model version, validation result, answers, and outcome.
- First five distinct tailored resumes for a model require approval. A replacement model repeats the gate.
- Stale facts/profile/validation invalidate prepared applications.

## Local model management

- Detect available RAM, GPU memory/support, CPU capabilities, and disk space; reserve resources for Windows, other applications, JobPilot, and browser work.
- Versioned tested model catalogue records source, license, checksum, context settings, and evaluation result.
- Recommend a compatible model and show download/disk/hardware information before requesting download approval.
- Validate downloads and run memory, speed, structured-output, and factual-tailoring evaluations.
- One inference job at a time initially; avoid unnecessary vision components.
- Reduce workload or pause before memory exhaustion.
- Only installed, validated models may be switched automatically; a new download always needs approval.
- Check for newer compatible releases while open no more than weekly; never auto-trust/download a replacement.
- Replacement becomes active only after evaluation and five-resume approval. Previous app-managed weights are deleted only after safe path/use checks. Independent models are never deleted.
- If no local model meets the standard, report the limitation without cloud fallback or weakened checks.

## Browser applications

- Explicit adapters for Greenhouse, Lever, and Ashby with common inspect/support/fill/submit/confirm operations.
- Approved factual answers only; explanatory text must derive from approved facts and JD.
- Unknown mandatory questions enter a review queue while other work continues.
- Reuse answers only when meaning/context match.
- Stop on CAPTCHA, assessment, login/verification challenge, unsupported form, or payment request.
- Dedicated app browser profile with local session storage and OS secret protection where practical.
- Transactional duplicate prevention and a single submission worker.
- Mark submitted only after explicit positive confirmation.
- Timeout/ambiguity after Submit becomes `UNCERTAIN`, never retryable failure.
- Respect source rate limits and back off.

## UI

Dashboard, Start/Pause/Stop, job list with explanations/gaps, resume PDF/diff/fact mapping, first-five review, questions/blocked work, application history, model/download/resource screens, targeting/answer settings, local export/backup/restore. UI must be understandable without technical knowledge.

## Development and pilot safety

- Controlled fixtures only for submission tests.
- Live employer pages may be used read-only for form recognition.
- No real applications during development.
- Real submission requires explicit user activation after onboarding/review.
- Never report prepared applications as submitted or promise 50/day without measured evidence.
