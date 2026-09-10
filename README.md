# jobpilot-local

`jobpilot-local` is an incremental Windows desktop application for local-first job discovery, evidence-backed resume tailoring, and user-authorized application automation.

## Status

Phase 0 - feasibility and architecture. No real-employer submission capability is enabled. The repository currently contains architecture records and executable feasibility primitives/tests only.

## Safety and privacy invariants

- Windows 10/11 x64 only for v1.
- No cloud AI, hosted database, telemetry, paid API, paid proxy, or CAPTCHA solving.
- No startup service or hidden background scheduler.
- Opening the application must never begin work automatically.
- `Start` is required to begin or resume scheduling.
- `Pause` schedules no new work.
- `Stop` cancels discovery, generation, and pre-submit work while leaving the UI open.
- Closing stops discovery/generation immediately. A submission that may already have started may receive up to 60 seconds for confirmation; otherwise it becomes `UNCERTAIN`.
- `UNCERTAIN` submissions are never automatically retried.
- Only processes and files proven to be owned by this application may be terminated or deleted.
- Real employer submissions remain disabled until explicit user activation after onboarding and review gates.

## Phase 0 developer checks

Production baseline: Python 3.13.15 on Windows 10/11 x64.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
pytest -m "not external"
```

External feasibility checks are intentionally opt-in because they require separately installed or approved binaries/models:

```powershell
pytest -m external
```

See `docs/PHASE0_ACCEPTANCE.md` for exact expectations and environment variables.

## Project records

- `SPEC.md` - agreed product requirements and approved changes.
- `ROADMAP.md` - dependency-ordered phases and status.
- `DECISIONS.md` - engineering decisions and evidence.
- `PROGRESS.md` - verification evidence, blockers, and exact next step.

No personal resume, answers, browser session, model weights, generated application package, or secret belongs in Git.
