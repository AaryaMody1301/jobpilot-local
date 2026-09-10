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

## Phase 1 - Runnable desktop foundation [~]

Build pywebview shell, bundled local UI, navigation, SQLite application storage, targeting settings, artifact directories, Start/Pause/Stop/Close lifecycle, and crash recovery using clearly labelled sample data. No discovery, AI tailoring, or employer submissions.

Acceptance: launch idle; state/settings persist; Pause schedules no new work; Stop/Close cancel work; reopen does not resume automatically; no owned worker remains after exit.

## Phase 2 - Resume import and approved fact bank [ ]

2A immutable LaTeX import, Tectonic baseline compile, page/layout baseline, template mapping. 2B supporting-source registry and fact correction/approval/versioning. Requires the user's actual LaTeX source. No automatic rewriting or submission.

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
