# Progress

## Current phase

Phase 9 - Packaging and user-authorized pilot.

Status: **repository implementation and technical hardening are complete; Phase 9 remains in progress only because the measured real-world application pilot has not yet been run. Phase 4's private five-real-resume human gate also remains independently open.**

Application/local-acceptance hardening PR #17 merged at `fca1f2e8d249b82fe089c91c5be6a885f0286307`. Repository-maintenance PR #18 merged at `0f366244cc07d6bda279b48f93ccd8ebc1824a41`, pinned the Windows dependency graph/GitHub Actions, published verified `v0.1.0`, and removed merged obsolete branches. PR #19 is the `v0.1.1` live-acceptance repair for the Phase 4 prompt-context overflow, Phase 8 eligibility-note UI guard, and canonical package version.

## Phase 9 distribution/recovery

The merged distribution/recovery boundary provides:

- a verified Windows 10/11 x64 onedir distribution with per-user setup and rollback-safe upgrade;
- hermetic Playwright Chromium and WebView2 prerequisite handling;
- release SHA-256 integrity metadata;
- portable local backup/restore for database/documents/application artifacts while preserving machine-specific models/tools/browser/cache state;
- restart-bound restore with a pre-restore safety backup;
- distribution/browser/WebView notices.

## User-authorized measured-pilot implementation

The pilot implementation intentionally reuses the existing Phase 6-8 state machine, immutable packages, provider adapters and **single application worker**. It does not introduce a second scheduler or a second submit worker.

Current behavior:

- project-level pilot implementation authorization is recorded, but every process launch starts with the live lane inactive;
- activation is allowed only while Idle and requires the exact local phrase `ENABLE MEASURED REAL APPLICATION PILOT`;
- activation is memory-only and never survives restart;
- every real application must have a current immutable `PREPARED` package and a fresh read-only live-form inspection before it can be armed;
- only supported Greenhouse/Lever/Ashby HTTPS hosted-form hosts are accepted;
- CAPTCHA, login/verification, payment, assessment, unsupported required fields and ambiguous submit controls remain blockers;
- a maximum of five distinct real applications can be armed during one launch;
- the worker can claim only application IDs explicitly armed in the current launch;
- deactivation, restart and restore staging rewind queued never-submitted real work to `PREPARED`, clear prior live inspection data and require inspection plus arming again;
- immediately before any live write, package freshness and the live form are checked again;
- the current tailored PDF is resolved from app-managed storage and re-hashed immediately before upload, and is uploaded only to a recognized resume/CV upload; another required file field blocks rather than guessing;
- missing mandatory application answers use the existing exact-context human review lane;
- optional fields are not invented; they are filled only when an exact-context approved answer already exists;
- Stop/deactivation is checked again at the final pre-submit boundary;
- confirmation state is recaptured immediately before the submit click, so success-like text that appears after inspection but before submission is part of the baseline and cannot produce a false positive;
- after the submit click, any ambiguous exception or absent **new post-submit** positive employer confirmation becomes terminal `UNCERTAIN` with no automatic retry;
- only newly observed explicit positive confirmation counts as a confirmed real application.

The provider write capability is isolated behind an explicit live-write adapter mode. Default live provider adapters preserve the fail-closed `adapter writes are disabled for live employer pages` contract used by Phase 7 acceptance.

## Final technical verification

PR #17 exact head: `87f1a31325a564e392dc8881edb51b04dd2e22f0`.

All Phase 0 through Phase 9 pull-request workflows completed successfully on that exact head on 2026-09-18. PR #17 merged into `main` at `fca1f2e8d249b82fe089c91c5be6a885f0286307`; the merge commit has the same file tree as the tested PR head.

Post-merge runs on that exact `main` commit also completed successfully:

- Phase 0: `35330432453`;
- Phase 4: `35330432442`;
- Phase 9: `35330432447`.

The Phase 9 merge run passed:

- dependency vulnerability auditing with no known vulnerabilities;
- deterministic regression tests: **145 passed, 1 skipped, 2 deselected**;
- focused live-pilot/hardening tests: **8 passed**;
- backup/restore and inactive-by-default pilot checks;
- inherited Phase 8 orchestration and Phase 7 provider boundaries;
- source desktop/window/browser checks;
- hermetic Chromium PyInstaller build;
- packaged desktop/browser verification;
- verified Windows distribution build;
- clean install and in-place upgrade verification;
- distribution artifact upload.

No failed safety condition was waived.

Final repository maintenance additionally uses pip 26.2.1 to resolve the exact Windows x64 / CPython 3.13 environment from `requirements-lock.in` into hash-addressed `pylock.toml`. Isolated sdist builds use `requirements-build.in` with setuptools 84.0.0 and wheel 0.48.0. Each acceptance workflow regenerates the lock and fails if it differs before installing it. Official GitHub Actions are referenced by verified full commit SHA rather than mutable major tags. A successful Phase 9 push on `main` publishes the current project version as a GitHub Release if absent and deletes only the obsolete branches already verified as fully merged into `main`.

## v0.1.1 live-acceptance repair

A real Phase 4 run loaded the validated Qwen3/llama.cpp configuration successfully but the generated chat request contained 10,104 input tokens for a validated 4,096-token context. The excess came from prompt construction sending all approved facts and source metadata although deterministic field-local validation allows only facts linked to currently editable LaTeX regions to support edits.

PR #19 therefore:

- sends only approved facts linked to editable regions to the model and serializes only fact ID, field ID and text;
- retains the full approved fact bank and source references in deterministic validation/audit paths rather than exposing irrelevant evidence to the model;
- uses pinned b10809's `/apply-template` and `/tokenize` endpoints to count the exact templated input before `/v1/chat/completions`;
- fails with a clear local context message if the compact input itself reaches the validated context instead of surfacing an HTTP 400 traceback;
- keeps Phase 8 eligibility decisions disabled in the UI until a nonblank note exists, while preserving the backend note guard;
- bumps the patch release to `0.1.1` and removes the stale duplicate `jobpilot.__version__` value.

## Dependency and model baseline

The direct Python/build baseline revalidated on 2026-09-18 is:

- pip 26.2.1 (CI installer/lock generator);
- Playwright 1.63.0;
- pypdf 6.19.0;
- setuptools 84.0.0;
- PyInstaller 6.22.3;
- pytest 9.1.1;
- pip-audit 2.10.1;
- psutil 7.2.2;
- pywebview 6.2.1.

The validated local-AI baseline deliberately remains llama.cpp v0.4.0 / build b10809 with the accepted Qwen3 4B GGUF revision. Newer upstream llama.cpp releases are metadata only until their exact artifacts receive checksum/license records, the existing local evaluation, and the replacement review gate. Cleanup does not silently upgrade that trust boundary.

## Provider/API choice

The measured pilot continues through supported hosted applicant forms. Public Greenhouse/Lever/Ashby programmatic application APIs require employer-side integration credentials/permissions rather than candidate credentials, so JobPilot does not ask the candidate for employer API keys or pretend those server integrations are an applicant authentication mechanism.

## Repository administration boundary

Two distribution/governance items cannot be fabricated in source control:

- `main` repository protection/rulesets must be enabled through GitHub repository administration. The desired policy is pull-request-only changes with required acceptance status checks and no force-push/deletion bypass. The connected repository automation does not expose administration writes.
- publisher Authenticode signing requires a real publisher certificate/private signing identity. JobPilot does not create, embed, or fake one. The current distribution remains hash-verified; WebView2 bootstrap downloads are independently required to carry a valid Microsoft Authenticode signature.

## Remaining private product evidence

Two deliberately non-synthetic gates remain outside repository/CI completion:

- Phase 4 requires five **distinct real** tailored resumes to be explicitly approved in the user's private local JobPilot database under one current validation context. CI-controlled tailoring cannot count toward this gate.
- Phase 9 requires a **measured real-world pilot** from the user's local/private JobPilot data using individually user-armed eligible applications. Record armed/confirmed/blocked/review/stale/`UNCERTAIN` outcomes and elapsed/local-day throughput.

The visible 50/day objective remains a target rather than a capability claim until measured real-pilot evidence supports it.

See `docs/PHASE4_CLOSEOUT.md` and `docs/PHASE9_PILOT_ACCEPTANCE.md` for the exact private closeout procedures and acceptance boundaries.
