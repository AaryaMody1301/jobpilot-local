# Progress

## Current phase

Phase 1 - runnable desktop foundation.

Status: **complete** on 2026-09-10. Phase 0 is complete and was merged to `main` through PR #1. Phase 1 is implemented and verified on `phase-1-desktop-foundation`; Phase 2 has not started.

## Verified repository state at phase start

- Read `SPEC.md`, `ROADMAP.md`, `DECISIONS.md`, `PROGRESS.md`, and `AGENTS.md` from the merged repository.
- `main` commit at Phase 1 start: `e973e9bf3d9067b62d0ad2f4ab6be6b383be5042` (merge of Phase 0 PR #1).
- The corrected Phase 0 Windows run `34450358935` completed successfully.
- Phase 0 Windows evidence: **28 passed, 2 deselected**; pinned dependencies and Playwright Chromium installed; PyInstaller 6.22.2 onedir probe built; packaged self-test exited successfully.

## Phase 1 work completed

- Added migration `002_phase1_foundation.sql` for local JSON settings, activity history, and sample-work metadata.
- Extended `ManagedPaths` to create database, document, artifact, model, browser, Tectonic cache, backup, cache, runtime, and log roots under the app-owned data directory.
- Serialized SQLite access for pywebview/background threads while preserving WAL, FULL synchronous mode, foreign keys, busy timeout, migrations, and crash classification.
- Added strict editable targeting settings with every agreed default and local JSON persistence.
- Added a sample-only lifecycle worker that is created only by Start, schedules no external work, obeys Pause, and is joined/cancelled by Stop or Close.
- Added thread-safe `ApplicationController` lifecycle and narrow `DesktopBridge` API.
- Added local bundled HTML/CSS/JavaScript dashboard with navigation, Start/Pause/Stop, sample queue/activity, complete targeting settings, and local-data view. Later-phase features are explicitly unavailable rather than simulated.
- Added Phase 0-to-Phase 1 migration coverage, crash/reopen coverage, no-worker-after-close coverage, controlled UI bridge coverage, source/package self-tests, and source/package hidden-window WebView2 smokes.
- Added Phase 1 Windows workflow and PyInstaller onedir specification.

## Verification evidence

Local host:

- `PYTHONPATH=src pytest -q -m 'not external'` -> **46 passed, 4 skipped, 2 deselected**.
- Local skips were environmental: three Playwright checks because the managed Chromium binary is absent in this container and one Windows Job Object check because this host is not Windows.
- Python bytecode compilation, JavaScript syntax validation, and example targeting JSON validation passed locally.

Windows GitHub Actions run `34455123604`, commit `a30df97856d89dd8f9b969eca478d8afa52457bc`:

- Python **3.13.15** installed successfully.
- Pinned direct dependencies installed: Playwright 1.62.0, psutil 7.2.2, pypdf 6.18.0, pywebview 6.2.1; development pins PyInstaller 6.22.2 and pytest 9.1.1 also installed.
- Matching Playwright Chromium revision installed successfully.
- `pytest -m "not external"` -> **50 passed, 2 deselected in 8.70s**.
- Source `--self-test` passed: launch idle, app-owned roots created, pywebview imported, reopen did not resume, settings persisted, worker stopped.
- Source hidden Edge/WebView2 smoke passed: bundled document loaded and `window.pywebview.api` bridge became available.
- PyInstaller 6.22.2 onedir build completed successfully.
- Packaged `--self-test` passed with the same lifecycle/persistence assertions.
- Packaged hidden Edge/WebView2 smoke passed with the local UI and JS bridge.
- The workflow completed successfully with no real employer or model activity.

## Limitations and boundaries

- GitHub's hosted Windows acceptance runner was Windows Server 2025, not an end-user Windows 10/11 installation. Clean-machine Windows 10/11 distribution testing remains part of Phase 9; Phase 1 nevertheless exercises the Windows x64 pywebview/WebView2, filesystem, SQLite, Playwright, Job Object, and PyInstaller paths.
- Phase 1 contains no job discovery, AI inference, resume rewriting, application form filling, or employer submission.
- The displayed confirmed-application count is zero by design; the sample queue is never reported as applications.
- No cloud inference was used and no employer application was sent.
- Resume/template compatibility is not evaluated until Phase 2 and requires the user's LaTeX resume source.

## Exact next step

Stop at the Phase 1 boundary. When Phase 2 is requested, first re-read the persistent records and inspect `main`, then begin Phase 2A by importing the user's actual LaTeX resume immutably, establishing its Tectonic baseline/page/layout data, and determining the editable template mapping. Do not enable automatic rewriting or submissions.
