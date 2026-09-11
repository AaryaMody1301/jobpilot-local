# Progress

## Current phase

Phase 2 - resume import and approved fact bank.

Status: **complete pending merge of PR #4** as of 2026-09-11. Phase 0 and Phase 1 are complete and merged to `main`. Phase 3 has not started.

## Verified repository state at phase start

- Re-read `SPEC.md`, `ROADMAP.md`, `DECISIONS.md`, `PROGRESS.md`, and `AGENTS.md` from the merged repository.
- `main` at Phase 2 start: `273b49fa4fe73e3900b11c96e8d965cee769ecaf`, merge of Phase 1 PR #2.
- Original Phase 2 branch: `phase-2-resume-fact-bank`, merged through PR #3.
- Real-resume finalization branch: `phase-2-real-resume-finalization`, PR #4.
- Existing Phase 0/1 lifecycle, SQLite recovery, Windows Job Object, bundled pywebview UI, targeting settings, and packaging boundaries were preserved.

## Phase 2 work completed

- Added migration `003_phase2_resume_fact_bank.sql` for source documents, template maps/regions, resume baselines, facts/fact versions, and fact-bank revision.
- Added immutable master-resume and supporting-document imports. Files are copied byte-for-byte into `%LOCALAPPDATA%\JobPilotLocal`, SHA-256 verified, deduplicated by content, and never written back to the user's original source path.
- A changed master creates a new retained source version instead of mutating/deleting an older master.
- Added conservative candidate mapping for standard LaTeX `\item` bullets. Each region keeps source line range and raw-text SHA. Regions start non-editable; any mapping change invalidates a previous confirmation.
- Added versioned facts with stable fact IDs, source-document ID, source locator, source SHA, candidate/approved/rejected status, correction history, and fact-bank revision.
- Fact approval re-hashes its backing source first and is refused if the app-owned source is missing or modified.
- Added protected non-bullet fact extraction after testing the real template shape. Structured `\role{title}{dates}{employer}{location}` fields, summary/skills/education/project-stack/language/professional-development text are now review candidates even when they are not editable bullets.
- Fixed LaTeX-to-display conversion so layout commands adjacent to factual text cannot swallow labels such as GPA.
- Historical inactive master facts remain retained for provenance but no longer block onboarding readiness for the active resume.
- Added an explicit app-managed Tectonic 0.17.0 installer for Windows x64. The release archive is size/SHA-256 pinned and unpacked only into the app-owned tool directory.
- Added original-template baseline compilation through the app-owned process supervisor. Network-enabled cache population is an explicit action; offline readiness requires a later `--only-cached --untrusted` compile.
- Added pypdf baseline inspection for page count/page geometry plus PDF/text hashes. Extracted PDF text is a validation signal only; it is not the source of factual truth or assumed to preserve reading order.
- Added source metrics for section order, bullet count, document class, local external references, and shell-escape/write18 signal.
- Added Phase 2 UI for master/supporting import, compiler status, explicit cache actions, baseline state, editable-region confirmation, and fact correction/approval.
- File-system selection stays native: the webview bridge accepts paths only from the native file dialog, not arbitrary JavaScript strings.
- Resume onboarding changes are limited to Idle. Tectonic install/compile operations are cancellable on Close through the app-owned process boundary.
- `onboarding_ready` requires verified master integrity, compiled + cached-only verified baseline, confirmed template map, zero active candidate facts, and at least one approved active fact.
- Added controlled LaTeX fixtures, migration regression tests, source tamper tests, fact-history tests, protected-fact tests, active-master scoping tests, controlled UI tests, and real Windows Tectonic acceptance.

## Real resume acceptance

The user supplied the actual LaTeX source in chat on 2026-09-11. It was treated as ephemeral private input and was **not committed to Git**.

Observed structure and layout validation:

- `article` class, A4, 11 pt, 0.6 inch margins;
- self-contained source with no custom local `.cls`, `.sty`, image, bibliography, or extra `.tex` dependency references;
- seven sections;
- three `\role` calls;
- 23 standard `\item` bullet regions;
- two A4 pages in the local validation render;
- no `\write18`/shell-escape request;
- no overfull or underfull box warnings after the final local validation pass.

A sanitized fixture preserving the real template's package/font/layout/custom-command shape was committed instead of personal data. Windows CI used Tectonic 0.17.0 to populate its support cache and then recompiled that sanitized template with `--only-cached --untrusted`, producing two pages successfully.

The real template review exposed and fixed three correctness issues before completion:

1. non-bullet protected facts were absent from the candidate fact bank;
2. adjacent LaTeX layout commands could corrupt display/provenance text;
3. unresolved candidates from inactive historical master versions could block the active resume.

The user explicitly approved **all factual claims in the supplied resume exactly as written** on 2026-09-11. This approval closes the Phase 2 fact-review gate. The personal claim text itself remains private runtime/chat data and is not reproduced in repository records.

## Verification evidence

Original Phase 2 Windows GitHub Actions run `34467708811`, commit `5d1f54c20c4ff224caaa2b5206ffbad0aabf61d4`:

- Python **3.13.15** and all pinned project dependencies installed successfully.
- Matching Playwright Chromium installed successfully.
- Python bytecode compilation and `node --check src/jobpilot/ui/app.js` passed.
- `pytest -m "not external"` -> **67 passed, 1 skipped, 2 deselected**.
- Real Tectonic network→cache→offline acceptance passed.
- Source/package lifecycle self-tests and hidden WebView2 smokes passed.

Real-resume finalization Windows run `34568832244`, head `82713e3393ca29104394059bac222d4bd7c9d065`:

- syntax validation passed;
- `pytest -m "not external"` -> **70 passed, 1 intentional platform-guard skip, 2 external tests deselected**;
- Tectonic 0.17.0 package-cache population passed;
- sanitized real-template shape recompiled successfully with cached resources only and produced **2 pages**;
- source self-test passed;
- source hidden Edge/WebView2 smoke passed;
- PyInstaller 6.22.2 onedir build passed;
- packaged self-test passed;
- packaged hidden Edge/WebView2 smoke passed;
- Phase 0 and Phase 1 regression workflows on the same finalization head also passed.

## Limitations and boundaries

- The approved facts are represented in runtime by explicit fact statuses; the public repository intentionally does not contain the user's personal resume or its factual claims.
- Exact visual comparison of future tailored resumes against the real two-page baseline belongs to Phase 4; Phase 2 establishes the immutable baseline and approval/provenance inputs only.
- GitHub-hosted Windows acceptance uses Windows Server 2025 rather than an end-user Windows 10/11 installation. Clean-machine Windows 10/11 distribution testing remains Phase 9.
- No AI inference, job discovery, resume rewriting, browser form filling, or employer submission is enabled in Phase 2.

## Exact next step

Merge PR #4. After the finalization changes are present on `main`, Phase 3 - Local AI and resource manager - is the first incomplete approved phase. Start it only from that merged `main` state. Phase 3 must implement hardware/resource detection, approved app-managed llama.cpp/model installation, checksum/license metadata, one-inference-at-a-time execution, resource-pressure handling, quality/structured-output evaluation, replacement review gating, and safe deletion/rollback without starting Phase 4.
