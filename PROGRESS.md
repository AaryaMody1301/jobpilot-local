# Progress

## Current phase

Phase 3 - Local AI and resource manager.

Status: **complete; ready for pull-request merge verification** as of 2026-09-11. Phases 0, 1 and 2 are complete. Phase 4 has not started.

## Verified repository state at Phase 3 start

- Re-read `SPEC.md`, `ROADMAP.md`, `DECISIONS.md`, `PROGRESS.md`, and `AGENTS.md` rather than relying on memory alone.
- Verified Phase 2 finalization PR #4 merged into `main` at `71ea2265a515cbba9ff6c99b80ab1b0a34ae540e`.
- Verified Phase 2 complete: the actual LaTeX structure was privately validated; a sanitized two-page template-shape fixture passed cached-only Tectonic; the user explicitly approved all factual claims exactly as written; no personal resume/fact text is committed.
- Found pre-existing `phase-3-local-ai-resource-manager` at `536a12555e1983d46bb80820e0154c82e658df19`, containing substantial Phase 3 work but 15 commits behind the real-resume finalization. It was preserved, not reset.
- Merged current `main` into it through internal sync PR #5, producing `7f849b0722147145ea10ef54409f253ef7e99be2`, then audited/fixed the Phase 3 work on `phase-3-stage` before advancing the real branch.

## Requirements preserved from the agreed product specification

- All AI inference is local. No cloud AI, hosted DB, paid API/proxy, telemetry, remote UI script, or cloud sign-in.
- No runtime/model download on launch. Downloads require explicit UI confirmation and catalogue source/license/revision/exact-size/checksum metadata.
- Hardware decisions use the actual running machine, not CI hardware, a model card, or a guessed GPU.
- Detect RAM/available memory, CPU capabilities, disk and GPU evidence; reserve OS/browser/JobPilot headroom.
- Keep a small versioned quantized catalogue; newest never means automatically trusted.
- One inference operation at a time; no unnecessary vision; live pressure must reduce/block/cancel instead of risking memory exhaustion.
- Every CPU/GPU configuration independently passes structured-output, malicious-JD/factual, controlled-tailoring and resource checks. Speed is compared only among passing configurations.
- Replacement weights install side-by-side, require evaluation plus the later five-distinct-resume review gate, and may delete previous weights only when app-managed, inside the model root, not in use and after all gates. Metadata/rollback are preserved.
- Upstream metadata checks are explicit, at most weekly while open, and never download/switch automatically.
- If no tested local candidate fits safely, report that result; do not fall back to cloud or weaken factual quality.
- Phase 3 does not implement JD-driven tailoring, discovery, application forms, or submission.

## Pinned Phase 3 catalogue

### llama.cpp

- stable release baseline `v0.4.0`, tested binary build `b10809`, MIT;
- CPU Windows x64 archive: 18,407,457 bytes, SHA-256 `9df3158ed228a641a4b127942d7f459f24c9e13f04682659d05c00c80099b6b5`;
- Vulkan Windows x64 archive: 35,221,385 bytes, SHA-256 `97e50b3ef0cdd2cb4d5afd446a9006b3496bee6c0d0ba7083d32f36075771870`.

### Model

- `ggml-org/Qwen3-4B-GGUF`, revision `2f3b082b1356a6123f7ed71e65aea340da25d53c`;
- `Qwen3-4B-Q4_K_M.gguf`, 2,497,280,640 bytes;
- SHA-256 `ab27b9bfa375a178d6cba48f3ad892b94b7739659dcc7aae8058ce0ffed6b328`;
- Apache-2.0, controlled JobPilot context 4096 tokens, text-only with no multimodal projection.

## Phase 3 implementation completed

- `004_phase3_local_ai.sql` persists hardware evidence, revisioned runtime/model installs, per-configuration evaluations, exact selected device/runtime, five-resume review gates/approvals, cleanup state and weekly update state.
- Hardware probe records RAM/availability, CPU topology/features, app-root disk and conservative OS display-adapter evidence; unknown VRAM stays unknown.
- Verified llama.cpp `--list-devices` is authoritative for accelerators. CPU uses `--device none`; Vulkan carries an exact reported `VulkanN` ID and multiple devices require explicit selection.
- Managed downloads are atomic and verify exact bytes plus SHA-256. Runtime ZIP extraction rejects traversal and symlink entries. Runtime executable/model weights are rehashed before use.
- `ManagedPaths` canonicalizes the app root once so Windows 8.3 aliases cannot cause false containment failures; deletion still requires proof that the target is below the dedicated app-owned tool/model root.
- llama.cpp binds only to `127.0.0.1`, receives a random per-session API key, runs `--offline`, one slot, no UI and no multimodal projection, and is owned by the process supervisor. Concurrent shutdown is serialized.
- One model operation is allowed at a time. Critical pressure blocks startup; constrained pressure lowers controlled context; a live watcher records pressure and closes the owned server if pressure becomes critical during evaluation.
- Evaluation uses deterministic schemas plus application-side validation, malicious-JD injection resistance, approved-fact-only selection and controlled resume wording. Model output never defines its own pass criteria.
- Evaluation persists backend/device/context/threads, elapsed time, generation/prompt throughput, peak process-tree RSS, pressure evidence and each pass gate.
- Selection chooses the fastest measured configuration that passed all gates and whose artifacts still verify.
- Every model revision has a unique install identity/directory so replacement validation cannot overwrite accepted weights.
- Selection creates a persisted 0/5 distinct-resume review gate. Duplicate resume keys count once. Phase 3 exposes no JS bridge method for approvals or auto-tailoring activation.
- Internal future replacement/rollback boundaries require the completed persisted gate, validated verified weights, not-in-use state, app ownership and safe path before cleanup; retired metadata remains.
- User-triggered upstream metadata checks are capped at once every seven days and never download/activate new artifacts.
- Model/resource UI shows actual resource evidence, exact artifact metadata, runtime devices, evaluation configuration/performance and pending review gate. UI JavaScript has no network API.
- GitHub workflows use official `actions/checkout@v7` and `actions/setup-python@v7`.

## b10809 structured-output contract: README/source mismatch

The exact pinned b10809 README and implementation disagree for `response_format.type = "json_schema"`. The README demonstrates direct `response_format.schema`; b10809 `server-common.cpp` reads `response_format.json_schema.schema`.

A Windows run using the README-shaped request loaded the same verified runtime/model with normal memory pressure but returned HTTP-success outputs that failed JobPilot's independent local validator. JobPilot therefore pins the implementation-shaped nested path for b10809. llama.cpp grammar remains only a generation aid: returned content is independently validated using a fail-closed local JSON-schema subset covering required fields, types, arrays/items, enums, string lengths and `additionalProperties: false`; unsupported local keywords are rejected.

## Failures found and fixed during finalization

No acceptance failure was waived:

1. A test called 1.5 GiB available on 16 GiB “constrained” although the explicit <12% policy correctly classifies it critical. Test data was corrected to 2.5 GiB; production thresholds were unchanged.
2. Windows `%TEMP%` used an 8.3 short path (`RUNNER~1`) while resolved descendants used the long name. Canonical root handling fixed the alias without weakening containment.
3. The b10809 README-shaped schema request failed real quality/format gates. Exact tagged parser source showed it reads nested `json_schema.schema`; the request was corrected while retaining stricter application-side validation.
4. Critical-pressure cleanup and normal session cleanup could race. Runtime close is serialized and a regression test races eight callers while requiring one supervisor release.
5. Earlier audit fixes covered revision-safe installs, persisted five-distinct-resume evidence instead of a caller boolean, explicit CPU device `none`, runtime-reported Vulkan identities, live pressure monitoring, throughput/configuration persistence, ZIP symlink rejection, tool-root deletion proof, cleanup preflight ownership, and obsolete Actions majors.

## Windows acceptance evidence

### Successful code-head run

Run `34575604480`, head `296c86f0327f05437eda5bfe842f8ff5f242183d`:

- `pytest -m "not external"`: **101 passed, 1 intentional platform-guard skip, 2 external probes deselected in 24.87s**;
- preserved Phase 2 Tectonic network-to-cache-to-`--only-cached --untrusted` acceptance passed;
- exact checksum-pinned llama.cpp CPU runtime and Qwen3 weight install passed;
- Qwen3 CPU evaluation at context 4096/device `none` passed structured, factual/malicious-JD, controlled-tailoring and resource gates;
- generation throughput **12.789 tokens/s**, evaluation **14,002 ms**, peak process-tree RSS **5,021,855,744 bytes**;
- live pressure normal, minimum available RAM **9,296,838,656 bytes**, critical trigger false;
- selected for future Phase 4 review with **0/5 approvals**, auto-tailoring disabled;
- source/package self-tests, hidden Edge/WebView2 smokes and PyInstaller onedir build all passed.

### Successful exact record-head run

Run `34576262983`, head `881781b2f8a768d7e23dc971711c7cf04477a61d` repeated the complete Phase 3 workflow successfully: dependency/browser setup, syntax, full non-external suite, Phase 2 Tectonic acceptance, real pinned llama.cpp/Qwen3 model acceptance, source self-test/WebView2 smoke, PyInstaller onedir build, packaged self-test and packaged WebView2 smoke all concluded `success`.

The GitHub-hosted Windows machine establishes a CPU compatibility baseline only. It is not the user's hardware recommendation. Local Vulkan suitability/performance must be established from the user's own runtime-reported devices and the same evaluation suite.

## Current boundary / exact next step

Phase 3 implementation is complete. Push this completion-record head to `phase-3-local-ai-resource-manager`, open the Phase 3 pull request to `main`, and require the PR merge-context Phase 0-3 checks to remain green. If they pass, the PR is ready for the user to merge.

Do not start Phase 4 in this phase. After Phase 3 is merged and the user asks to continue, Phase 4 is the first incomplete phase: manual-JD evidence-based tailoring, deterministic factual/LaTeX/PDF/layout validation, and the five distinct human-reviewed tailored resumes required to complete the persisted model review gate.
