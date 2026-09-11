# jobpilot-local

`jobpilot-local` is an incremental Windows desktop application for local-first job discovery, evidence-backed resume tailoring, and user-authorized application automation.

## Status

Phases 0-3 are complete on the Phase 3 branch. Phase 3 - **Local AI and resource manager** - has passed the complete Windows branch-head acceptance and is awaiting pull-request merge verification. Phase 4 has not started.

Phase 3 adds local hardware/resource detection, explicit app-managed llama.cpp/model installation, local quality/resource evaluation, per-device performance evidence, revision-safe replacement primitives, and a persisted five-distinct-resume review gate for the later tailoring phase. It does **not** enable job discovery, JD-driven resume rewriting, browser form filling, or employer submission.

## Safety and privacy invariants

- Windows 10/11 x64 only for v1.
- No cloud AI, hosted database, telemetry, paid API, paid proxy, CAPTCHA solving, remote UI scripts, or cloud sign-in.
- No startup service or hidden background scheduler.
- Opening the application is always Idle and starts no download/inference/work thread.
- Runtime/model downloads require explicit confirmation and exact catalogue size/SHA verification.
- `Start` is required to begin or resume the sample session lifecycle; model setup/evaluation uses separate explicit actions.
- `Pause` schedules no new sample work.
- `UNCERTAIN` submissions are never automatically retried in later phases.
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

The initial Phase 3 catalogue is deliberately small:

- llama.cpp stable baseline `v0.4.0`, tested Windows build `b10809`;
- checksum-pinned Windows x64 CPU runtime plus optional Vulkan runtime;
- `ggml-org/Qwen3-4B-GGUF` revision `2f3b082b1356a6123f7ed71e65aea340da25d53c`;
- `Qwen3-4B-Q4_K_M.gguf`, exact 2,497,280,640 bytes, SHA-256 `ab27b9bfa375a178d6cba48f3ad892b94b7739659dcc7aae8058ce0ffed6b328`, Apache-2.0.

The app never downloads these artifacts on launch. The Model & resources screen measures the actual machine, shows reserved RAM/disk and GPU evidence, and requires explicit confirmation for each runtime/model download. Files are installed only after exact size/SHA verification.

CPU evaluation is forced with `--device none`. Vulkan is considered only after the installed llama.cpp runtime reports one or more `VulkanN` devices through `--list-devices`; each selected configuration must independently pass the same structured/factual/resource evaluation. Speed is compared only among passing configurations.

Automatic tailoring remains disabled. Selecting a validated configuration creates a persisted review gate at **0/5 distinct resumes**. Phase 4 supplies those human-reviewed tailored resumes; Phase 3 has no UI/API shortcut to complete the gate.

If reserved resources cannot safely run the tested catalogue, the app reports that result instead of using cloud inference or weakening factual/quality requirements.

## Verified Windows CPU baseline

Combined Phase 3 code-head run `34575604480` passed:

- **101 passed, 1 intentional skip, 2 external probes deselected**;
- preserved Phase 2 cached-only Tectonic acceptance;
- exact pinned llama.cpp/Qwen3 download and integrity verification;
- CPU `--device none` evaluation at 4096 context;
- structured, malicious-JD/factual, controlled-tailoring and resource gates;
- **12.789 generated tokens/second**, **5,021,855,744 bytes peak process-tree RSS**, normal live memory pressure;
- 0/5 future review approvals and automatic tailoring disabled;
- source/package self-tests, WebView2 smokes and PyInstaller onedir build.

Exact record-head run `34576262983` then repeated the complete workflow successfully before Phase 3 was marked complete.

This is a CI CPU compatibility baseline, not a claim about the user's own hardware. The application must probe and evaluate the actual local CPU/Vulkan configuration before selection.

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
- `docs/PHASE3_ACCEPTANCE.md` - Phase 3 gates and exact pinned catalogue.

Phase 4 is intentionally not started in this branch.
