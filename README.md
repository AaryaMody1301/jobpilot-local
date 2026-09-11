# jobpilot-local

`jobpilot-local` is an incremental Windows desktop application for local-first job discovery, evidence-backed resume tailoring, and user-authorized application automation.

## Status

Phases 0-3 are complete and merged. Phase 4 - **Evidence-based resume tailoring** - has passed its controlled Windows technical acceptance but remains **partial** until the user has approved five distinct real tailored resumes for the current validated model/profile/template context.

Phase 5 job discovery and all employer submission paths remain disabled.

## Safety and privacy invariants

- Windows 10/11 x64 only for v1.
- No cloud AI, hosted database, telemetry, paid API, paid proxy, CAPTCHA solving, remote UI scripts, or cloud sign-in.
- No startup service or hidden background scheduler.
- Opening the application is always Idle and starts no download/inference/application work.
- Runtime/model downloads require explicit confirmation and exact catalogue size/SHA verification.
- Private master/source documents, approved facts, generated resumes and model weights live outside Git under the app-managed local data root.
- JD text is untrusted data. Embedded instructions never override approved facts, template boundaries, or validation.
- Local model output is structured plain-text edit intent; application code renders controlled LaTeX.
- Only source-linked approved facts may support claims. Cross-bullet claim composition, unsupported content, and silent removal of existing numeric/date/metric literals are blocked.
- Tailoring compilation uses app-managed Tectonic cached-only and `--untrusted`; it cannot silently download packages.
- Pending review becomes stale if master/facts/template/baseline/profile/model/evaluation evidence changes.
- Automatic tailoring requires five distinct persisted human approvals in the **current** review context. Controlled CI output never counts toward that gate.
- `UNCERTAIN` submissions are never automatically retried when submission phases later exist.
- Only app-owned processes/files proven under managed roots may be terminated/deleted.
- Real employer submissions remain disabled until later explicit activation after all gates.

## Run the Phase 4 desktop

Production baseline: Python 3.13.15 on Windows 10/11 x64.

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
python -m jobpilot.app.main
```

### 1. Resume/fact onboarding

Use the **Resume & facts** screen to import the private master `.tex`, install the pinned Tectonic tool, explicitly populate any missing support cache, require the subsequent cached-only baseline, confirm editable regions, and resolve every candidate fact. The private source and fact values are stored locally and are not committed to this repository.

### 2. Local AI setup

The Phase 3 tested catalogue remains the Phase 4 baseline:

- llama.cpp stable baseline `v0.4.0`, tested Windows build `b10809`;
- checksum-pinned Windows x64 CPU runtime plus optional Vulkan runtime;
- `ggml-org/Qwen3-4B-GGUF` revision `2f3b082b1356a6123f7ed71e65aea340da25d53c`;
- `Qwen3-4B-Q4_K_M.gguf`, 2,497,280,640 bytes, SHA-256 `ab27b9bfa375a178d6cba48f3ad892b94b7739659dcc7aae8058ce0ffed6b328`, Apache-2.0.

The app measures the actual machine and evaluates installed CPU/Vulkan configurations. CPU is explicit `--device none`; Vulkan uses only exact device IDs reported by the verified llama.cpp runtime. Speed is compared only among configurations that pass all quality/resource gates.

### 3. Manual-JD tailoring and review

Phase 4 accepts manually pasted JD text. An optional source URL is recorded as inert provenance only; it is not fetched by Phase 4. The app:

1. labels the JD untrusted and hashes it;
2. asks the selected validated local model for structured keyword mappings and plain-text wording edits;
3. validates every used keyword/fact and requires field-linked source evidence;
4. renders only confirmed simple wording regions through application code;
5. compiles cached-only with Tectonic;
6. checks protected source structure, page count/geometry, overflow and expected PDF content;
7. writes a tamper-evident local audit package;
8. shows PDF, diff, keyword/fact mapping and validation for human review.

Approve only accurate outputs. Reject/correct facts and regenerate when necessary.

The first five **distinct** approved real tailored resumes for a selected model must share one current validation context. Changes to the approved fact bank, targeting/profile, template map, offline baseline or selected/evaluated model configuration invalidate/reset stale review evidence. Automatic tailoring remains disabled until the persisted current-context gate reaches 5/5.

## Verified Phase 4 technical baseline

Windows run `34593289955` at code head `e15ae7dc4aed425cb2675921e2c119b1c961fa2a` passed:

- **117 passed, 1 intentional platform-guard skip, 2 external probes deselected**;
- real pinned local Qwen3/Tectonic controlled tailoring;
- malicious instruction-like JD text treated as data;
- one validated field-linked edit with one approved fact reference;
- cached-only compile, unchanged page count and no overflow;
- result `needs_review`, review gate still 0/5 and automatic tailoring disabled;
- source/package self-tests, hidden WebView2 smokes and PyInstaller onedir build.

This controlled result proves mechanics only and is not a human review approval.

## Acceptance checks

```powershell
pytest -m "not external"
python scripts\phase4_tailoring_acceptance.py
python -m jobpilot.app.main --self-test
python -m jobpilot.app.main --window-smoke
pyinstaller --clean --noconfirm packaging\jobpilot.spec
.\dist\jobpilot-local\jobpilot-local.exe --self-test
.\dist\jobpilot-local\jobpilot-local.exe --window-smoke
```

`phase4_tailoring_acceptance.py` intentionally performs CI-only public downloads of the exact already-approved test catalogue and runs localhost-only inference. Normal application downloads still require explicit UI approval.

## Local data

Runtime data lives under `%LOCALAPPDATA%\JobPilotLocal`: SQLite, immutable source documents, generated artifacts, model weights, app-managed tools, browser data, caches, backups, runtime files, and logs. Private candidate data and model weights must never be committed.

## Project records

- `SPEC.md` - agreed requirements and approved changes.
- `ROADMAP.md` - phase dependencies, acceptance and status.
- `DECISIONS.md` - engineering decisions and rationale.
- `PROGRESS.md` - actual repository state, test evidence, blockers and exact continuation.
- `docs/PHASE4_ACCEPTANCE.md` - Phase 4 technical and human acceptance gates.

Phase 5 is intentionally not started while the Phase 4 human review gate remains incomplete.
