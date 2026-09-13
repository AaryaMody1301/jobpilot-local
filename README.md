# jobpilot-local

`jobpilot-local` is a local-first Windows desktop assistant for job discovery, evidence-backed resume tailoring, and user-authorized application automation.

## Status

- Phases 0-3 are complete.
- Phase 4 tailoring is technically implemented and merged. Its private five-real-resume review gate remains independently authoritative until `--phase4-gate-report` succeeds for the current local context.
- Phase 5 job discovery and matching is complete.
- Phase 6 controlled application-engine work is complete and accepted.
- Phase 7 Greenhouse, Lever and Ashby hosted-form adapters are complete and accepted. Current live checks remain read-only; Phase 8 orchestration and Phase 9 real-application pilot activation have not started.

## Phase 7

Phase 7 adds the supported hiring-platform adapter boundary without enabling real submissions:

- one shared hosted-form adapter implementation under the existing `jobpilot.applications` package;
- Greenhouse support for `job-boards.greenhouse.io` and `boards.greenhouse.io`;
- Lever support for `jobs.lever.co` and `jobs.eu.lever.co`;
- Ashby support for `jobs.ashbyhq.com`;
- exact provider-host validation and credential-free absolute HTTP(S) targets;
- read-only live form recognition of visible fields, required status and one supported submit control;
- controlled loopback filling/submission for adapter acceptance only;
- hard live write guards: adapter `fill()`/`submit()` cannot operate on real employer pages;
- conservative blockers for CAPTCHA, login/verification, assessment, actual payment/card controls and unsupported required fields;
- explicit positive confirmation required after controlled submit;
- unsupported live variants reported instead of guessed.

The implementation reuses the existing `ApplicationAdapter` contract, Playwright dependency and Phase 5 public-board discovery. No new runtime dependency, provider SDK, browser framework or duplicate application state machine was added.

Current read-only live recognition on the accepted Phase 7 head found application fields and a single submit control for current GitLab/Greenhouse, Nium/Lever and Ashby/Ashby examples. Each also exposed CAPTCHA integration, so all three current examples are conservatively reported unsupported for automatic submission. No real employer form was filled or submitted.

## Safety and privacy

- Windows 10/11 x64 only for v1.
- No cloud AI, hosted database, telemetry, paid proxy/API, CAPTCHA solving, remote UI scripts, or cloud sign-in.
- Private resume sources, approved facts, generated resumes, local databases, browser state, and model weights stay outside Git under the app-managed local data root.
- JDs, ATS payloads, employer pages, and model output are untrusted data.
- Automatic resume tailoring still requires the current five-distinct-resume Phase 4 gate.
- Phase 7 live employer pages are recognition-only; provider adapter writes require an app-controlled loopback fixture.
- `UNCERTAIN` submission outcomes are never automatically retried.
- Phase 8 must still connect the provider adapters to discovery/matching/tailoring/application orchestration. Phase 9 separately requires explicit user authorization before any real-application pilot.

Check the private Phase 4 gate without exposing resume/JD/fact content:

```powershell
python -m jobpilot.app.main --phase4-gate-report
```

## Run

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
$env:PLAYWRIGHT_BROWSERS_PATH="$env:LOCALAPPDATA\JobPilotLocal\browsers"
python -m playwright install chromium
python -m jobpilot.app.main
```

The application still launches Idle. Phase 7 does not add hidden scheduling or real-employer execution.

## Phase 7 acceptance

Windows run `34745312735` at code head `3a95d0a32755c94b21ec77c209749986718167a6` passed the final Phase 7 path:

- Python and bundled JavaScript syntax validation;
- the complete non-external regression suite;
- controlled loopback fill/submit/explicit-confirmation acceptance for Greenhouse, Lever and Ashby adapters;
- read-only live recognition for current Greenhouse, Lever and Ashby hosted forms;
- fail-closed live write guards;
- source self-test and hidden WebView2/pywebview smoke;
- PyInstaller onedir build;
- packaged self-test and packaged hidden-window smoke.

See `docs/PHASE7_ACCEPTANCE.md` for the exact boundary, live evidence and check rationale.

## Local data

Runtime data lives under `%LOCALAPPDATA%\JobPilotLocal`. Private candidate data, browser state, and model weights must never be committed.

## Project records

- `SPEC.md` - v1 product requirements.
- `ROADMAP.md` - phase order and current status.
- `DECISIONS.md` - engineering decisions.
- `PROGRESS.md` - current handoff and exact verification evidence.
- `AGENTS.md` - repository implementation rules, including the compact Ponytail-style code/check policy.
- `docs/PHASE7_ACCEPTANCE.md` - Phase 7 acceptance boundary and evidence.
