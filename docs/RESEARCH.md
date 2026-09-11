# Feasibility and dependency research

Official documentation and project-owned sources are preferred. Advertised behavior from reference automation repositories is not accepted without tests.

## Phase 0 baseline - 2026-09-10

### Python and Python packages

- Python 3.13.15 (2026-08-05): https://www.python.org/downloads/release/python-31315/
- pywebview 6.2.1: https://pypi.org/project/pywebview/
- Playwright Python 1.62.0: https://pypi.org/project/playwright/
- psutil 7.2.2: https://pypi.org/project/psutil/
- pypdf 6.18.0: https://pypi.org/project/pypdf/
- pytest 9.1.1: https://pypi.org/project/pytest/
- PyInstaller 6.22.2: https://pypi.org/project/pyinstaller/

Pywebview documents a blocking `window.events.closing` event whose handler can cancel closing. Playwright documents version-coupled browser binaries and `PLAYWRIGHT_BROWSERS_PATH`; JobPilot uses app-managed browser storage.

### Windows process ownership

Microsoft documents Job Objects as a mechanism for managing groups of processes as a unit. `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` terminates associated processes when the final job handle closes, and Windows 8+ supports nested jobs. JobPilot launches owned children suspended, assigns the Job Object, then resumes them.

### Tectonic

Tectonic 0.17.0, Windows x64 MSVC asset `tectonic-0.17.0-x86_64-pc-windows-msvc.zip`, SHA-256 `f61ce51f0b0ade1015b7de7ef368541c5424e9756ecbd0d7af97d6d48030845f`. Tectonic V2 documents `--only-cached` and `--untrusted`; JobPilot uses both during offline verification.

### ATS discovery

Greenhouse public GET Job Board endpoints require no authentication while application POST requires employer API credentials. Lever publishes public postings keyed by company site but applicant POST requires API credentials. Ashby publishes a public job-board endpoint keyed by board name. These constraints justify public ATS discovery plus hosted-form browser interaction later and the approved starter-board registry.

### Reference repositories

Reviewed only for ideas/risk identification: `AbhishekMandapmalvi/AutoApply`, `humancto/mr-jobs`, `ATAboukhadra/job_finder`, `speedyapply/JobSpy`. No code is copied. One inspected AutoApply Greenhouse adapter treated absence of a post-click error as success; JobPilot instead requires explicit positive confirmation and otherwise preserves `UNCERTAIN`.

## Phase 3 local AI refresh - 2026-09-11

### llama.cpp release and exact build

- upstream: https://github.com/ggml-org/llama.cpp
- license: MIT
- stable semantic release baseline: `v0.4.0`
- tested prebuilt binary build: `b10809`
- exact b10809 server documentation was inspected, not only current `master`.

The b10809 server docs explicitly expose `--list-devices`, `--device <...>` with `none = don't offload`, `--n-gpu-layers`, `--offline`, and `--no-mmproj`. JobPilot therefore forces CPU tests with `--device none` and treats runtime-reported devices as authoritative for Vulkan instead of inferring usability from Windows display-adapter names.

Pinned Windows x64 archives:

- CPU: `llama-b10809-bin-win-cpu-x64.zip`, 18,407,457 bytes, SHA-256 `9df3158ed228a641a4b127942d7f459f24c9e13f04682659d05c00c80099b6b5`;
- Vulkan: `llama-b10809-bin-win-vulkan-x64.zip`, 35,221,385 bytes, SHA-256 `97e50b3ef0cdd2cb4d5afd446a9006b3496bee6c0d0ba7083d32f36075771870`.

### Schema-constrained chat output

The exact b10809 server README documents schema-constrained chat output using `response_format` with a direct `schema` member, e.g. `{"type":"json_schema","schema":{...}}`. JobPilot uses that llama.cpp-native request shape.

This is still not a trust boundary. Issue history includes cases where some JSON-schema request paths returned a successful response without enforcing the intended schema, and reasoning modes can interact with grammar behavior. JobPilot therefore disables thinking for the controlled evaluation and performs strict local parsing plus deterministic evidence/fact checks after every response.

### Initial tested model

- repository: https://huggingface.co/ggml-org/Qwen3-4B-GGUF
- license: Apache-2.0
- pinned source revision: `2f3b082b1356a6123f7ed71e65aea340da25d53c`
- file: `Qwen3-4B-Q4_K_M.gguf`
- exact file size: 2,497,280,640 bytes
- SHA-256: `ab27b9bfa375a178d6cba48f3ad892b94b7739659dcc7aae8058ce0ffed6b328`
- controlled JobPilot context baseline: 4096 tokens
- text-only use; no multimodal projection is downloaded/loaded.

The upstream model page advertises compatibility with llama.cpp and much larger possible context than JobPilot uses. Upstream maximum context is not treated as a safe local setting. The app evaluates only a conservative context that fits its live resource budget.

A previous successful Phase 3 branch run using this CPU configuration measured approximately 5.0 GB peak process RSS and roughly 11 generated tokens/second while passing structured/factual/controlled-tailoring checks. That pre-finalization measurement is retained only as a conservative resource reference; a new combined final-tree acceptance is required.

### GPU policy

llama.cpp can enumerate several backends, but Phase 3 intentionally starts with CPU plus Vulkan to avoid silently assuming CUDA toolkit/runtime compatibility. Windows/nvidia-smi data may indicate a GPU exists, but only the checksum-verified llama.cpp runtime's `--list-devices` evidence may create an evaluable Vulkan configuration. If several devices are present, the user selects an exact ID. Every configuration must independently pass the same quality/resource suite before measured speed is compared.

### GitHub Actions maintenance

Current official `actions/checkout` and `actions/setup-python` documentation uses major version 7. The repository's older v4/v5 workflow pair emitted Node runtime deprecation warnings on current hosted Windows runners, so Phase 3 updates the acceptance workflows to v7 before the final run.

## Safety consequence

No web source, model card, benchmark, CI runner, or GPU name is allowed to decide the user's runtime configuration by assumption. The local app captures the actual machine state, requires explicit artifact download approval, verifies exact content, discovers accelerator devices from the installed runtime, measures each candidate configuration locally, and selects only among configurations that pass deterministic factual/structured/resource checks. If none fit, the outcome is “no safe tested local model”; there is no cloud fallback.
