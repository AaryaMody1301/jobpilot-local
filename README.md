# jobpilot-local

`jobpilot-local` is a local-first Windows desktop assistant for job discovery, evidence-backed resume tailoring, and user-authorized application automation.

## Status

- Phases 0-3 are complete.
- Phase 4 tailoring is technically implemented and merged. Its private five-real-resume review gate remains independently authoritative until `--phase4-gate-report` succeeds for the current local context.
- Phase 5 job discovery and matching is complete.
- Phase 6 controlled application-engine work is complete and accepted.
- Phase 7 Greenhouse, Lever and Ashby hosted-form adapters are complete and accepted.
- Phase 8 end-to-end orchestration is complete and accepted.
- Phase 9 distribution/recovery is implemented and accepted. **Phase 9 is still in progress because the separately authorized real-application pilot has not been activated or run.**

## Phase 9 distribution and recovery

The current Phase 9 build adds a clean Windows distribution boundary without enabling real employer writes:

- Windows 10/11 x64 onedir package with a per-user `setup.cmd` installer;
- rollback-safe in-place program upgrades while `%LOCALAPPDATA%\JobPilotLocal` remains separate and preserved;
- Playwright Chromium bundled hermetically into the frozen application, with packaged browser smoke independent of a global Playwright cache;
- Microsoft Edge WebView2 Evergreen Runtime detection during setup and official Microsoft bootstrap when it is absent;
- release integrity manifest with per-file SHA-256/size plus a ZIP SHA-256 sidecar;
- portable local backup/restore for the SQLite database, private documents and generated/application artifacts;
- restart-bound restore with archive/path/hash/schema/database validation and an automatic pre-restore safety backup;
- machine-specific models, tools, browser/profile data, caches, runtime files and logs remain outside portable backups;
- bundled legal/browser/WebView notices;
- local Phase 9 UI for backup/restore and distribution status.

There is deliberately no real-pilot activation method or UI control in this build. Live Greenhouse/Lever/Ashby pages remain read-only, provider write guards remain intact, and `UNCERTAIN` outcomes are still never automatically retried.

## Install a Phase 9 distribution artifact

1. Extract `JobPilotLocal-<version>-win-x64.zip`.
2. Close any running JobPilot Local process.
3. Run `setup.cmd` from the extracted directory.
4. Launch **JobPilot Local** from the Start Menu shortcut.

The installer is per-user by default and writes program files under `%LOCALAPPDATA%\Programs\JobPilotLocal`. Private JobPilot state remains under `%LOCALAPPDATA%\JobPilotLocal`. Running a newer package's `setup.cmd` upgrades program files in place without deleting that data root.

The setup checks for WebView2. If the Evergreen Runtime is missing, it retrieves Microsoft's official bootstrapper, verifies a valid Microsoft Authenticode signature, silently installs the Runtime, and verifies availability before continuing.

## Backup and restore

Use **Local data -> Portable backup** in the desktop app while JobPilot is Idle.

A portable backup includes:

- the SQLite state database;
- imported/private source documents;
- generated resume and application artifacts.

It excludes machine-specific or reproducible state such as model weights, downloaded tools, Playwright/browser profile state, caches, runtime files and logs.

Restore validates the archive and database first, stages the payload, then requires an application restart. On the next launch JobPilot makes a pre-restore safety backup and swaps only the portable roots before opening the restored database. Machine-specific state is preserved.

Portable backup ZIPs contain private candidate data and should be stored with the same care as the original resume/application files.

## Safety and privacy

- Windows 10/11 x64 only for v1.
- No cloud AI, hosted database, telemetry, paid proxy/API, CAPTCHA solving, remote UI scripts, or cloud sign-in.
- Private resume sources, approved facts, generated resumes, local databases, browser state, and model weights stay outside Git under the app-managed local data root.
- JDs, ATS payloads, employer pages, and model output are untrusted data.
- Automatic resume tailoring still requires the current five-distinct-resume Phase 4 gate.
- Live employer pages remain read-only in the current Phase 9 distribution/recovery build.
- `UNCERTAIN` submission outcomes are never automatically retried.
- A later separate explicit user authorization is required before any real-application pilot is implemented/enabled.
- The visible 50/day objective is a target, not an established capability; no throughput claim is made without measured real-pilot evidence.

Check the private Phase 4 gate without exposing resume/JD/fact content:

```powershell
python -m jobpilot.app.main --phase4-gate-report
```

## Run from source

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
$env:PLAYWRIGHT_BROWSERS_PATH="$env:LOCALAPPDATA\JobPilotLocal\browsers"
python -m playwright install chromium
python -m jobpilot.app.main
```

## Phase 9 distribution acceptance

Windows run `35056956675` at technical head `b5ebda60793e3f61a25885b4370ebf5242d2e705` passed the distribution/recovery path:

- Python and bundled JavaScript syntax validation;
- complete non-external regression suite: 131 passed, 1 skipped, 2 deselected;
- backup/restore roundtrip with pre-restore safety backup, schema/integrity checks and machine-specific-state preservation;
- explicit pilot-lock verification;
- inherited Phase 8 orchestration and Phase 7 provider boundaries;
- source Phase 9 self-test and hidden WebView2/pywebview smoke;
- PyInstaller build with hermetic Playwright Chromium;
- packaged browser launch with the global browser environment removed;
- verified distribution archive build;
- clean install and in-place upgrade with private local-data preservation;
- installed application self-test, bundled-browser smoke and hidden-window smoke;
- distribution artifact and SHA-256 sidecar upload.

No real employer form was filled or submitted. See `docs/PHASE9_DISTRIBUTION_ACCEPTANCE.md` for the exact boundary and evidence.

## Local data

Runtime data lives under `%LOCALAPPDATA%\JobPilotLocal`. Private candidate data, browser state, and model weights must never be committed.

## Project records

- `SPEC.md` - v1 product requirements.
- `ROADMAP.md` - phase order and current status.
- `DECISIONS.md` - engineering decisions.
- `PROGRESS.md` - current handoff and exact verification evidence.
- `AGENTS.md` - repository implementation rules, including the compact Ponytail-style code/check policy.
- `docs/PHASE9_DISTRIBUTION_ACCEPTANCE.md` - Phase 9 distribution/recovery boundary and evidence.
