# jobpilot-local

`jobpilot-local` is an incremental Windows desktop application for local-first job discovery, evidence-backed resume tailoring, and user-authorized application automation.

## Status

Phases 0-2 are complete. Phase 3 - **Local AI and resource manager** - is in final Windows acceptance.

Phase 3 adds local hardware/resource detection, explicit app-managed llama.cpp/model installation, local quality/resource evaluation, per-device performance evidence, and a persisted five-resume review gate for the later tailoring phase. It does **not** enable job discovery, JD-driven resume rewriting, browser form filling, or employer submission.

## Safety and privacy invariants

- Windows 10/11 x64 only for v1.
- No cloud AI, hosted database, telemetry, paid API, paid proxy, CAPTCHA solving, remote UI scripts, or cloud sign-in.
- No startup service or hidden background scheduler.
- Opening the application is always Idle and starts no download/inference/work thread.
- `Start` is required to begin or resume the sample session lifecycle.
- `Pause` schedules no new work.
- `Stop` cancels discovery/generation/pre-submit work when those later phases exist while leaving the UI open.
- `UNCERTAIN` submissions are never automatically retried.
- Only app-owned processes and files proven to be under managed roots may be terminated/deleted.
- Real employer submissions remain disabled until explicit activation after all onboarding/review gates.

## Run the Phase 3 desktop

Production baseline: Python 3.13.15 on Windows 10/11 x64.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
python -m jobpilot.app.main
```

### Resume/fact onboarding

The private master `.tex`, supporting documents, generated PDFs and approved fact values live under `%LOCALAPPDATA%\JobPilotLocal`, not in Git. The supplied real template/facts completed Phase 2 development acceptance, but each local installation still imports its own private source and stores its own source-linked approvals.

Tectonic remains two-step: explicitly populate missing support files when needed, then require a cached-only `--untrusted` compile before the local resume gate is ready.

### Local AI setup

The initial Phase 3 catalogue is intentionally small:

- llama.cpp stable baseline `v0.4.0`, tested Windows build `b10809`;
- checksum-pinned Windows x64 CPU runtime plus optional Vulkan runtime;
- `ggml-org/Qwen3-4B-GGUF` revision `2f3b082b1356a6123f7ed71e65aea340da25d53c`;
- `Qwen3-4B-Q4_K_M.gguf`, exact 2,497,280,640 bytes, SHA-256 `ab27b9bfa375a178d6cba48f3ad892b94b7739659dcc7aae8058ce0ffed6b328`, Apache-2.0.

The app never downloads those artifacts on launch. The Model & resources screen first measures the actual machine, shows reserved RAM/disk and GPU evidence, then requires explicit confirmation for each runtime/model download. Files are installed only after exact size/SHA verification.

CPU evaluation is forced with `--device none`. Vulkan is considered only after the installed llama.cpp runtime reports one or more `VulkanN` devices through `--list-devices`; each selected configuration must independently pass the same structured/factual/resource evaluation. The fastest **passing** measured configuration is selected for future Phase 4 review.

Automatic tailoring remains disabled. Selection creates a persisted review gate at **0/5 distinct resumes**. Phase 4 supplies those human-reviewed tailored resumes; Phase 3 cannot bypass that gate.

If the reserved resources cannot safely run the tested catalogue, the app reports that result instead of using cloud inference or weakening factual/quality requirements.

## Acceptance checks

```powershell
pytest -m "not external"
python scripts\phase2_tectonic_acceptance.py
python scripts\phase3_model_acceptance.py
python -m jobpilot.app.main --self-test
python -m jobpilot.app.main --window-smoke
pyinstaller --clean --noconfirm packaging\jobpilot.spec
.\dist\jobpilot-local\jobpilot-local.exe --self-test
.\dist\jobpilot-local\jobpilot-local.exe --window-smoke
```

`phase3_model_acceptance.py` intentionally performs public CI-only downloads of the exact pinned CPU runtime and Qwen3 4B weight, then runs localhost-only inference. Normal application downloads still require the UI approval actions.

## Local data

Runtime data is outside Git under `%LOCALAPPDATA%\JobPilotLocal`: SQLite, immutable source documents, generated artifacts, model weights, app-managed tools, browser data, caches, backups, runtime files, and logs. Private candidate data and model weights must never be committed.

## Project records

- `SPEC.md` - agreed requirements and approved changes.
- `ROADMAP.md` - dependency-ordered phases/status.
- `DECISIONS.md` - engineering decisions/rationale.
- `PROGRESS.md` - actual repository state, evidence, blockers, exact continuation.
- `docs/PHASE3_ACCEPTANCE.md` - Phase 3 test gates and exact pinned catalogue.

Phase 4 is intentionally not started in this branch.
