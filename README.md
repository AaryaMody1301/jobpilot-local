# jobpilot-local

`jobpilot-local` is an incremental Windows desktop application for local-first job discovery, evidence-backed resume tailoring, and user-authorized application automation.

## Status

Phase 0 feasibility/architecture and Phase 1 runnable desktop foundation are complete. Phase 2 resume onboarding/fact-bank functionality is implemented and controlled-fixture verified on `phase-2-resume-fact-bank`, but Phase 2 remains **partial** until the user's actual LaTeX resume and its local dependencies pass the same baseline/mapping/fact-review workflow.

No AI tailoring, job discovery, ATS form filling, or real-employer submission is enabled yet.

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

## Run the Phase 2 desktop

Production baseline: Python 3.13.15 on Windows 10/11 x64.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
python -m jobpilot.app.main
```

The Phase 2 UI adds **Resume & facts**. Importing a master resume uses a native file picker and copies the selected `.tex` immutably into `%LOCALAPPDATA%\JobPilotLocal`; personal documents are never committed to Git.

Tectonic setup is deliberately two-step:

1. click **Install Tectonic 0.17.0** and approve the pinned official binary download;
2. if the original resume needs uncached support files, click **Compile + cache packages** and explicitly approve package network access;
3. click **Compile cached only** and require that offline compile to succeed before the baseline gate can pass;
4. review candidate editable regions and confirm the mapping;
5. correct/approve/reject every candidate fact. Extraction never auto-approves facts.

Run repository acceptance checks:

```powershell
pytest -m "not external"
python scripts\phase2_tectonic_acceptance.py
python -m jobpilot.app.main --self-test
python -m jobpilot.app.main --window-smoke
pyinstaller --clean --noconfirm packaging\jobpilot.spec
.\dist\jobpilot-local\jobpilot-local.exe --self-test
.\dist\jobpilot-local\jobpilot-local.exe --window-smoke
```

Controlled Windows Phase 2 acceptance run `34467708811` passed 67 tests (1 intentional platform-guard skip, 2 external tests deselected), a real Tectonic 0.17.0 network-to-cache-to-offline baseline, source/package self-tests, and source/package hidden WebView2 smokes. See `docs/PHASE2_ACCEPTANCE.md` and `PROGRESS.md`.

## Local data

Runtime data is kept outside Git under `%LOCALAPPDATA%\JobPilotLocal`, including the SQLite database and app-owned document, artifact, model, browser, tool, cache, backup, runtime, and log folders. Private candidate data and generated artifacts must never be committed.

## Current blocker

Phase 2 cannot be marked complete until the user's actual `.tex` resume is tested. If that source references local `.cls`, `.sty`, fonts, images, bibliography files, or custom resume commands, the exact dependencies/mapping must be handled without silently changing the master template or compiler.

## Project records

- `SPEC.md` - agreed product requirements and approved changes.
- `ROADMAP.md` - dependency-ordered phases and status.
- `DECISIONS.md` - engineering decisions and evidence.
- `PROGRESS.md` - verification evidence, blockers, and exact next step.

No personal resume, answers, browser session, model weights, generated application package, or secret belongs in Git.
