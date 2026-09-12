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

The user explicitly authorized Phase 5 development on 2026-09-12 without treating that sequencing exception as completion of the private Phase 4 gate.

Acceptance: `docs/PHASE4_ACCEPTANCE.md`, `docs/PHASE4_CLOSEOUT.md`.

## Phase 5 - Job discovery and matching [x]

Completed:
- [x] normalization and manual job import;
- [x] verified Greenhouse/Lever/Ashby starter registry and explicit public discovery;
- [x] live validation before persisting user-added board identifiers;
- [x] conservative source/content deduplication;
- [x] hard eligibility for targeting constraints and Brentwood exclusion;
- [x] unknown mandatory conditions routed to review instead of guessed;
- [x] required/preferred requirement extraction and source-verified approved-fact matching;
- [x] explainable ranking separated from eligibility and never labelled an ATS score/interview probability;
- [x] bundled local jobs UI with Python-owned network boundary;
- [x] employer form filling and submission remain disabled;
- [x] focused Windows acceptance run `34686987747` passed syntax, full non-external regression, three live public ATS contracts, source/package smoke, and PyInstaller build.

Acceptance: `docs/PHASE5_ACCEPTANCE.md`.

## Phase 6 - Application engine using controlled forms [ ]

6A transactional application journal/single worker. 6B controlled Playwright fixture engine and approved answers. 6C CAPTCHA/challenge/unknown-question/duplicate/crash/network/sleep/close recovery. No real employers.

## Phase 7 - Supported hiring-platform adapters [ ]

7A Greenhouse, then 7B Lever, then 7C Ashby. Each adapter must pass controlled submissions and read-only live form recognition before the next begins. Unsupported variants are reported, not guessed.

## Phase 8 - End-to-end orchestration [ ]

Connect discovery, matching, tailoring, gates, queues, attention lane, submission, resource pressure, stale-package invalidation, history, and daily confirmed counter. Target 50 confirmed applications without weakening eligibility or factual quality.

## Phase 9 - Packaging and user-authorized pilot [ ]

Clean-machine Windows distribution, setup/upgrade, backup/restore, notices, then separate explicit real-application activation and a measured pilot. Never claim 50/day without evidence.
