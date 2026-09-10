# Progress

## Current phase

Phase 1 - runnable desktop foundation.

Status: implementation in progress on 2026-09-10. Phase 0 is complete and was merged to `main` through PR #1.

## Verified repository state at phase start

- Read `SPEC.md`, `ROADMAP.md`, `DECISIONS.md`, `PROGRESS.md`, and `AGENTS.md` from the merged repository.
- `main` commit at Phase 1 start: `e973e9bf3d9067b62d0ad2f4ab6be6b383be5042` (merge of Phase 0 PR #1).
- The corrected Phase 0 Windows run `34450358935` completed successfully.
- Windows evidence: **28 passed, 2 deselected**; pinned dependencies and Playwright Chromium installed; PyInstaller 6.22.2 onedir probe built; packaged self-test exited successfully.
- Phase 0 external Tectonic/model probes remain opt-in because no user resume/cache or approved local model exists yet; that does not block the architecture phase.

## Phase 1 work implemented

- Added migration `002_phase1_foundation.sql` for local JSON settings, activity history, and sample-work metadata.
- Extended `ManagedPaths` to create database, document, artifact, model, browser, Tectonic cache, backup, cache, runtime, and log roots under the app-owned data directory.
- Serialized SQLite access for pywebview/background threads while preserving WAL, FULL synchronous mode, foreign keys, busy timeout, migrations, and crash classification.
- Added strict editable targeting settings with the agreed defaults and local JSON persistence.
- Added a sample-only lifecycle worker that is created only by Start, schedules no external work, obeys Pause, and is joined/cancelled by Stop or Close.
- Added thread-safe `ApplicationController` lifecycle and narrow `DesktopBridge` API.
- Added local bundled HTML/CSS/JavaScript dashboard with navigation, Start/Pause/Stop, sample queue/activity, targeting settings, and local-data view. Later-phase features are explicitly shown as unavailable rather than simulated.
- Added source and packaged self-tests plus hidden Edge/WebView2 smoke mode.
- Added Phase 1 Windows workflow and PyInstaller onedir specification.

## Verification evidence so far

Local host:

- `PYTHONPATH=src pytest -q -m 'not external'` -> **46 passed, 4 skipped, 2 deselected**.
- Skips are environmental: three Playwright tests because the managed Chromium binary is not installed in this container and one Windows Job Object test because this host is not Windows.
- `python -m jobpilot.app.main --self-test` cannot run on this host because pywebview is not installed and this container cannot reach PyPI; the Windows workflow installs the exact pinned dependency and must pass the source/package self-tests.
- This environment also blocks browser navigation to local `file://` and loopback URLs by administrator policy, so interactive DOM smoke evidence must come from the Windows workflow.

## Known boundaries

- Phase 1 contains no job discovery, AI inference, resume rewriting, application form filling, or employer submission.
- The displayed confirmed-application count is zero by design; the sample queue is never reported as applications.
- Resume/template compatibility is not evaluated until Phase 2 and requires the user's LaTeX resume source.

## Exact next step

Publish the Phase 1 branch, run its Windows acceptance workflow, fix any failures, record the final evidence, and stop at the Phase 1 boundary. Do not start Phase 2 until requested.
