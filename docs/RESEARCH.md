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
- exact b10809 README **and source implementation** were inspected, not only current `master`.

The b10809 server docs expose `--list-devices`, `--device <...>` with `none = don't offload`, `--n-gpu-layers`, `--offline`, and `--no-mmproj`. JobPilot therefore forces CPU tests with `--device none` and treats runtime-reported devices as authoritative for Vulkan instead of inferring usability from Windows display-adapter names.

Pinned Windows x64 archives:

- CPU: `llama-b10809-bin-win-cpu-x64.zip`, 18,407,457 bytes, SHA-256 `9df3158ed228a641a4b127942d7f459f24c9e13f04682659d05c00c80099b6b5`;
- Vulkan: `llama-b10809-bin-win-vulkan-x64.zip`, 35,221,385 bytes, SHA-256 `97e50b3ef0cdd2cb4d5afd446a9006b3496bee6c0d0ba7083d32f36075771870`.

### Schema-constrained chat output

The exact b10809 README shows schema-constrained chat output with a direct `response_format.schema`. However, its actual `server-common.cpp` parser for `response_format.type = "json_schema"` reads `response_format.json_schema.schema`. A Windows acceptance using the README-shaped direct field returned HTTP-success responses that were missing required fields or were not JSON; the same pinned Qwen3/runtime had previously passed with the implementation-shaped nested path.

JobPilot therefore pins the b10809 wire contract to the **source implementation that the executable runs**: `response_format={"type":"json_schema","json_schema":{"name":"jobpilot_response","strict":true,"schema":{...}}}`. This upstream README/source mismatch is recorded rather than guessed away.

This parser path is still not a trust boundary. Issue history includes cases where schema request paths returned a successful response without enforcing the intended schema, and reasoning modes can interact with grammar behavior. JobPilot disables thinking for the controlled evaluation and independently validates the returned JSON against a fail-closed local schema subset before deterministic fact/evidence checks. Unsupported local schema keywords are rejected rather than silently ignored.

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

Current official `actions/checkout` and `actions/setup-python` documentation uses major version 7. The repository's older v4/v5 workflow pair emitted Node runtime deprecation warnings on current hosted Windows runners, so Phase 3 updated the acceptance workflows to v7. Final maintenance on 2026-09-18 then pinned the verified v7 commit SHAs rather than mutable tags, and Phase 9 pins upload-artifact v7 plus download-artifact v8 the same way. The Windows/Python 3.13 dependency environment is resolved by pip 26.2.1 into the committed PEP 751 `pylock.toml`. Normal CI does not re-resolve that lock: it verifies the direct pins against `pyproject.toml`, verifies locked artifact SHA-256 values, and installs the committed lock exactly. Regeneration is an explicit dependency-maintenance action using `scripts/update_dependency_lock.ps1`; this avoids routine CI changing merely because an unconstrained transitive release appeared upstream. Because `proxy_tools` is distributed as an sdist, isolated build resolution is separately constrained by `requirements-build.in` to setuptools 84.0.0 and wheel 0.48.0.

## Safety consequence

No web source, model card, benchmark, CI runner, or GPU name is allowed to decide the user's runtime configuration by assumption. The local app captures the actual machine state, requires explicit artifact download approval, verifies exact content, discovers accelerator devices from the installed runtime, measures each candidate configuration locally, and selects only among configurations that pass deterministic factual/structured/resource checks. If none fit, the outcome is “no safe tested local model”; there is no cloud fallback.


## Local-AI maintenance evaluation - 2026-09-21

Upstream llama.cpp currently marks semantic release `v0.4.1` as latest. The version-bump build is `b10964`; later `b109xx` builds are rolling pre-releases and are not used as the maintenance target.

Exact b10964 Windows x64 artifacts from the official GitHub release metadata:

- CPU: `llama-b10964-bin-win-cpu-x64.zip`, 18,427,629 bytes, SHA-256 `917f39c076402c421224824607397af20f53625a60defc20e8dd22446bf4c5d7`;
- Vulkan: `llama-b10964-bin-win-vulkan-x64.zip`, 31,674,542 bytes, SHA-256 `1ee3ad952f4ba71f438bd6d7bebef19e1c7af04adcaa35d08b4ddabb27d4c642`.

The exact b10964 server source still parses `response_format.type = "json_schema"` from `response_format.json_schema.schema`, and its documented/implemented runtime options still include `--list-devices`, `--device`, `--offline`, `--no-mmproj`, and `--no-ui`. The existing JobPilot runtime and independent local schema/factual validators therefore remain applicable to this candidate.

The existing Qwen3 4B GGUF stays pinned for this runtime-only comparison. Qwen's official Qwen3 4B GGUF remains a text-generation model with Q4_K_M available. The newer Qwen3.5-4B line is published as an image-text model, so it is not a drop-in replacement for JobPilot's text-only/no-mmproj trust boundary and is out of scope for this maintenance slice.

b10964 is catalogued as a maintenance candidate, not a baseline replacement. CI evaluates it with the same structured/factual/tailoring/resource suite after the baseline acceptance. Passing CI does not auto-select it; local explicit selection plus the existing five-distinct-resume gate are still required before automatic tailoring could move to that runtime.
