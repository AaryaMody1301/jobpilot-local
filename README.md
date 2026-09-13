# jobpilot-local

`jobpilot-local` is a local-first Windows desktop assistant for job discovery, evidence-backed resume tailoring, and user-authorized application automation.

## Status

- Phases 0-3 are complete.
- Phase 4 tailoring is technically implemented and merged. Its private five-real-resume review gate remains independently authoritative until `--phase4-gate-report` succeeds for the current local context.
- Phase 5 job discovery and matching is complete.
- Phase 6 controlled application-engine work is complete and accepted. It is deliberately limited to app-controlled localhost/loopback fixtures; real employer form adapters and real employer submission remain disabled and belong to later phases.

## Phase 6

Phase 6 adds the application engine without crossing the real-employer boundary:

- transactional SQLite application transitions and persistent duplicate prevention;
- one explicit-session application worker; launch remains Idle with no hidden scheduler;
- a dedicated persistent Playwright Chromium profile under the app-managed data root;
- localhost/loopback-only controlled form targets, with non-loopback HTTP(S) browser requests blocked;
- exact-context approved-answer reuse keyed by question identity plus a semantic SHA-256 context fingerprint;
- a review lane for unknown mandatory questions while other queued controlled fixtures can continue;
- conservative blocking for CAPTCHA/challenge, assessment, login/verification, payment, and unsupported required fields;
- bounded retries only before the submit boundary;
- `SUBMITTING` journaled immediately before the click, explicit positive confirmation required for `CONFIRMED`, and ambiguous post-submit outcomes becoming terminal `UNCERTAIN`;
- safe recovery of interrupted pre-submit work to the queue;
- a bundled Phase 6 UI for the controlled queue, review lane, worker state, and application journal.

The implementation reuses the existing application package/state machine, SQLite layer, Playwright dependency, managed browser/profile paths, and desktop shell. No new runtime dependency or provider abstraction was added.

## Safety and privacy

- Windows 10/11 x64 only for v1.
- No cloud AI, hosted database, telemetry, paid proxy/API, CAPTCHA solving, remote UI scripts, or cloud sign-in.
- Private resume sources, approved facts, generated resumes, local databases, browser state, and model weights stay outside Git under the app-managed local data root.
- JDs, ATS payloads, employer pages, and model output are untrusted data.
- Automatic resume tailoring still requires the current five-distinct-resume Phase 4 gate.
- Phase 6 rejects non-loopback application targets and does not implement Greenhouse, Lever, or Ashby employer-form adapters.
- `UNCERTAIN` submission outcomes are never automatically retried.

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

The Playwright browser path above matches JobPilot's app-managed browser root. The application still launches Idle; the controlled browser worker is created only after explicit Start.

## Phase 6 acceptance

Windows run `34743335410` at code head `8d1cb12d1a5ff096ecfc8b8df470777ee3b99c43` passed the focused Phase 6 path:

- Python and bundled JavaScript syntax validation;
- the complete non-external regression suite;
- the controlled localhost Playwright acceptance covering review, exact-context answer reuse, blocking, retry, duplicate prevention, single-worker submission, confirmation, and `UNCERTAIN` handling;
- source self-test and hidden WebView2/pywebview smoke;
- PyInstaller onedir build;
- packaged self-test and packaged hidden-window smoke.

See `docs/PHASE6_ACCEPTANCE.md` for the exact boundary and check rationale.

## Local data

Runtime data lives under `%LOCALAPPDATA%\JobPilotLocal`. Private candidate data, browser state, and model weights must never be committed.

## Project records

- `SPEC.md` - v1 product requirements.
- `ROADMAP.md` - phase order and current status.
- `DECISIONS.md` - engineering decisions.
- `PROGRESS.md` - current handoff and exact verification evidence.
- `AGENTS.md` - repository implementation rules, including the compact Ponytail-style code/check policy.
- `docs/PHASE6_ACCEPTANCE.md` - Phase 6 acceptance boundary and evidence.
