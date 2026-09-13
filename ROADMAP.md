# Roadmap

Status legend: `[ ] planned`, `[~] in progress`, `[x] complete`, `[!] blocked/partial`.

## Phase 0 - Feasibility and architecture [x]

Windows/local-first architecture, lifecycle/state model, managed process/file ownership, SQLite recovery, Tectonic/llama.cpp trust boundaries, controlled browser feasibility, and Windows acceptance.

Acceptance: `docs/PHASE0_ACCEPTANCE.md`.

## Phase 1 - Runnable desktop foundation [x]

Bundled pywebview desktop, persistent settings/runtime/activity state, Start/Pause/Stop/Close lifecycle, crash recovery, targeting controls, packaging, and Windows smoke acceptance.

Acceptance: `docs/PHASE1_ACCEPTANCE.md`.

## Phase 2 - Resume import and approved fact bank [x]

Immutable LaTeX source import, Tectonic offline baseline, confirmed editable map, source-linked fact versions, protected non-bullet facts, explicit fact review, and real supplied-template acceptance.

Acceptance: `docs/PHASE2_ACCEPTANCE.md`.

## Phase 3 - Local AI and resource manager [x]

Hardware/resource evidence, pinned app-managed llama.cpp/Qwen catalogue, checksum-verified installs, local evaluation, one-inference ownership, pressure handling, revision-safe replacement/rollback, and persisted review gate.

Acceptance: `docs/PHASE3_ACCEPTANCE.md`.

## Phase 4 - Evidence-based resume tailoring [!]

Technical implementation is complete and merged: JD-as-data handling, field-local approved-fact edits, deterministic LaTeX/PDF validation, tamper-evident run packages, staleness/context binding, review UI, and automatic-tailoring gate enforcement.

Remaining private product gate:
- [ ] five distinct real tailored resumes must be explicitly approved under one current validation context;
- [ ] automatic tailoring remains disabled until the current local gate is 5/5.

The user explicitly authorized later phase development without treating that sequencing exception as completion of the private Phase 4 gate.

Acceptance: `docs/PHASE4_ACCEPTANCE.md`, `docs/PHASE4_CLOSEOUT.md`.

## Phase 5 - Job discovery and matching [x]

Completed: normalized/manual discovery, verified public Greenhouse/Lever/Ashby boards, conservative deduplication, targeting eligibility, source-verified approved-fact matching, explainable ranking, local jobs UI, and current-feed retirement. Employer submission remained disabled throughout Phase 5.

Acceptance: `docs/PHASE5_ACCEPTANCE.md`.

## Phase 6 - Application engine using controlled forms [~]

Implementation in progress:
- [x] 6A transactional application journal, duplicate prevention, single explicit-session worker, and crash recovery;
- [x] 6B localhost-only Playwright controlled-form contract and exact-context approved-answer reuse;
- [x] 6C conservative CAPTCHA/challenge/unknown-question/network/Stop/Close/`UNCERTAIN` behavior;
- [ ] exact-head Windows Phase 6 acceptance and final pull-request-context Phase 0-6 checks.

No real employer submission and no Greenhouse/Lever/Ashby form adapter is part of Phase 6.

Acceptance: `docs/PHASE6_ACCEPTANCE.md`.

## Phase 7 - Supported hiring-platform adapters [ ]

7A Greenhouse, then 7B Lever, then 7C Ashby. Each adapter must pass controlled submissions and read-only live form recognition before the next begins. Unsupported variants are reported, not guessed.

## Phase 8 - End-to-end orchestration [ ]

Connect discovery, matching, tailoring, gates, queues, attention lane, submission, resource pressure, stale-package invalidation, history, and daily confirmed counter. Target 50 confirmed applications without weakening eligibility or factual quality.

## Phase 9 - Packaging and user-authorized pilot [ ]

Clean-machine Windows distribution, setup/upgrade, backup/restore, notices, then separate explicit real-application activation and a measured pilot. Never claim 50/day without evidence.
