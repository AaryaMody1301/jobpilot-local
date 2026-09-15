# jobpilot-local

`jobpilot-local` is a local-first Windows desktop assistant for job discovery, evidence-backed resume tailoring, and user-authorized application automation.

## Status

- Phases 0-3 are complete.
- Phase 4 tailoring is technically implemented and merged. Its private five-real-resume review gate remains independently authoritative until `--phase4-gate-report` succeeds for the current local context.
- Phase 5 job discovery and matching is complete.
- Phase 6 controlled application-engine work is complete and accepted.
- Phase 7 Greenhouse, Lever and Ashby hosted-form adapters are complete and accepted.
- Phase 8 end-to-end orchestration is complete and accepted. Real employer submission remains disabled and belongs to the separately authorized Phase 9 pilot.

## Phase 8

Phase 8 connects the already-built local components without introducing a second orchestration framework:

- verified public/manual discovery and evidence-backed matching feed the existing transactional application journal;
- hard eligibility failures stop as ineligible, while unknown mandatory conditions enter an explicit attention lane;
- eligible work reuses the existing evidence-backed tailoring service and current Phase 4 model/human-review gates;
- immutable application packages bind one discovered-job snapshot to tailoring audit evidence and the current approved application-answer fingerprint;
- stale/deactivated jobs, stale/tampered resume evidence, or changed approved answers invalidate prepared/queued work before submit;
- the existing single application worker remains the only submission worker;
- development submission remains loopback-only and requires explicit positive confirmation;
- live Greenhouse/Lever/Ashby inspection is recognition-only and has no Phase 8 fill/submit activation;
- resource pressure can pause new tailoring without reducing quality gates;
- the desktop attention/history lane exposes review, stale, blocked and pilot-activation states;
- the local-day objective shows 50 confirmed real applications as a target, not a ceiling. Controlled fixture confirmations are excluded and no eligibility/factual/review rule changes to chase the target.

Application launch remains Idle. Discovery/orchestration starts only after explicit Start, and the existing Pause/Stop/Close boundaries remain authoritative.

## Safety and privacy

- Windows 10/11 x64 only for v1.
- No cloud AI, hosted database, telemetry, paid proxy/API, CAPTCHA solving, remote UI scripts, or cloud sign-in.
- Private resume sources, approved facts, generated resumes, local databases, browser state, and model weights stay outside Git under the app-managed local data root.
- JDs, ATS payloads, employer pages, and model output are untrusted data.
- Automatic resume tailoring still requires the current five-distinct-resume Phase 4 gate.
- Phase 8 live employer pages are read-only. Provider adapter writes remain disabled outside controlled loopback fixtures.
- `UNCERTAIN` submission outcomes are never automatically retried.
- Phase 9 separately requires explicit user authorization before any real-application pilot.

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

## Phase 8 acceptance

Windows run `34946104772` at runtime code head `5b2a10827a2b81533a2017dd9828395ded91a383` passed the final Phase 8 path:

- Python and bundled JavaScript syntax validation;
- complete non-external regression suite: 129 passed, 1 skipped, 2 deselected;
- focused controlled end-to-end orchestration with immutable-package freshness, two mandatory answer reviews, package refresh, single controlled submission, explicit confirmation and controlled-counter exclusion;
- stale-package invalidation before claim when approved answers change;
- inherited Phase 7 controlled/live-read-only provider acceptance for Greenhouse, Lever and Ashby;
- source self-test and hidden WebView2/pywebview Phase 8 smoke;
- PyInstaller onedir build;
- packaged self-test and packaged hidden-window smoke.

No real employer form was filled or submitted. See `docs/PHASE8_ACCEPTANCE.md` for the exact boundary and evidence.

## Local data

Runtime data lives under `%LOCALAPPDATA%\JobPilotLocal`. Private candidate data, browser state, and model weights must never be committed.

## Project records

- `SPEC.md` - v1 product requirements.
- `ROADMAP.md` - phase order and current status.
- `DECISIONS.md` - engineering decisions.
- `PROGRESS.md` - current handoff and exact verification evidence.
- `AGENTS.md` - repository implementation rules, including the compact Ponytail-style code/check policy.
- `docs/PHASE8_ACCEPTANCE.md` - Phase 8 acceptance boundary and evidence.
