# Phase 0 feasibility research

Research date: 2026-09-10. Official documentation and project-owned sources are preferred. Advertised behavior from reference automation repositories is not accepted without tests.

## Python and Python packages

- Python 3.13.15 (2026-08-05): https://www.python.org/downloads/release/python-31315/
- pywebview 6.2.1: https://pypi.org/project/pywebview/
- Playwright Python 1.62.0: https://pypi.org/project/playwright/
- psutil 7.2.2: https://pypi.org/project/psutil/
- pypdf 6.18.0: https://pypi.org/project/pypdf/
- pytest 9.1.1: https://pypi.org/project/pytest/
- PyInstaller 6.22.2: https://pypi.org/project/pyinstaller/

Pywebview documents a blocking `window.events.closing` event whose handler can cancel closing. Phase 1 will use this to show the bounded submission-confirmation close state rather than relying on a background service:
https://pywebview.flowrl.com/api/

Playwright documents that each Playwright release requires matching browser binaries and supports an explicit `PLAYWRIGHT_BROWSERS_PATH`. JobPilot therefore pins Playwright with its Chromium revision and stores browser binaries under app-managed data:
https://playwright.dev/python/docs/browsers

## Windows process ownership

Microsoft documents Job Objects as a mechanism for managing groups of processes as a unit. `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` terminates associated processes when the final job handle closes, and Windows 8+ supports nested jobs:
https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects

Phase 0 creates owned child processes suspended, assigns them to the Job Object, then resumes them. This prevents a newly launched process from creating descendants before containment is established.

## Tectonic

Current release reviewed: Tectonic 0.17.0, published 2026-07-27.

Windows x64 MSVC asset:
`tectonic-0.17.0-x86_64-pc-windows-msvc.zip`
SHA-256: `f61ce51f0b0ade1015b7de7ef368541c5424e9756ecbd0d7af97d6d48030845f`

Release: https://github.com/tectonic-typesetting/tectonic/releases/tag/tectonic%400.17.0
License: MIT, with additional licenses applying to derived/bundled TeX ecosystem elements.

Tectonic's V2 compile command documents `--only-cached` and `--untrusted`. JobPilot uses both during normal compilation. Package-cache population is an explicit onboarding operation:
https://tectonic-typesetting.github.io/book/latest/v2cli/compile.html

## llama.cpp

Source: https://github.com/ggml-org/llama.cpp
License: MIT.

The current server supports CPU/GPU quantized inference, local HTTP endpoints, and schema-constrained JSON generation. The current source converts `json_schema` constraints to grammar. However, recent issue history includes a report where a `response_format: json_schema` path returned success without enforcing the schema. For this reason, JobPilot always performs strict local response validation in addition to the generation constraint.

Server docs: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
Grammar/schema docs: https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md
Relevant regression report: https://github.com/ggml-org/llama.cpp/issues/24097

llama.cpp has very frequent build releases/nightlies. Phase 0 intentionally does not declare a production binary/model merely because it is newest. Phase 3 will freeze the exact source/tag/checksum/backend only after hardware-specific compatibility, memory, speed, structured-output, and factual-tailoring evaluation.

## ATS discovery

Greenhouse public GET Job Board endpoints require no authentication. Job retrieval can include application questions, while application POST requires a Job Board API key:
https://docs.greenhouse.io/job-board.html

Lever publishes jobs under a company site name. Its Postings API does not offer global full-text job search, and application POST requires an API key. JobPilot uses public postings for discovery and hosted forms for applicant-side automation:
https://github.com/lever/postings-api

Ashby provides a public job-board endpoint keyed by job-board name:
https://developers.ashbyhq.com/docs/public-job-posting-api

These per-company identifiers justify the approved versioned starter registry plus user-added verified boards.

## Reference repositories

Reviewed only for ideas and risk identification:

- https://github.com/AbhishekMandapmalvi/AutoApply
- https://github.com/humancto/mr-jobs
- https://github.com/ATAboukhadra/job_finder
- https://github.com/speedyapply/JobSpy

No code from these projects is copied in Phase 0. One inspected AutoApply Greenhouse adapter treats absence of a post-click error as success; that is insufficient for JobPilot, which requires explicit positive confirmation and otherwise stores `UNCERTAIN`.
