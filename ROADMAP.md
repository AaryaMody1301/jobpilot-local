# Roadmap

Status legend: `[ ] planned`, `[~] in progress`, `[x] complete`, `[!] blocked/partial`.

## Phase 0 - Feasibility and architecture [x]

User-visible outcome: no employer automation yet; reviewed architecture and executable feasibility probes for the highest-risk local/Windows behaviors.

Dependencies: none.

Deliverables:
- [x] authoritative `SPEC.md`, `ROADMAP.md`, `DECISIONS.md`, `PROGRESS.md` records;
- [x] module/trust/data/state architecture;
- [x] dependency/version/license research and notices;
- [x] deterministic session/application state-machine primitives;
- [x] managed-path deletion boundary;
- [x] SQLite migration and interrupted-work recovery spike;
- [x] Windows suspended-process + Job Object ownership spike;
- [x] Tectonic cached/untrusted command boundary;
- [x] llama.cpp structured-response request/validation boundary;
- [x] Playwright controlled-form read-only recognition fixture;
- [x] Windows CI definition for reproducible Phase 0 checks;
- [x] Windows CI acceptance evidence: corrected Phase 0 commit passed 28 non-external tests, Chromium fixture recognition, Windows Job Object checks, PyInstaller onedir build, and packaged self-test;
- [x] external Tectonic/llama.cpp probes defined and intentionally deferred to the phases that have an approved compiler cache/model; they are not Phase 0 completion blockers.

Later interfaces: `SessionStateMachine`, `ApplicationStateMachine`, `ProcessSupervisor`, `Database`, `ManagedPaths`, `TectonicCompiler`, `LlamaServerClient`, `ApplicationAdapter`.

Acceptance: see `docs/PHASE0_ACCEPTANCE.md`.

Completion blockers: any Windows ownership test that kills an unrelated process, a state path that makes an uncertain submission retryable, inability to cancel close/new work deterministically, or inability to run the chosen local runtime components on the Windows target.

## Phase 1 - Runnable desktop foundation [x]

User-visible outcome: a runnable local pywebview dashboard with navigation, editable targeting settings, persistent SQLite state, app-owned folders, Start/Pause/Stop/Close lifecycle, crash recovery, and clearly labelled sample work only.

Dependencies: Phase 0 lifecycle, storage, process-ownership, and packaging decisions.

Deliverables:
- [x] local pywebview shell and bundled HTML/CSS/JavaScript UI with no remote scripts or telemetry;
- [x] SQLite Phase 1 migration, persistent targeting settings, runtime sessions, activity history, and sample queue metadata;
- [x] full app-owned local directory structure outside Git;
- [x] Start/Pause/Stop/Close controller and sample-only worker created only by explicit Start;
- [x] crash recovery that launches idle and requeues safe interrupted sample work;
- [x] editable targeting controls for all agreed Phase 1 preferences;
- [x] migration upgrade test from a Phase 0 database;
- [x] source and packaged lifecycle self-tests;
- [x] real Windows pywebview/WebView2 hidden-window bridge smoke;
- [x] PyInstaller onedir desktop package feasibility build;
- [x] Windows acceptance run `34455123604`: 50 tests passed, 2 external tests deselected; source/package self-tests and source/package hidden-window smokes passed.

Interfaces retained for later phases: `ApplicationController`, `DesktopBridge`, `Database`, `ManagedPaths`, `TargetingSettings`, session state machine, and the explicit work scheduling boundary.

Acceptance: see `docs/PHASE1_ACCEPTANCE.md`.

Known boundary: this phase contains no job discovery, AI inference, resume rewriting, application form filling, or employer submission. The dashboard's application count remains zero; sample work is never presented as an application.

## Phase 2 - Resume import and approved fact bank [x]

2A immutable LaTeX import, Tectonic baseline compile, page/layout baseline, template mapping. 2B supporting-source registry and fact correction/approval/versioning. No automatic rewriting or submission.

Completed:
- [x] migration `003_phase2_resume_fact_bank.sql` for immutable source metadata, template maps/regions, resume baseline, versioned facts, and fact-bank revision;
- [x] native file-picker boundary for master `.tex` and supported evidence files; JavaScript cannot supply arbitrary filesystem paths;
- [x] byte-for-byte app-owned master/source copies with SHA-256 integrity checks, deduplication, and retained historical source versions;
- [x] candidate bullet-region mapping with source line ranges/raw hashes; regions start non-editable and mapping changes invalidate confirmation;
- [x] candidate fact creation with stable IDs, source references, versions, correction history, explicit approve/reject, and source-integrity recheck before approval;
- [x] protected non-bullet fact extraction for role title/date/employer/location, summary text, technical skills, project stack lines, education, professional development, and languages;
- [x] inactive historical master facts remain retained but cannot block the active resume's approval gate;
- [x] checksum-pinned app-managed Tectonic 0.17.0 installer requiring an explicit user action;
- [x] explicit cache-populating compile followed by mandatory `--only-cached --untrusted` baseline verification;
- [x] baseline page count/page geometry/PDF hash/extracted-text hash/source metrics and compile-log persistence;
- [x] onboarding-ready gate requiring verified master integrity, successful cached-only baseline, confirmed mapping, zero unresolved candidate facts, and at least one approved fact;
- [x] Phase 2 UI for import, compiler/cache state, baseline status, editable-region review, fact review, and supporting sources;
- [x] Phase 0→1→2 migration regression coverage and controlled Playwright UI coverage;
- [x] Windows acceptance on finalization head `82713e3393ca29104394059bac222d4bd7c9d065`: 70 passed, 1 intentional platform-guard skip, 2 external tests deselected; real Tectonic network→cache→offline acceptance passed; source/package self-tests and source/package WebView2 smokes passed;
- [x] user-provided real template structure reviewed outside Git: two A4 pages, 23 standard `\item` regions, seven sections, three `\role` calls, no `write18`, and no overfull/underfull box warnings in the local validation pass;
- [x] sanitized structural fixture matching the real package/font/layout/custom-command shape compiled with Tectonic 0.17.0 and recompiled cached-only to two pages on Windows CI;
- [x] user explicitly approved all factual claims in the supplied resume exactly as written on 2026-09-11. The private claim text is not committed to Git.

Acceptance: see `docs/PHASE2_ACCEPTANCE.md` and `PROGRESS.md`.

## Phase 3 - Local AI and resource manager [ ]

3A RAM/CPU/disk/GPU detection and budgets. 3B approved model/binary download, checksum validation, one-job inference. 3C speed/memory/structured-output/factual-tailoring evaluation plus safe replacement/rollback/deletion. Exact llama.cpp/model pin occurs here.

## Phase 4 - Evidence-based resume tailoring [ ]

4A JD-as-data parsing and structured fact-linked edits. 4B deterministic factual/LaTeX/PDF/layout validation. 4C first-five distinct resume approval gate for the active model. Manual JD input only.

## Phase 5 - Job discovery and matching [ ]

5A normalization/manual import. 5B verified Greenhouse/Lever/Ashby starter registry and discovery. 5C hard eligibility, required/preferred requirements, evidence matching, conservative deduplication, explainable ranking, Brentwood exclusion.

## Phase 6 - Application engine using controlled forms [ ]

6A transactional application journal/single worker. 6B controlled Playwright fixture engine and approved answers. 6C CAPTCHA/challenge/unknown question/duplicate/crash/network/sleep/close recovery suite. No real employers.

## Phase 7 - Supported hiring-platform adapters [ ]

7A Greenhouse, then 7B Lever, then 7C Ashby. Each adapter must pass controlled submissions and read-only live form recognition before the next begins. Unsupported variants are reported, not guessed.

## Phase 8 - End-to-end orchestration [ ]

Connect session-scoped discovery, matching, tailoring, gates, queues, attention lane, submission, resource pressure, stale-package invalidation, history, and daily confirmed counter. The target is 50 confirmed applications with no ceiling and no relaxed requirements.

## Phase 9 - Packaging and user-authorized pilot [ ]

9A Windows onedir package, setup/upgrade docs, local backup/restore, notices, clean-machine tests. 9B separate explicit real-application activation followed by measured pilot and honest acceptance report. Do not claim 50/day without evidence.
