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

Status: accepted for Phase 0 implementation and tightened in Phase 3.

llama.cpp grammar/JSON-schema constraints improve generation reliability but are not validation. Every response is parsed and locally validated against the expected structure and later against approved fact IDs. Recent llama.cpp issue history shows that some schema request paths have regressed silently, so a successful HTTP response can never establish structural or factual validity by itself.

Phase 3 pins llama.cpp build `b10809`. Its own server documentation uses the llama.cpp-native chat shape `response_format={"type":"json_schema","schema":...}`. JobPilot uses that exact contract instead of an OpenAI-nested wrapper, disables thinking for the controlled evaluation, and still applies strict local structural/factual checks after generation.

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

## D-014 - immutable resume and evidence provenance

Status: accepted for Phase 2 implementation.

The original user-selected master `.tex` is never edited in place. JobPilot copies it byte-for-byte into a versioned app-owned directory, records SHA-256/size/original name, and verifies the copy before registering it. Re-importing identical bytes reuses that source version; changed bytes create a new source version while older evidence remains retained. Every candidate fact and editable region points to the registered source and a source locator/hash.

A fact cannot become approved if its backing app-owned source no longer matches its recorded SHA-256. Editing a fact creates a new candidate version under the same stable fact ID rather than rewriting approved history.

## D-015 - explicit Tectonic installation and two-step offline gate

Status: accepted for Phase 2 implementation.

Phase 2 pins the app-managed Windows x64 Tectonic binary to version 0.17.0 and verifies the official release archive by exact byte size and SHA-256 before installing it under JobPilot's managed tool root. Installation occurs only after an explicit UI action.

Package support files may be fetched only during an explicitly approved cache-populating baseline compile. Onboarding is not ready until the same master source later compiles successfully with `--only-cached --untrusted`. A network-enabled compile therefore cannot by itself satisfy the resume baseline gate.

## D-016 - native source selection and explicit mapping/fact review

Status: accepted for Phase 2 implementation.

The JavaScript UI does not receive a generic filesystem-import method. Master/supporting paths enter the controller only from pywebview's native file dialog. Candidate editable regions start disabled and must be selected by the user; any later region change invalidates mapping confirmation. Automatically extracted resume statements start as candidate facts and every candidate must be approved, corrected, or rejected before onboarding can be ready.

## D-017 - PDF extraction is validation evidence, not factual truth

Status: accepted for Phase 2 implementation.

pypdf records baseline page geometry and extracted-text hashes and checks that a compiled resume contains usable text. The immutable LaTeX source and approved facts remain authoritative. PDF extraction order is not assumed to reproduce semantic reading order, so extracted PDF text cannot silently create or approve facts.

## D-018 - real-template protected facts and approval privacy

Status: approved/completed, 2026-09-11.

Testing the user's actual LaTeX template showed that authoritative facts exist outside editable bullet regions. Phase 2 therefore extracts protected non-bullet facts such as `\role` title/date/employer/location fields and factual section text into the same candidate/approval system. These values are protected evidence, not automatically editable wording. Historical facts from inactive master resume versions remain retained for provenance but do not block readiness for the active master.

The user explicitly approved all factual claims in the supplied resume exactly as written on 2026-09-11. That approval closes the Phase 2 fact-review gate. The repository records the approval event and validation outcome only; it does not reproduce or commit the private resume source or personal fact values. Future runtime imports must still create source-linked fact records with the normal integrity/versioning rules rather than relying on this repository note as a substitute for the private local fact bank.

## D-019 - Phase 3 tested local-AI catalogue

Status: accepted for Phase 3 implementation, 2026-09-11.

The initial tested catalogue stays deliberately small. It pins llama.cpp stable release `v0.4.0` / binary build `b10809` with checksum-addressed Windows x64 CPU and Vulkan archives, plus `ggml-org/Qwen3-4B-GGUF` revision `2f3b082b1356a6123f7ed71e65aea340da25d53c`, file `Qwen3-4B-Q4_K_M.gguf`, exact SHA-256 `ab27b9bfa375a178d6cba48f3ad892b94b7739659dcc7aae8058ce0ffed6b328`, exact size 2,497,280,640 bytes, Apache-2.0. Model weights are never committed or auto-downloaded.

A newer upstream build/revision is metadata only until it receives a new catalogue identity, checksum/license review, local evaluation, and later five-resume review. Newest is not assumed best.

## D-020 - runtime-reported devices are authoritative

Status: accepted for Phase 3 implementation, 2026-09-11.

OS probes are evidence about display adapters, not proof that llama.cpp can use them. The installed checksum-verified llama.cpp runtime must report accelerator IDs through `--list-devices`. CPU evaluation is forced with `--device none`; a Vulkan run carries an exact reported `VulkanN` ID. Multiple Vulkan devices require explicit selection. Each CPU/GPU configuration passes the same evaluation independently before speed can be compared.

CUDA is not added to the initial catalogue because that would introduce additional runtime/toolkit compatibility assumptions. Vulkan is the first optional accelerator backend; a later backend can be added only with its own pinned/tested artefacts.

## D-021 - evidence-backed resource budgets and one inference at a time

Status: accepted for Phase 3 implementation, 2026-09-11.

Hardware detection records RAM/available memory, CPU topology/features, app-root disk capacity, conservative OS/browser/JobPilot reserves, OS GPU evidence, and runtime device evidence. Unknown VRAM remains unknown. A prior successful Windows CPU acceptance measured approximately 5.0 GB peak llama.cpp process RSS for the pinned Qwen3 4B candidate; that measurement is a conservative reference floor, not a universal machine requirement.

Only one model operation/server is allowed at a time. Critical memory pressure blocks startup. Constrained pressure reduces the controlled context. A live watcher continues during evaluation and closes the app-owned llama.cpp session if pressure becomes critical. No cloud fallback or quality weakening is allowed when the machine cannot safely run the tested catalogue.

## D-022 - revisioned weights and persisted five-resume replacement gate

Status: accepted for Phase 3 implementation, 2026-09-11.

Every model revision has a distinct install ID and app-owned directory, so validating a replacement cannot overwrite the currently accepted weights. Selection records the fastest configuration that passed the same quality/resource suite. Automatic tailoring remains disabled in Phase 3.

The future activation gate is persisted in SQLite and requires approvals for five distinct tailored resumes for the exact selected model/configuration. It cannot be satisfied by a caller-supplied boolean. Changing the selected configuration invalidates existing review evidence. Replacement cleanup is preflighted before activation, refuses shared/non-app-managed or in-use weights, remains beneath the model root, keeps retired metadata, and supports rollback to a still-validated previous model.

## D-023 - model update checks are explicit and non-authoritative

Status: accepted for Phase 3 implementation, 2026-09-11.

Upstream runtime/model metadata checks occur only after an explicit UI action and at most once every seven days while the application is open. A check may report a newer version/revision but never downloads or switches to it. Any new binary/model still requires explicit download approval, checksum/license metadata, evaluation, and the later five-resume review gate.

## D-024 - current official GitHub Actions majors

Status: accepted for Phase 3 maintenance, 2026-09-11.

The acceptance workflows use official `actions/checkout@v7` and `actions/setup-python@v7`. The prior v4/v5 pair was still functional but emitted Node runtime deprecation warnings on current hosted runners. This maintenance change does not alter application behavior.
