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

The user explicitly authorized later phase development without treating that sequencing exception as completion of the private Phase 4 gate. The post-Phase-9 hardening matrix re-ran and passed the real local Phase 4 tailoring acceptance at hardening head `75205774ad8cf444fe9081073b59c3e951849a50`, run `35077829627`; this technical acceptance does not substitute for the five human approvals.

Acceptance: `docs/PHASE4_ACCEPTANCE.md`, `docs/PHASE4_CLOSEOUT.md`.

## Phase 5 - Job discovery and matching [x]

Completed: normalized/manual discovery, verified public Greenhouse/Lever/Ashby boards, conservative deduplication, targeting eligibility, source-verified approved-fact matching, explainable ranking, local jobs UI, and current-feed retirement. Employer submission remained disabled throughout Phase 5.

Acceptance: `docs/PHASE5_ACCEPTANCE.md`.

## Phase 6 - Application engine using controlled forms [x]

Completed:
- [x] 6A transactional application journal, duplicate prevention, single explicit-session worker, and crash recovery;
- [x] 6B localhost-only Playwright controlled-form contract and exact-context approved-answer reuse;
- [x] 6C conservative CAPTCHA/challenge/unknown-question/network/Stop/Close/`UNCERTAIN` behavior;
- [x] exact-head Windows Phase 6 acceptance at code head `8d1cb12d1a5ff096ecfc8b8df470777ee3b99c43`, run `34743335410`.

No real employer submission and no Greenhouse/Lever/Ashby employer-form adapter is part of Phase 6.

Acceptance: `docs/PHASE6_ACCEPTANCE.md`.

## Phase 7 - Supported hiring-platform adapters [x]

Completed sequentially:
- [x] 7A Greenhouse hosted-form adapter: controlled loopback submission/confirmation and current GitLab form recognition passed before Lever work began;
- [x] 7B Lever hosted-form adapter: controlled loopback submission/confirmation and current Nium form recognition passed before Ashby work began;
- [x] 7C Ashby hosted-form adapter: controlled loopback submission/confirmation and current Ashby form recognition passed;
- [x] unsupported/challenge variants are reported rather than guessed;
- [x] live employer pages remain read-only and adapter write methods fail closed outside loopback in the Phase 7 boundary;
- [x] exact-head Windows Phase 7 acceptance at code head `3a95d0a32755c94b21ec77c209749986718167a6`, run `34745312735`.

Acceptance: `docs/PHASE7_ACCEPTANCE.md`.

## Phase 8 - End-to-end orchestration [x]

Completed:
- [x] discovery/matching outcomes are journaled into the existing application state machine;
- [x] eligibility unknowns use an explicit attention lane and cannot be guessed;
- [x] eligible work reuses the existing evidence-backed tailoring service and the Phase 4 human/automatic-tailoring gates;
- [x] immutable application packages bind the discovered job snapshot, tailoring audit evidence, current approved-answer fingerprint and submission attempt;
- [x] prepared/queued packages are invalidated before submit when their job, resume/context evidence or approved answers become stale;
- [x] the existing single application worker remains the only component allowed to cross the controlled submit boundary;
- [x] provider live-form inspection is read-only and Phase 8 exposes no real-employer fill/submit activation;
- [x] orchestration respects resource pressure and explicit Start/Pause/Stop/Close lifecycle boundaries;
- [x] attention/history and a local-calendar-day `50 confirmed real applications` target are visible; controlled confirmations are excluded and the target never weakens eligibility/factual/review gates;
- [x] exact-head Windows Phase 8 acceptance at code head `5b2a10827a2b81533a2017dd9828395ded91a383`, run `34946104772`.

Real employer submission remained disabled throughout Phase 8.

Acceptance: `docs/PHASE8_ACCEPTANCE.md`.

## Phase 9 - Packaging and user-authorized pilot [~]

Distribution/recovery completed:
- [x] verified Windows 10/11 x64 onedir distribution and SHA-256 release metadata;
- [x] per-user setup and rollback-safe in-place program upgrade while preserving the separate local data root;
- [x] hermetic Playwright Chromium bundling and frozen-browser smoke without a global browser cache;
- [x] WebView2 Evergreen Runtime detection and official Microsoft bootstrap path when absent;
- [x] portable local backup/restore with integrity checks, restart-bound application and pre-restore safety backup;
- [x] exact browser/WebView/legal notices in the distribution;
- [x] exact-head Windows distribution/recovery acceptance at code head `b5ebda60793e3f61a25885b4370ebf5242d2e705`, run `35056956675`.

Measured-pilot activation path:
- [x] received the later separate user authorization for the real-application pilot implementation on 2026-09-16;
- [x] implemented the minimum real-employer hosted-form write path without weakening eligibility, package freshness, approved-answer, provider-blocker, single-worker, confirmation or `UNCERTAIN` boundaries;
- [x] every launch starts inactive, requires an exact local activation phrase, a fresh read-only inspection and explicit per-application arming, with at most five armed applications per launch;
- [x] restart/deactivation/restore forces queued real work back to `PREPARED`, clears stale live inspection data and requires fresh inspection plus re-arming;
- [x] live resume upload resolves the persisted managed `pdf_relpath` and re-verifies its SHA-256 immediately before browser upload;
- [x] post-submit success requires newly observed confirmation evidence relative to a captured pre-submit baseline, so static success-like text cannot by itself produce `CONFIRMED`;
- [x] dependency/package hardening is current for the accepted release baseline: Playwright 1.63.0, pypdf 6.18.1, PyInstaller 6.22.3 and pinned `pip-audit` 2.10.1;
- [x] exact-head post-audit hardening matrix passed Phase 0 through Phase 9 at code head `75205774ad8cf444fe9081073b59c3e951849a50`; Phase 9 run `35077829573`, Phase 4 run `35077829627`;
- [ ] run the measured real-world pilot from current local/private candidate data and record actual confirmed-application throughput/quality evidence;
- [ ] never claim 50/day without measured evidence.

The accepted technical pilot implementation and hardening acceptance did not fill or submit a real employer form. CI live-provider checks remain read-only; only controlled loopback fixtures perform writes. Phase 4's private five-real-resume gate remains independently authoritative.

Acceptance: `docs/PHASE9_DISTRIBUTION_ACCEPTANCE.md`, `docs/PHASE9_PILOT_ACCEPTANCE.md`. Phase 9 remains `[~]` until measured real-pilot evidence is recorded.
