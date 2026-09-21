# Progress

## Current repository state

JobPilot's technical product implementation is complete through verified Windows distribution and the explicitly user-authorized measured-pilot write path.

Recent cleanup:

- PR #21 merged at `1ee3dfbc0a32a9afb720ec0564c9be7083055d1e`: production runtime entrypoint/bridge cleanup and removal of development sample lifecycle state.
- PR #23 merged at `02836dded7fc7211738405d6acd93cd039cc2d25`: final production UI consolidation, current product copy, active-view rendering, accessibility fixes, and final-shell Playwright coverage.
- PR #24 merged at `3c9122ab24be2a6a2adc8f23db7d698f5071ecbc`: durable CI/acceptance/release workflows and deletion of phase-era repository scaffolding.

## Current CI design

PR #24 replaced ten phase workflows with:

- `Windows CI / windows-ci`;
- `Windows Acceptance / windows-acceptance`;
- `Windows Release / windows-release` plus release publishing on `main`.

The deterministic suite runs once per PR rather than once per historical phase. Full Windows acceptance keeps the real Tectonic, local-model/tailoring, controlled application, provider, orchestration, backup/restore, frozen desktop, and clean install/upgrade boundaries.


## Job/application workspace

PR #25 merged the job/application workspace with migration `010_job_application_workspace.sql`; user-workspace metadata remains separate from application state transitions.

- Jobs can be searched/filtered and inspected from their saved local snapshot, including the JD, evidence match, compensation and deadline metadata when available.
- Lever/Ashby compensation is captured from their public board payloads. Greenhouse pay/deadline metadata is refreshed only on explicit user request from the public per-job endpoint.
- Applications can be searched/filtered and inspected with the exact recorded tailoring run, tailored PDF hash/preview, immutable package ID/manifest hash, journal timestamps, saved JD and URLs.
- Follow-up date, notes and next action are local metadata only; editing is allowed while the session is idle and does not alter the application safety state machine.

## Dependency and model baseline

- Python 3.13.15
- pip 26.2.1
- Playwright 1.63.0
- pypdf 6.19.0
- setuptools 84.0.0
- PyInstaller 6.22.3
- pytest 9.1.1
- pip-audit 2.10.1
- psutil 7.2.2
- pywebview 6.2.1

The committed Windows x64 / CPython 3.13 dependency graph is hash-addressed in `pylock.toml`. Isolated sdist builds are constrained by `requirements-build.in`.

The validated local-AI baseline remains llama.cpp v0.4.0 / b10809 with the accepted Qwen3 4B GGUF revision.

Maintenance PR 5 evaluates stable llama.cpp v0.4.1 / b10964 as a side-by-side CPU/Vulkan candidate. The exact GitHub Windows artifacts are pinned by size and SHA-256, the existing controlled quality/resource suite must pass, and the selected baseline must not auto-switch. No model revision is changed.

## Active private gates

Two deliberately non-synthetic gates remain:

- five distinct real tailored resumes must be explicitly approved in the user's private local JobPilot database under one current validation context;
- the measured real-world pilot must be run from private local data using individually armed eligible applications.

The visible 50/day objective remains a target, not a capability claim.

## Repository administration boundary

Branch protection/rulesets and publisher signing require repository-administrator/signing credentials and cannot be fabricated in source control.

The desired required PR checks are `windows-ci` and `windows-acceptance`. See `docs/REPOSITORY_GOVERNANCE.md`.
