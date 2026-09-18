# Phase 9 distribution/recovery acceptance

Initial acceptance: 2026-09-16  
Refreshed against current `main`: 2026-09-18

Status: **accepted for the distribution/recovery half of Phase 9**. The separately authorized pilot implementation is also technically accepted; measured real-world pilot evidence remains pending.

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

This distribution/recovery acceptance itself did **not** authorize or validate real employer filling/submission. The later authorized write-path boundary is documented separately in `PHASE9_PILOT_ACCEPTANCE.md`; CI still does not submit to real employers.

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

## Current-main revalidation

The latest application-hardening merge is PR #17 at main commit `fca1f2e8d249b82fe089c91c5be6a885f0286307` (2026-09-18). Its exact PR head `87f1a31325a564e392dc8881edb51b04dd2e22f0` passed the complete Phase 0 through Phase 9 pull-request matrix. The merge commit has the same file tree as that tested head.

The Phase 9 push run on that merge is `35330432447`. It passed dependency vulnerability audit with no known vulnerabilities, **145 passed, 1 skipped, 2 deselected** in the deterministic regression suite, the focused pilot/hardening checks, backup/restore, inherited Phase 7/8 acceptance, source/frozen/installed desktop and browser smokes, hermetic Chromium packaging, clean install/in-place upgrade, and distribution artifact upload.

## Browser/runtime distribution boundary

The accepted build installs Playwright browser assets using `PLAYWRIGHT_BROWSERS_PATH=0` before PyInstaller analysis. The frozen executable then sets `PLAYWRIGHT_BROWSERS_PATH=0` itself. Acceptance removes the runner browser environment before launching the packaged browser smoke and observes a successful frozen Chromium launch.

Accepted browser baseline:

- Playwright Python `1.63.0`;
- Playwright Chromium revision `1243`;
- Chrome for Testing `153.0.8010.12` Windows x64;
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

## Historical pilot lock and current boundary

At the original 2026-09-16 distribution-only acceptance head, the Phase 9 controller exposed `pilot_authorized = false`, `pilot_activation_available = false`, and `real_employer_submission_enabled = false`; there was no pilot-activation bridge/UI action. That was the deliberate Phase 9A boundary.

A separate user authorization on 2026-09-16 later permitted the measured-pilot implementation. Current `main` therefore contains that write path, but every launch still starts inactive and requires the exact activation phrase, a fresh supported read-only inspection, explicit per-application arming, and the existing eligibility/factual/package/provider/confirmation gates. See `PHASE9_PILOT_ACCEPTANCE.md`.

Phase 4's private five-real-resume review gate remains independently authoritative.

## Development finding repaired before acceptance

The first Phase 9 development run found that the restore mutation guard also blocked the read-only `snapshot()` needed to redraw the UI after staging a restore. The repair permits state snapshots while continuing to reject Start and inherited mutations until restart applies the staged restore. The full gate then passed; no safety/integrity requirement was waived.

## Remaining product boundary

Phase 9 stays `[~]` because the measured real-world pilot has not yet been run. The live write path is already implemented under the later explicit authorization, but every real application remains individually gated and user-armed.

The pilot must continue to preserve eligibility/factual/tailoring gates, provider blockers, explicit confirmation semantics, stale-package checks, single-worker ownership, and terminal `UNCERTAIN` behavior. Throughput must be measured from real confirmed applications; the product must not claim 50/day from controlled fixtures or inference.
