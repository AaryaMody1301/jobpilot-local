# jobpilot-local

`jobpilot-local` is an incremental Windows desktop application for local-first job discovery, evidence-backed resume tailoring, and user-authorized application automation.

## Status

Phase 0 feasibility/architecture and Phase 1 runnable desktop foundation are complete. Phase 2 resume onboarding/fact-bank functionality is also complete pending merge of PR #4: the real template structure was validated outside Git, the corresponding sanitized Tectonic compatibility fixture passes Windows CI, and the user explicitly approved all factual claims in the supplied resume exactly as written.

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

The real-resume finalization run `34568832244` passed 70 tests (1 intentional platform-guard skip, 2 external tests deselected), a real Tectonic 0.17.0 network-to-cache-to-offline acceptance, a two-page sanitized fixture matching the supplied template structure, source/package self-tests, and source/package hidden WebView2 smokes. See `docs/PHASE2_ACCEPTANCE.md`, `ROADMAP.md`, and `PROGRESS.md`.

## Real resume privacy

The supplied resume source and its factual claims are not stored in this public repository. Only sanitized structural fixtures and the fact-bank/provenance machinery belong in Git. User approval of the supplied facts is recorded as a phase acceptance decision without reproducing the private claims.

## Local data

Runtime data is kept outside Git under `%LOCALAPPDATA%\JobPilotLocal`, including the SQLite database and app-owned document, artifact, model, browser, tool, cache, backup, runtime, and log folders. Private candidate data and generated artifacts must never be committed.

## Next phase

After PR #4 is merged, Phase 3 is the next implementation phase: local hardware/resource detection, app-managed llama.cpp/model installation, validation/evaluations, one-at-a-time inference, resource-pressure handling, and safe replacement/rollback/deletion. Phase 4 resume tailoring must not start during Phase 3.

## Project records

- `SPEC.md` - agreed product requirements and approved changes.
- `ROADMAP.md` - dependency-ordered phases and status.
- `DECISIONS.md` - engineering decisions and evidence.
- `PROGRESS.md` - verification evidence, blockers, and exact next step.

No personal resume, answers, browser session, model weights, generated application package, or secret belongs in Git.
