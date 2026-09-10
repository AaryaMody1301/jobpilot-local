# Progress

## Current phase

Phase 0 - feasibility and architecture.

Status: implementation in progress on 2026-09-10. Local non-external checks pass; target-Windows CI evidence is still required before this phase can be marked complete.

## Verified repository state at phase start

- GitHub repository: `AaryaMody1301/jobpilot-local`.
- Default branch: `main`.
- Repository was empty before Phase 0.
- No repository-local `AGENTS.md` or inherited project files existed.

## Completed work

- User approved Windows 10/11 x64 v1 target, Stop semantics, starter ATS board registry plus user additions, and MIT licensing.
- Official documentation/release research performed for Python, pywebview, Playwright, Windows Job Objects, Tectonic, llama.cpp, Greenhouse, Lever, and Ashby.
- Defined session and application state machines, including terminal `UNCERTAIN` submission outcomes.
- Added SQLite WAL/migration/recovery primitives that requeue safe pre-submit work and classify interrupted post-submit attempts as `UNCERTAIN`.
- Added app-owned path guards for future destructive model cleanup.
- Added cross-platform process-supervisor interface and Windows Job Object implementation that creates the child suspended, assigns it to the owned Job Object, then resumes it.
- Added Tectonic command policy (`--only-cached`, `--untrusted`) and explicit cache-population opt-in.
- Added localhost-only llama.cpp request builder plus strict local structured-response validation.
- Added read-only controlled Playwright form inspection and blocker recognition; it contains no submit action.
- Added Phase 0 Windows GitHub Actions workflow and PyInstaller desktop self-test probe.

## Verification evidence

Local host verification on 2026-09-10:

- `PYTHONPATH=src pytest -q -m 'not external'` -> **25 passed, 3 skipped, 2 deselected**.
- Skips are target-dependent: two controlled Playwright tests because the local Chromium binary is absent, and one Windows Job Object test because this host is not Windows.
- `PYTHONPATH=src pytest -q -m external` -> **2 skipped, 28 deselected** because no explicitly installed Tectonic executable or approved llama.cpp model/server was supplied.
- A dependency-install attempt in this container could not reach PyPI, so pywebview/PyInstaller packaging cannot be honestly verified on this host.
- Windows CI is configured to install the pinned project dependencies and Playwright Chromium, run the non-external suite, package the pywebview probe with PyInstaller, and execute its self-test. That workflow result is required before Phase 0 completion.

## Known constraints

- This development environment is not the target Windows desktop. Windows Job Object and pywebview/WebView2 behavior must be verified by the Windows CI job and later on a real Windows 10/11 desktop.
- No user LaTeX resume has been provided; template compatibility belongs to Phase 2 and cannot be claimed yet.
- No model download has been approved or performed. Phase 0 validates the llama.cpp request/response trust boundary, not model quality. Hardware-specific model selection remains Phase 3.
- Tectonic 0.17.0 is recorded as the candidate Windows binary, but the optional external compilation probe is not a substitute for testing the user's actual template in Phase 2.
- No real employer application will be submitted during development.

## Exact next step

Publish the Phase 0 branch, collect the Windows workflow result, fix any target-platform failures, update this record with the evidence, then stop at the Phase 0 boundary for review.
