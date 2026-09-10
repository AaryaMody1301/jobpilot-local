# Phase 1 acceptance - runnable desktop foundation

Phase 1 proves the local desktop/storage/lifecycle foundation only. Discovery, resume tailoring, local-model inference, ATS browsers, and employer submission remain disabled.

## Required behavior

- Launch creates the app-owned data folders and SQLite database, applies migrations, and opens a new runtime session in `idle`.
- Launch does not create or start the sample worker.
- The bundled UI is local HTML/CSS/JavaScript and exposes no remote script or telemetry dependency.
- `Start` creates/resumes only the Phase 1 sample lifecycle worker.
- `Pause` stops scheduling new sample items. An item already running at the instant Pause is pressed may finish.
- `Stop` cancels/requeues any current sample item, joins the worker, leaves the desktop open, and returns the runtime session to `idle`.
- Closing joins the worker, requeues safe sample work, marks the session `exited`, closes SQLite, and leaves no JobPilot sample worker alive.
- An unclean previous session is marked `crashed`, safely running pre-submit work is requeued, and the new launch remains `idle`.
- Targeting defaults match `SPEC.md`, are editable, validate before persistence, and survive normal restart.
- The sample dashboard always reports zero real confirmed applications in Phase 1.

## Automated checks

Run on Windows 10/11 x64 development machines:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
pytest -m "not external"
python -m jobpilot.app.main --self-test
python -m jobpilot.app.main --window-smoke
```

Package acceptance:

```powershell
pyinstaller --clean --noconfirm packaging\jobpilot.spec
.\dist\jobpilot-local\jobpilot-local.exe --self-test
.\dist\jobpilot-local\jobpilot-local.exe --window-smoke
```

`--window-smoke` opens a hidden Edge/WebView2 window, verifies the bundled document and pywebview JS bridge, and exits. It performs no external request.

## Manual review

Launch with:

```powershell
python -m jobpilot.app.main
```

Verify the dashboard is initially Idle, the banner says Phase 1 Sample Mode, navigation works, targeting changes persist after restart, and Start/Pause/Stop affect only the sample lifecycle list.

## Phase boundary

A passing Phase 1 does not establish resume compatibility, model quality, job-discovery correctness, or application-submission capability. Those belong to later phases.
