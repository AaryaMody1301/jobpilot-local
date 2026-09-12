# jobpilot-local

`jobpilot-local` is a local-first Windows desktop assistant for job discovery, evidence-backed resume tailoring, and later user-authorized application automation.

## Status

- Phases 0-3 are complete.
- Phase 4 tailoring is technically implemented and merged. Its private five-real-resume review gate remains independently authoritative until `--phase4-gate-report` returns success for the current local context.
- Phase 5 job discovery and matching is implemented and accepted. Phase 6 employer-form automation has not started, and employer submission remains disabled.

## Phase 5

Phase 5 adds:

- manual job import with credential-free HTTP(S) provenance;
- a versioned starter registry for public Greenhouse, Lever, and Ashby boards;
- user-added board identifiers that are persisted only after a live supported public payload is returned;
- normalized local job storage and conservative deduplication;
- hard targeting checks for excluded employers, target roles, permanent full-time employment, experience limits, office-location rules, overseas sponsorship, and explicit remote restrictions;
- `review` instead of guessing when mandatory location, employment, remote-origin, or sponsorship information is unknown;
- required/preferred requirement extraction and evidence matching using only current approved facts whose source still verifies;
- explainable ranking whose components are visible and are not presented as an ATS score or interview probability;
- a bundled jobs UI. JavaScript performs no network requests; Python owns the public ATS GET boundary.

The implementation intentionally uses Python's standard library for the three JSON GET feeds and reuses the existing desktop shell rather than adding a new HTTP dependency or UI framework.

## Safety and privacy

- Windows 10/11 x64 only for v1.
- No cloud AI, hosted database, telemetry, paid proxy/API, CAPTCHA solving, remote UI scripts, or cloud sign-in.
- Private resume sources, approved facts, generated resumes, local databases, browser state, and model weights stay outside Git under the app-managed local data root.
- JDs, ATS payloads, employer pages, and model output are untrusted data.
- Automatic resume tailoring still requires the current five-distinct-resume Phase 4 gate.
- Phase 5 never fills or submits employer forms.
- `UNCERTAIN` submission outcomes, when later phases exist, are never automatically retried.

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
python -m playwright install chromium
python -m jobpilot.app.main
```

## Phase 5 acceptance

Windows run `34686987747` at head `76398acef947a7c09df83db40fa06b82103f04f0` passed the focused Phase 5 path:

- Python and bundled JavaScript syntax validation;
- the complete non-external regression suite;
- live normalization of one verified public Greenhouse, Lever, and Ashby board;
- source self-test and hidden WebView2/pywebview smoke;
- PyInstaller onedir build;
- packaged self-test and packaged hidden-window smoke.

See `docs/PHASE5_ACCEPTANCE.md` for the exact boundary and check rationale.

## Local data

Runtime data lives under `%LOCALAPPDATA%\JobPilotLocal`. Private candidate data and model weights must never be committed.

## Project records

- `SPEC.md` - v1 product requirements.
- `ROADMAP.md` - phase order and current status.
- `DECISIONS.md` - engineering decisions.
- `PROGRESS.md` - current handoff and exact verification evidence.
- `AGENTS.md` - repository implementation rules, including the compact Ponytail-style code/check policy.
- `docs/PHASE5_ACCEPTANCE.md` - Phase 5 acceptance boundary.
