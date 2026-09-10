# jobpilot-local

`jobpilot-local` is an incremental Windows desktop application for local-first job discovery, evidence-backed resume tailoring, and user-authorized application automation.

## Status

Phase 0 feasibility/architecture is complete. Phase 1 builds the runnable desktop foundation using clearly labelled local sample work. No job discovery, resume rewriting, local-model inference, ATS form filling, or real-employer submission is enabled yet.

## Safety and privacy invariants

- Windows 10/11 x64 only for v1.
- No cloud AI, hosted database, telemetry, paid API, paid proxy, or CAPTCHA solving.
- No startup service or hidden background scheduler.
- Opening the application is always Idle and does not create a work thread.
- `Start` is required to begin or resume scheduling.
- `Pause` schedules no new work.
- `Stop` cancels discovery, generation, and pre-submit work while leaving the UI open.
- Closing stops discovery/generation immediately. A later submission that may already have started may receive up to 60 seconds for confirmation; otherwise it becomes `UNCERTAIN`.
- `UNCERTAIN` submissions are never automatically retried.
- Only processes and files proven to be owned by this application may be terminated or deleted.
- Real employer submissions remain disabled until explicit user activation after onboarding and review gates.

## Run the Phase 1 desktop

Production baseline: Python 3.13.15 on Windows 10/11 x64.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
python -m jobpilot.app.main
```

The dashboard is deliberately marked **Phase 1 · Sample Mode**. Start only advances local sample lifecycle items used to prove Start/Pause/Stop and persistence.

Run acceptance checks:

```powershell
pytest -m "not external"
python -m jobpilot.app.main --self-test
python -m jobpilot.app.main --window-smoke
pyinstaller --clean --noconfirm packaging\jobpilot.spec
.\dist\jobpilot-local\jobpilot-local.exe --self-test
.\dist\jobpilot-local\jobpilot-local.exe --window-smoke
```

See `docs/PHASE1_ACCEPTANCE.md` for exact Phase 1 expectations. External Tectonic/llama.cpp feasibility checks remain explicitly opt-in with `pytest -m external`.

## Local data

Runtime data is kept outside Git under `%LOCALAPPDATA%\JobPilotLocal`, including the SQLite database and app-owned document, artifact, model, browser, cache, backup, runtime, and log folders. Private candidate data and generated artifacts must never be committed.

## Project records

- `SPEC.md` - agreed product requirements and approved changes.
- `ROADMAP.md` - dependency-ordered phases and status.
- `DECISIONS.md` - engineering decisions and evidence.
- `PROGRESS.md` - verification evidence, blockers, and exact next step.

No personal resume, answers, browser session, model weights, generated application package, or secret belongs in Git.
