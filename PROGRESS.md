# Progress

## Current phase

Phase 3 - Local AI and resource manager.

Status: **implementation and combined code-head acceptance complete; final record-head/PR verification pending** as of 2026-09-11. Phases 0, 1 and 2 are complete. Phase 4 has not started.

## Verified repository state at Phase 3 start

- Re-read `SPEC.md`, `ROADMAP.md`, `DECISIONS.md`, `PROGRESS.md`, and `AGENTS.md` instead of relying on memory alone.
- Verified Phase 2 finalization PR #4 merged into `main` at `71ea2265a515cbba9ff6c99b80ab1b0a34ae540e`.
- Verified Phase 2 complete: the actual LaTeX structure was privately validated; a sanitized two-page template-shape fixture passed cached-only Tectonic; the user explicitly approved all factual claims exactly as written; no personal resume/fact text is committed.
- Found existing `phase-3-local-ai-resource-manager` at `536a12555e1983d46bb80820e0154c82e658df19`, containing substantial Phase 3 work but 15 commits behind the real-resume finalization. It was not reset or discarded.
- Merged current `main` into it through internal sync PR #5, producing `7f849b0722147145ea10ef54409f253ef7e99be2`, then audited/fixed Phase 3 on staging branch `phase-3-stage`.

## Requirements preserved from the agreed product specification

- All AI inference is local. No cloud AI, hosted DB, paid API/proxy, telemetry, remote UI script, or cloud sign-in.
- No runtime/model download on launch. Downloads require explicit UI confirmation and a tested catalogue record containing source, license, revision, exact size and checksum.
- Hardware decisions use the actual running machine, not CI hardware, a model card, or a guessed GPU.
- Detect RAM/available memory, CPU capabilities, disk, GPU evidence; reserve OS/browser/JobPilot headroom.
- Small versioned quantized catalogue; newest never means automatically trusted.
- One inference operation at a time; no unnecessary vision; live resource pressure must reduce/block/cancel rather than risk memory exhaustion.
- Each CPU/GPU configuration independently passes structured-output, malicious-JD/factual, controlled-tailoring and resource checks. Speed is compared only among passing configurations.
- Replacement weights install side-by-side, must pass evaluation and later five-distinct-resume human review, and may delete previous weights only when app-managed, inside the model root, not in use, and after all gates. Metadata remains and rollback is preserved.
- Upstream metadata checks are explicit, at most weekly while open, and never download/switch automatically.
- If no safe tested local model fits, report that result; do not fall back to cloud or weaken factual quality.
- Phase 3 does not implement JD-driven tailoring, discovery, application forms, or submission.

## Current pinned local-AI catalogue

### llama.cpp

- stable semantic release baseline: `v0.4.0`;
- tested binary build: `b10809`;
- CPU Windows x64 archive: 18,407,457 bytes, SHA-256 `9df3158ed228a641a4b127942d7f459f24c9e13f04682659d05c00c80099b6b5`;
- Vulkan Windows x64 archive: 35,221,385 bytes, SHA-256 `97e50b3ef0cdd2cb4d5afd446a9006b3496bee6c0d0ba7083d32f36075771870`;
- MIT.

### Model

- `ggml-org/Qwen3-4B-GGUF`;
- pinned revision `2f3b082b1356a6123f7ed71e65aea340da25d53c`;
- `Qwen3-4B-Q4_K_M.gguf`;
- exact size 2,497,280,640 bytes;
- SHA-256 `ab27b9bfa375a178d6cba48f3ad892b94b7739659dcc7aae8058ce0ffed6b328`;
- Apache-2.0;
- JobPilot controlled context baseline 4096 tokens;
- text-only: no multimodal projection is downloaded or loaded.

## Phase 3 implementation

- `004_phase3_local_ai.sql` persists hardware evidence, revisioned runtime/model installs, per-configuration evaluation evidence, exact selected device/runtime, five-resume review gates/approvals, cleanup state and weekly update state.
- Hardware probe records local RAM/availability, CPU topology/features, app-root disk and OS display-adapter evidence; unknown VRAM stays unknown.
- Verified llama.cpp runtime is authoritative for accelerator devices via `--list-devices`. CPU uses `--device none`; Vulkan carries exact reported `VulkanN` identity, and multiple Vulkan devices require explicit selection.
- Managed downloads are atomic and verify exact bytes + SHA-256. Runtime ZIP extraction rejects path traversal and symlink entries. Runtime executable and model weights are rehashed before use.
- `ManagedPaths` canonicalizes the app root once so Windows 8.3 short-path aliases cannot create false containment failures; deletion still requires proof that a path is below the dedicated app-owned tool/model root.
- llama.cpp binds only to `127.0.0.1`, receives a random per-session API key, runs `--offline`, one slot, no UI, no multimodal projection, and is owned by the process supervisor. Concurrent shutdown is serialized so normal close/resource-pressure close cannot double-release process handles.
- One model operation is allowed at a time. Critical pressure blocks startup; constrained pressure lowers controlled context; a live watcher records pressure and closes the owned llama.cpp server if pressure becomes critical during evaluation.
- Evaluation uses deterministic schemas plus application-side validation, malicious-JD injection resistance, approved-fact-only selection and controlled resume wording. Model output never defines its own passing criteria.
- Evaluation persists backend/device/context/threads, elapsed time, generation/prompt throughput, peak process-tree RSS, pressure evidence and each pass gate.
- Selection chooses the fastest measured configuration that passed all gates and whose artifacts still verify.
- Every model revision has a unique install identity/directory, preventing replacement evaluation from overwriting the current version.
- Selecting a validated configuration creates a persisted 0/5 distinct-resume review gate. Duplicate resume keys count once. Phase 3 exposes no JS bridge method that can add approvals or activate auto-tailoring.
- Internal future replacement/rollback boundaries require the completed persisted gate, validated verified weights, not-in-use state, app ownership and safe path before activation/cleanup; retired metadata remains.
- User-triggered upstream metadata checks are capped at once every seven days and never download/activate new artifacts.
- Model/resource UI shows actual resource evidence, runtime devices, exact artifact metadata, evaluation configuration/performance and pending review gate. UI JavaScript has no network API.
- GitHub workflows now use official `actions/checkout@v7` and `actions/setup-python@v7`.

## b10809 structured-output contract: README/source mismatch

The exact pinned b10809 README and implementation disagree for `response_format.type = "json_schema"`. The README demonstrates a direct `response_format.schema`; b10809 `server-common.cpp` actually reads `response_format.json_schema.schema`.

This was verified empirically: a Windows run using the README-shaped request loaded the same verified runtime/model with normal memory pressure but produced HTTP-success responses that failed JobPilot's independent local validator. The implementation-shaped nested request is therefore pinned for b10809. This does not make llama.cpp grammar enforcement trusted: JobPilot independently parses the response and validates a fail-closed local JSON-schema subset (required fields, types, arrays/items, enums, string lengths and `additionalProperties: false`). Unsupported schema keywords are rejected rather than ignored.

## Failures found and fixed during finalization

No acceptance failure was waived:

1. A unit test labelled 1.5 GiB available on 16 GiB as “constrained”, but the explicit policy correctly treats <12% available as critical. Test data was corrected to 2.5 GiB; production thresholds were unchanged.
2. Windows `%TEMP%` supplied an 8.3 short path (`RUNNER~1`) while resolved descendants used the long name. Valid app-owned runtime installation was falsely rejected. Managed root canonicalization fixed the alias without weakening containment.
3. The b10809 README-shaped direct schema request failed real model quality/format gates. Inspection of the exact tagged parser showed it reads the nested `json_schema.schema` field. The request was corrected to the executable's parser contract while preserving the stricter application-side schema validator.
4. Concurrent critical-pressure and normal session cleanup could race. Session close is now serialized and a regression test races eight callers while requiring a single supervisor release.

Earlier audit corrections also covered revision-safe installs, persisted five-distinct-resume evidence instead of a caller boolean, explicit CPU device `none`, runtime-reported Vulkan identities, live pressure monitoring, throughput/configuration persistence, ZIP symlink rejection, tool-root deletion proof, preflight cleanup ownership, and outdated Actions majors.

## Successful combined code-head acceptance

Windows GitHub Actions run `34575604480`, code head `296c86f0327f05437eda5bfe842f8ff5f242183d`:

- current Actions v7 checkout/setup succeeded;
- Python/JavaScript syntax validation passed;
- `pytest -m "not external"` -> **101 passed, 1 intentional platform-guard skip, 2 external probes deselected in 24.87s**;
- preserved Phase 2 Tectonic 0.17.0 cache-populating + cached-only/untrusted acceptance passed;
- exact checksum-pinned llama.cpp CPU runtime/model install passed;
- Qwen3 4B CPU evaluation used device `none`, context 4096 and passed structured, factual/malicious-JD, controlled-tailoring and resource gates;
- measured generation throughput: **12.789 tokens/second**;
- evaluation elapsed: **14,002 ms**;
- peak llama.cpp process-tree RSS: **5,021,855,744 bytes**;
- live pressure remained `normal`, minimum available RAM **9,296,838,656 bytes**, critical trigger false;
- selected for future Phase 4 review with **5 approvals remaining (0/5)**;
- automatic tailoring remained **disabled**;
- source self-test passed;
- source Edge/WebView2 hidden-window smoke passed;
- PyInstaller onedir build passed;
- packaged self-test passed;
- packaged Edge/WebView2 hidden-window smoke passed;
- workflow concluded success.

This CI machine establishes a CPU compatibility baseline only. It is not the user's hardware recommendation. Local Vulkan suitability/performance can only be established when the user's installed runtime reports devices and those configurations pass the same evaluation on that machine.

## Current boundary / exact next step

Fast-forward the final record/documentation staging head into `phase-3-local-ai-resource-manager` and rerun the complete Windows Phase 3 workflow. If that exact head is green, Phase 3 can be marked complete and opened as a merge-ready PR against `main`. The PR merge-context checks must also remain green.

Phase 4 is the first later phase and remains untouched. It will implement manual-JD evidence-based tailoring, deterministic factual/LaTeX/PDF/layout validation, and the five distinct human-reviewed tailored resumes required to complete the persisted model review gate.
