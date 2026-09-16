# jobpilot-local

`jobpilot-local` is a local-first Windows desktop assistant for job discovery, evidence-backed resume tailoring, and user-authorized application automation.

## Status

- Phases 0-3 are complete.
- Phase 4 tailoring is technically implemented and merged. Its private five-real-resume review gate remains independently authoritative until `--phase4-gate-report` succeeds for the current local context.
- Phase 5 job discovery and matching is complete.
- Phase 6 controlled application-engine work is complete and accepted.
- Phase 7 Greenhouse, Lever and Ashby hosted-form adapters are complete and accepted.
- Phase 8 end-to-end orchestration is complete and accepted.
- Phase 9 distribution/recovery is implemented and accepted.
- The separately authorized Phase 9 measured-pilot write path is technically implemented and accepted. **Phase 9 remains in progress because a measured real-world pilot has not yet been run and no 50/day capability claim has been established.**

## Phase 9 distribution and recovery

The current Phase 9 build includes:

- Windows 10/11 x64 onedir package with a per-user `setup.cmd` installer;
- rollback-safe in-place program upgrades while `%LOCALAPPDATA%\JobPilotLocal` remains separate and preserved;
- Playwright Chromium bundled hermetically into the frozen application, with packaged browser smoke independent of a global Playwright cache;
- Microsoft Edge WebView2 Evergreen Runtime detection during setup and official Microsoft bootstrap when it is absent;
- release integrity manifest with per-file SHA-256/size plus a ZIP SHA-256 sidecar;
- portable local backup/restore for the SQLite database, private documents and generated/application artifacts;
- restart-bound restore with archive/path/hash/schema/database validation and an automatic pre-restore safety backup;
- machine-specific models, tools, browser/profile data, caches, runtime files and logs outside portable backups;
- bundled legal/browser/WebView notices;
- local Phase 9 distribution/recovery and measured-pilot controls.

## Measured real-application pilot

The user-authorized pilot is intentionally explicit and small. JobPilot does **not** start a real-employer write lane automatically.

For an eligible prepared application:

1. launch JobPilot; the real-employer lane starts inactive;
2. keep JobPilot Idle and inspect the prepared application's live form read-only;
3. the form must be a supported Greenhouse, Lever or Ashby HTTPS hosted application with no CAPTCHA/challenge, login/verification, payment, assessment, unsupported required field or ambiguous submit control;
4. type the exact local activation phrase `ENABLE MEASURED REAL APPLICATION PILOT`;
5. explicitly arm that one prepared application in the Attention lane;
6. press Start; the existing single application worker is the only worker that may claim and submit it;
7. if a mandatory live question has no exact-context approved answer, JobPilot returns the application to human review instead of guessing;
8. immediately before filling/submitting, JobPilot rechecks package freshness and re-inspects the form;
9. after the submit click, only explicit positive employer confirmation counts as `CONFIRMED`; an ambiguous outcome becomes terminal `UNCERTAIN` and is not automatically retried.

At most five distinct real applications may be armed in one process launch. Activation is memory-only. Restart, deactivation, or restore staging returns queued never-submitted live work to `PREPARED`, clears its previous live inspection, and requires a fresh inspection plus explicit re-arming.

The current tailored PDF is uploaded only to a recognized resume/CV upload. JobPilot does not invent answers or guess another required file upload.

Public Greenhouse, Lever and Ashby programmatic submission APIs are employer integrations requiring employer-side credentials/permissions. JobPilot therefore uses the supported hosted applicant forms for this candidate-side pilot rather than asking the candidate for an employer API key.

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
- The measured live lane is off by default on every launch and requires local activation plus per-application arming.
- CAPTCHA/challenge, login/verification, payment, assessment, stale-package and unsupported-form conditions remain fail-closed.
- `UNCERTAIN` submission outcomes are never automatically retried.
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

## Phase 9 acceptance

Distribution/recovery acceptance is recorded at technical head `b5ebda60793e3f61a25885b4370ebf5242d2e705`, Windows run `35056956675`.

Measured-pilot activation implementation acceptance is recorded at technical head `06a2f31d47dc3dbe09bcf0eda3fd34bf0278d0e5`, Windows run `35072562186`.

The pilot technical run passed:

- Python and bundled JavaScript syntax validation;
- complete non-external regression suite: **135 passed, 1 skipped, 2 deselected**;
- four focused pilot safety tests;
- backup/restore with the authorized pilot inactive by default after launch/restore;
- inherited Phase 8 orchestration and Phase 7 provider boundaries;
- source Phase 9 self-test and hidden WebView2/pywebview pilot UI smoke;
- PyInstaller build with hermetic Playwright Chromium;
- packaged browser launch with the global browser environment removed;
- verified distribution archive build;
- clean install and in-place upgrade with private local-data preservation;
- installed application self-test, bundled-browser smoke and hidden-window smoke;
- distribution artifact and SHA-256 sidecar upload.

The accepted technical run did **not** fill or submit a real employer form. Its live Greenhouse/Lever/Ashby checks remained read-only, and the current examples all exposed CAPTCHA integration. See `docs/PHASE9_DISTRIBUTION_ACCEPTANCE.md` and `docs/PHASE9_PILOT_ACCEPTANCE.md` for exact boundaries and evidence.

## Local data

Runtime data lives under `%LOCALAPPDATA%\JobPilotLocal`. Private candidate data, browser state, and model weights must never be committed.

## Project records

- `SPEC.md` - v1 product requirements.
- `ROADMAP.md` - phase order and current status.
- `DECISIONS.md` - engineering decisions.
- `PROGRESS.md` - current handoff and exact verification evidence.
- `AGENTS.md` - repository implementation rules, including the compact Ponytail-style code/check policy.
- `docs/PHASE9_DISTRIBUTION_ACCEPTANCE.md` - Phase 9 distribution/recovery boundary and evidence.
- `docs/PHASE9_PILOT_ACCEPTANCE.md` - authorized pilot write-path technical boundary and measured-pilot handoff.
