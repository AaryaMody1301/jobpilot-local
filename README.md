# jobpilot-local

`jobpilot-local` is a local-first Windows desktop assistant for job discovery, evidence-backed resume tailoring, and user-authorized application automation.

## Status

- Phases 0-3 are complete.
- Phase 4 tailoring is technically implemented and merged. Its private five-real-resume review gate remains independently authoritative until `--phase4-gate-report` succeeds for the current local context.
- Phase 5 job discovery and matching is complete.
- Phase 6 controlled application-engine work is complete and accepted.
- Phase 7 Greenhouse, Lever and Ashby hosted-form adapters are complete and accepted.
- Phase 8 end-to-end orchestration is complete and accepted.
- Phase 9 distribution/recovery and the separately authorized measured-pilot write path are technically implemented and accepted.
- Final repository-level closeout PR #16 merged into `main` at `f5df77697b667f14df55583d94058f175ece5074` after every Phase 0 through Phase 9 PR-head workflow passed.
- **Phase 9 remains in progress only because a measured real-world pilot has not yet been run and no 50/day capability claim has been established.**

The final accepted Python/build baseline is Playwright 1.63.0, pypdf 6.19.0, setuptools 84.0.0, PyInstaller 6.22.3, pytest 9.1.1, pip-audit 2.10.1, psutil 7.2.2 and pywebview 6.2.1.

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
8. immediately before filling/submitting, JobPilot rechecks package freshness, re-inspects the form and re-verifies the managed tailored PDF hash;
9. immediately before the click, JobPilot recaptures the confirmation baseline; only explicit positive evidence that appears after the click counts as `CONFIRMED`, while an ambiguous outcome becomes terminal `UNCERTAIN` and is not automatically retried.

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

## Acceptance

Historical distribution/recovery acceptance is recorded at technical head `b5ebda60793e3f61a25885b4370ebf5242d2e705`, Windows run `35056956675`.

Historical measured-pilot activation implementation acceptance is recorded at technical head `06a2f31d47dc3dbe09bcf0eda3fd34bf0278d0e5`, Windows run `35072562186`.

The final repository-level closeout is PR #16. Its exact head `2004157ad079ffdfe51f17f86155b8b2027f09d7` passed all Phase 0 through Phase 9 pull-request workflows on 2026-09-17, including dependency audit, the deterministic regression suite, the delayed pre-submit confirmation regression, final Phase 9 UI interaction coverage at the 960x660 minimum viewport, backup/restore, inherited provider/orchestration gates, source/frozen/installed Windows smokes, hermetic browser build, verified distribution build, clean install/in-place upgrade, and artifact upload. It merged as `f5df77697b667f14df55583d94058f175ece5074`.

The accepted technical runs did **not** fill or submit a real employer form. Live Greenhouse/Lever/Ashby CI checks remain read-only; writes are exercised only against controlled loopback fixtures. See `docs/PHASE9_DISTRIBUTION_ACCEPTANCE.md` and `docs/PHASE9_PILOT_ACCEPTANCE.md` for exact boundaries and evidence.

## Local AI baseline

The validated runtime remains llama.cpp v0.4.0 / build b10809 with the checksum-pinned Qwen3 4B GGUF catalogue entry. Newer upstream releases are metadata-only until exact artifacts receive checksum/license records, local evaluation, and the existing replacement review gate. They are never silently substituted during update or cleanup.

## Local data

Runtime data lives under `%LOCALAPPDATA%\JobPilotLocal`. Private candidate data, browser state, generated application packages, local backups and model weights must never be committed.

## Project records

- `SPEC.md` - v1 product requirements.
- `ROADMAP.md` - phase order and current status.
- `DECISIONS.md` - engineering decisions.
- `PROGRESS.md` - current handoff and exact verification evidence.
- `AGENTS.md` - repository implementation rules, including the compact Ponytail-style code/check policy.
- `docs/PHASE9_DISTRIBUTION_ACCEPTANCE.md` - Phase 9 distribution/recovery boundary and evidence.
- `docs/PHASE9_PILOT_ACCEPTANCE.md` - authorized pilot write-path technical boundary and measured-pilot handoff.

## License

Original JobPilot Local code is MIT licensed. External binaries, browsers, Python packages, model weights and other third-party components retain their own licenses and notices. See `THIRD_PARTY_NOTICES.md` and `packaging/BROWSER_NOTICES.md`.
