# Progress

## Current phase

Phase 9 - Packaging and user-authorized pilot.

Status: **repository implementation and technical hardening are complete; Phase 9 remains in progress only because the measured real-world application pilot has not yet been run. Phase 4's private five-real-resume human gate also remains independently open.**

Final repository-level closeout PR #16 merged into `main` at `f5df77697b667f14df55583d94058f175ece5074` after its exact head passed all Phase 0 through Phase 9 workflows. The final cleanup then reconciled roadmap/progress metadata with that merged baseline.

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

PR #16 exact head: `2004157ad079ffdfe51f17f86155b8b2027f09d7`.

All Phase 0 through Phase 9 pull-request workflows completed successfully on that exact head on 2026-09-17. The final Phase 9 run passed:

- dependency vulnerability auditing;
- deterministic regression tests including the final Phase 9 UI interaction regression at the 960x660 minimum viewport;
- the focused live-pilot/hardening tests, including delayed pre-submit success-text protection;
- backup/restore and inactive-by-default pilot checks;
- inherited Phase 8 orchestration and Phase 7 provider boundaries;
- source desktop/window/browser checks;
- hermetic Chromium PyInstaller build;
- packaged desktop/browser verification;
- verified Windows distribution build;
- clean install and in-place upgrade verification;
- distribution artifact upload.

The merged `main` commit is `f5df77697b667f14df55583d94058f175ece5074`. Its Phase 0, Phase 4 and Phase 9 push workflows were also observed completing successfully before the final cleanup request.

No failed safety condition was waived.

## Dependency and model baseline

The final Python/build baseline accepted on 2026-09-17 is:

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

## Remaining private product evidence

Two deliberately non-synthetic gates remain outside repository/CI completion:

- Phase 4 requires five **distinct real** tailored resumes to be explicitly approved in the user's private local JobPilot database under one current validation context. CI-controlled tailoring cannot count toward this gate.
- Phase 9 requires a **measured real-world pilot** from the user's local/private JobPilot data using individually user-armed eligible applications. Record armed/confirmed/blocked/review/stale/`UNCERTAIN` outcomes and elapsed/local-day throughput.

The visible 50/day objective remains a target rather than a capability claim until measured real-pilot evidence supports it.

See `docs/PHASE4_CLOSEOUT.md` and `docs/PHASE9_PILOT_ACCEPTANCE.md` for the exact private closeout procedures and acceptance boundaries.
