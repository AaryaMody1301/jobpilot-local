# Phase 9 distribution/recovery acceptance

Date: 2026-09-16

Status: **accepted for the distribution/recovery half of Phase 9 only**. The real-application pilot is a separate explicit-authorization boundary and remains unstarted.

## Accepted scope

This acceptance covers:

- a Windows 10/11 x64 per-user JobPilot distribution;
- hermetic Playwright Chromium in the frozen application;
- WebView2 Evergreen Runtime prerequisite handling;
- verified release contents and SHA-256 archive metadata;
- clean setup and rollback-safe in-place program upgrade;
- portable local backup/restore and pre-restore safety backup;
- legal/browser/runtime notices;
- source, frozen and installed-app desktop smoke;
- preservation of all Phase 7/8 live-write safety boundaries.

It does **not** authorize, implement or validate real employer filling/submission.

## Technical head and Windows gate

Accepted technical head: `b5ebda60793e3f61a25885b4370ebf5242d2e705`

Windows workflow: `35056956675` (`Phase 9 distribution acceptance`)

The exact-head workflow passed:

- Python and bundled JavaScript syntax validation;
- the complete non-external regression suite: **131 passed, 1 skipped, 2 deselected**;
- Phase 9 backup/restore and pilot-lock acceptance;
- inherited Phase 8 end-to-end controlled orchestration acceptance;
- inherited Phase 7 Greenhouse/Lever/Ashby controlled-submit and live-read-only provider acceptance;
- source self-test and hidden WebView2/pywebview smoke;
- PyInstaller onedir build after hermetic Playwright browser installation;
- frozen self-test, bundled-browser smoke and hidden-window smoke with the global Playwright browser environment removed;
- verified Windows distribution creation;
- clean per-user install;
- second-pass in-place upgrade with `%LOCALAPPDATA%\JobPilotLocal` sentinel preservation;
- installed application self-test, bundled-browser smoke and hidden-window smoke;
- Windows distribution artifact and SHA-256 sidecar upload.

## Browser/runtime distribution boundary

The accepted build installs Playwright browser assets using `PLAYWRIGHT_BROWSERS_PATH=0` before PyInstaller analysis. The frozen executable then sets `PLAYWRIGHT_BROWSERS_PATH=0` itself. Acceptance removes the runner browser environment before launching the packaged browser smoke and observes a successful frozen Chromium launch.

Accepted browser baseline:

- Playwright Python `1.62.0`;
- Playwright Chromium revision `1234`;
- Chrome for Testing `151.0.7922.34` Windows x64;
- matching Playwright-installed headless shell, FFmpeg and support binaries.

The desktop shell still uses pywebview's Edge Chromium backend. Setup checks for the Evergreen Microsoft Edge WebView2 Runtime using the documented 64-bit registration. If absent, it retrieves Microsoft's official Evergreen Bootstrapper, verifies a valid Microsoft Authenticode signature, invokes the documented silent install, and verifies availability before continuing.

`packaging/BROWSER_NOTICES.md` records the exact distribution baseline and upstream notice boundary. The distribution also includes the project license and `THIRD_PARTY_NOTICES.md`.

## Setup and upgrade boundary

The release archive contains a per-user `setup.cmd` / `install.ps1` path. The installer:

1. validates the distribution manifest format and exact file set;
2. verifies every declared file byte length and SHA-256;
3. ensures WebView2 is available;
4. stages program files next to the intended install root;
5. moves an existing install aside for upgrade;
6. atomically moves the staged program into the install root;
7. restores the prior program directory if replacement fails;
8. deletes the prior program directory only after successful replacement;
9. optionally writes a Start Menu shortcut.

Default program root: `%LOCALAPPDATA%\Programs\JobPilotLocal`.

Private application state remains under `%LOCALAPPDATA%\JobPilotLocal`. Acceptance performed an install, wrote a sentinel under the redirected data root, ran the installer again as an upgrade, and verified the sentinel remained unchanged before running the installed executable checks.

## Portable backup/restore boundary

Portable backups include only:

- `db/` — SQLite application state;
- `documents/` — imported/private document sources;
- `artifacts/` — generated resume/application evidence and artifacts.

They intentionally exclude:

- model weights;
- app-managed tools/runtimes;
- Playwright browsers;
- browser profile/session data;
- Tectonic/cache data;
- runtime coordination files;
- logs.

Backup creation uses SQLite's backup API, rejects symbolic links, and records byte length/SHA-256 for every portable file plus applied schema migrations.

Restore validates archive paths, file-count/expanded-size bounds, the manifest, exact member list, SHA-256/size values, allowed top-level roots, SQLite `quick_check`, and migration compatibility. A valid archive is staged under the managed runtime root. After staging, JobPilot remains readable but blocks new mutation/session work until restart.

On next launch, before opening the database, JobPilot revalidates the staged payload, creates a `pre-restore-*.zip` safety backup of current portable data, swaps only `db`, `documents`, and `artifacts`, and preserves all machine-specific roots. The normal migration path then upgrades an older compatible restored database if necessary.

Acceptance proved backup -> mutation -> staged restore -> restart/apply restored the original database/document state while preserving a machine-specific model sentinel and creating the safety backup.

## Live-provider safety evidence

The inherited provider acceptance remained conservative on the accepted Phase 9A head:

- Greenhouse/GitLab: 29 visible fields, CAPTCHA blocker, live write guard active;
- Lever/Nium: 11 visible fields, CAPTCHA blocker, live write guard active;
- Ashby/Ashby: 26 visible fields, CAPTCHA blocker, live write guard active.

Controlled loopback confirmations passed for all three adapters. Current live examples remained unsupported for automatic submission. No real employer form was filled or submitted.

## Pilot lock

The Phase 9 controller exposes:

- `pilot_authorized = false`;
- `pilot_activation_available = false`;
- `real_employer_submission_enabled = false`.

The Phase 9 bridge/UI contains no pilot-activation action. Existing provider live-write guards and the controlled submission worker therefore remain the executable boundary, not just a UI convention.

Phase 4's private five-real-resume review gate also remains independently authoritative.

## Development finding repaired before acceptance

The first Phase 9 development run found that the restore mutation guard also blocked the read-only `snapshot()` needed to redraw the UI after staging a restore. The repair permits state snapshots while continuing to reject Start and inherited mutations until restart applies the staged restore. The full gate then passed; no safety/integrity requirement was waived.

## Next boundary

Phase 9 stays `[~]` after this acceptance. A later separate explicit user instruction must authorize the real-application pilot before a live employer write path is implemented or enabled.

Any pilot must preserve existing eligibility/factual/tailoring gates, provider blockers, explicit confirmation semantics, stale-package checks, single-worker ownership, and terminal `UNCERTAIN` behavior. Throughput must be measured from real confirmed applications; the product must not claim 50/day from controlled fixtures or inference.
