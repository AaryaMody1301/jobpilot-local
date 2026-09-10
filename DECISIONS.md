# Engineering decisions

## D-001 - Windows target

Status: approved, 2026-09-10.

V1 targets Windows 10/11 x64 only. ARM64 and older Windows releases are out of scope until a later approved change. This keeps pywebview/WebView2, Playwright Chromium, Tectonic, llama.cpp, GPU backends, and packaging on one test matrix.

## D-002 - Stop semantics

Status: approved, 2026-09-10.

Stop keeps the desktop UI open. It cancels discovery, generation, and pre-submit activity immediately and prevents new scheduling. If an irreversible submission may already have started, the same confirmation window used during Close applies for at most 60 seconds. An unresolved outcome is `UNCERTAIN`.

## D-003 - Board discovery registry

Status: approved, 2026-09-10.

Phase 5 will ship a versioned starter registry of verified public Greenhouse, Lever, and Ashby board identifiers and support user additions. Board identifiers must be verified before discovery; a guessed identifier is never silently trusted.

## D-004 - Repository license

Status: approved, 2026-09-10.

Original `jobpilot-local` code is MIT licensed. External binaries, browsers, Python packages, model weights, and any future reused code retain their own licenses and notices in `THIRD_PARTY_NOTICES.md`.

## D-005 - Process ownership on Windows

Status: accepted for Phase 0 implementation.

Use a Windows Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. Child processes launched by the supervisor are created suspended, assigned to the Job Object, and only then resumed. This avoids the race where a child could spawn descendants before ownership is established. Do not enumerate and kill processes by name.

Evidence: Microsoft documents Job Objects as a unit for process management and `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` as terminating associated processes when the final job handle closes. Windows 8+ supports nested jobs, so the v1 Windows 10/11 target is compatible with nested host jobs.

## D-006 - SQLite durability and crash classification

Status: accepted for Phase 0 implementation.

SQLite is authoritative. Use WAL, foreign keys, busy timeout, explicit migrations, and transactional state transitions. On startup, pre-submit leased work may return to a safe pending state, while `SUBMITTING` or `CONFIRMING` attempts from an interrupted session become `UNCERTAIN`. There is no recovery transition from `UNCERTAIN` back to an automatic submission state.

## D-007 - Tectonic network boundary

Status: accepted for Phase 0 implementation.

Normal compilation uses Tectonic `--only-cached` and `--untrusted`. The cache directory is app-managed. Onboarding may perform an explicitly approved cache-populating compile without `--only-cached`; normal tailoring cannot silently fetch packages. Template/compiler changes require user approval if the baseline cannot be preserved.

## D-008 - Playwright browser ownership

Status: accepted for Phase 0 implementation.

Pin Playwright and its Chromium revision together. Store the Playwright-managed browser under app-owned storage with `PLAYWRIGHT_BROWSERS_PATH`. Do not assume a global browser installation. A dedicated persistent browser profile is introduced in Phase 6.

## D-009 - llama.cpp structured-output trust boundary

Status: accepted for Phase 0 implementation.

llama.cpp grammar/JSON-schema constraints improve generation reliability but are not validation. Every response is parsed and locally validated against the expected structure and later against approved fact IDs. Recent llama.cpp issue history shows that some schema request paths have regressed silently, so a successful HTTP response can never establish structural or factual validity by itself.

The exact llama.cpp production build and model are intentionally not pinned in Phase 0. They are frozen only after the Phase 3 hardware-specific evaluation, with source/tag, checksum, backend, context, and measured results recorded.

## D-010 - ATS discovery versus submission

Status: accepted for architecture.

Use documented public GET interfaces for discovery. Applicant-side submission uses visible Playwright interaction with hosted employer forms rather than employer-authenticated application APIs. Greenhouse application POST requires a Job Board API key; Lever application POST requires an API key. Browser adapters must still stop on CAPTCHA, login/verification, assessment, payment, or unsupported forms.

## D-011 - pywebview bridge concurrency

Status: accepted for Phase 1 implementation.

pywebview documents that exposed Python API functions execute in separate threads and are not thread-safe. Phase 1 therefore serializes the shared SQLite connection with an in-process re-entrant lock and opens it with `check_same_thread=False`. Lifecycle methods are serialized by the `ApplicationController` lock. This keeps one authoritative local connection without assuming JS bridge calls run on the GUI thread.

## D-012 - no dormant scheduler on launch

Status: accepted for Phase 1 implementation.

The Phase 1 sample worker is not created on application launch. It is created only by explicit Start, may remain paused while the app is open, and is joined and discarded by Stop or Close. Pause does not cancel an item that was already executing; it only prevents another item from being claimed, matching the product requirement that Pause stops scheduling new work.

## D-013 - bundled UI without a separate application backend

Status: accepted for Phase 1 implementation.

The desktop loads bundled HTML/CSS/JavaScript directly in pywebview and exposes a narrow `js_api` bridge. JobPilot does not run Flask/FastAPI or a separate application web backend for its UI. The UI contains no remote scripts, analytics, or external fetch calls.
