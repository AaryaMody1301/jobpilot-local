# Progress

## Current phase

Phase 3 - Local AI and resource manager.

Status: **in progress; implementation audited and staged, final combined Windows acceptance pending** as of 2026-09-11. Phases 0, 1 and 2 are complete. Phase 4 has not started.

## Verified repository state at Phase 3 start

- Re-read `SPEC.md`, `ROADMAP.md`, `DECISIONS.md`, `PROGRESS.md`, and `AGENTS.md` instead of relying on memory alone.
- Verified Phase 2 finalization PR #4 merged into `main` at `71ea2265a515cbba9ff6c99b80ab1b0a34ae540e`.
- Verified Phase 2 is `[x] complete`: the user's actual LaTeX structure was privately validated, a sanitized two-page template-shape fixture passed cached-only Tectonic on Windows, and the user explicitly approved all factual claims in the supplied resume exactly as written. Personal resume/fact text remains outside Git.
- Found an existing `phase-3-local-ai-resource-manager` branch at `536a12555e1983d46bb80820e0154c82e658df19`. It contained substantial Phase 3 work but was 15 commits behind the Phase 2 finalization. It was not reset or discarded.
- Merged current `main` into that Phase 3 branch through internal sync PR #5, producing `7f849b0722147145ea10ef54409f253ef7e99be2`. This preserves both histories and makes the Phase 3 work include every Phase 2 finalization fix.
- Continued audit/fixes on staging branch `phase-3-stage` so the large external model acceptance is triggered only after a cohesive review.

## Recalled requirements that govern Phase 3

- Everything remains local; no cloud AI, hosted database, paid API/proxy, telemetry, remote UI script, or cloud sign-in.
- Model/runtime download requires an explicit user action and exact source/license/checksum metadata.
- Hardware recommendation must be based on the actual running machine; CI hardware must never be presented as the user's GPU/RAM profile.
- Detect RAM, available memory, CPU capabilities, disk, GPU evidence, and reserve resources for Windows/browser/JobPilot.
- Initial catalogue is small, versioned, quantized and tested. Newest does not automatically mean trusted or selected.
- One inference operation at a time. No unnecessary vision. Resource pressure must reduce/block/cancel rather than cause unsafe memory exhaustion.
- Every usable configuration must pass structured-output, factual/malicious-JD and controlled-tailoring quality checks plus resource checks; speed is measured only among passing configurations.
- Switching is allowed only to installed/validated weights. A replacement repeats the later five-distinct-resume human review gate.
- Old weights may be deleted only if JobPilot proves they are app-managed, inside the model root, not in use, and a replacement has satisfied all gates; metadata remains.
- Update checks may occur at most weekly while open, never download/switch automatically, and still require approval/evaluation.
- If no local candidate fits safely, report that result. Never use cloud inference or weaken factual requirements.
- Phase 3 must not start JD-driven tailoring, discovery, form filling, or employer submission.

## Current official dependency/model verification

Research was rechecked on 2026-09-11 against project-owned/official sources before freezing Phase 3:

- llama.cpp stable release baseline: `v0.4.0`; tested Windows binary build `b10809`.
- b10809 server docs expose `--list-devices`, explicit `--device`, `--offline`, `--no-mmproj`, and schema-constrained `response_format`. `--device none` is the explicit no-offload CPU path.
- llama.cpp b10809 chat schema shape is `response_format={"type":"json_schema","schema":...}`. JobPilot uses that native form and independently parses/validates the returned JSON.
- Runtime catalogue pins b10809 Windows x64 CPU and Vulkan archives by exact byte count and SHA-256.
- Model catalogue pins `ggml-org/Qwen3-4B-GGUF`, revision `2f3b082b1356a6123f7ed71e65aea340da25d53c`, `Qwen3-4B-Q4_K_M.gguf`, exact size 2,497,280,640 bytes, SHA-256 `ab27b9bfa375a178d6cba48f3ad892b94b7739659dcc7aae8058ce0ffed6b328`, Apache-2.0.
- GitHub Actions acceptance was updated from deprecated Node-runtime action majors to official `actions/checkout@v7` and `actions/setup-python@v7`.

## Pre-existing Phase 3 evidence retained

Before the Phase 2 finalization merge, the old Phase 3 branch already had a successful Windows run `34478348579` / job `102874581087` using the pinned CPU runtime and Qwen3 4B Q4_K_M. It measured approximately 5,016,252,416 bytes peak RSS and passed its structured, factual/malicious-JD, controlled-tailoring and resource checks while leaving automatic tailoring disabled. Generation in the log was roughly 11 tokens/second at the controlled 4096-token context.

That run is useful empirical input for conservative RAM policy, but **is not Phase 3 completion evidence** because it predates the merged real-resume finalization and the safety fixes below.

## Phase 3 audit findings fixed before final acceptance

The existing branch was not accepted as-is. The audit found and corrected these material gaps:

1. Acceptance documentation named the wrong model size even though the actual script used Qwen3 4B.
2. Model revisions shared one logical install identity/path, so a future revision could overwrite old weights before replacement review.
3. Replacement activation accepted a caller-supplied review boolean rather than persisted evidence of five distinct approved resumes.
4. CPU mode relied on `-ngl 0`; b10809 docs explicitly support `--device none`, which is now required to prove CPU-only evaluation.
5. OS GPU detection was not enough to bind inference to an actual llama.cpp device. The runtime now enumerates `--list-devices`, and Vulkan evaluation requires an exact discovered `VulkanN` ID.
6. Resource pressure was checked before/after inference but not continuously. A live watcher now records pressure and terminates the owned local server if memory becomes critical.
7. Evaluation did not persist enough performance/configuration evidence to choose the fastest passing CPU/GPU configuration. It now stores exact device, context, throughput, elapsed time, peak RSS and pressure evidence.
8. llama.cpp response schema used an OpenAI-nested wrapper. b10809's own server docs use direct `response_format.schema`; the request was corrected while retaining strict application-side validation.
9. ZIP extraction allowed a symlink entry; runtime extraction now rejects both traversal and symlink members.
10. Destructive tool cleanup lacked the same explicit managed-root proof used for model cleanup. Managed tool/model deletion boundaries are now separate and enforced.
11. Replacement cleanup could discover an ownership problem after activation. Ownership/in-use/path checks now occur before changing the active model state.
12. Old GitHub Actions majors emitted Node runtime deprecation warnings; acceptance workflows now use current official majors.

## Phase 3 implementation staged

- Migration `004_phase3_local_ai.sql` stores hardware snapshots, runtime/model installs, per-configuration evaluations, selected runtime/device, persisted five-resume review gates/approvals, cleanup state and weekly update state.
- Qwen model revisions have unique install IDs and directories based on pinned source revision, so evaluation is side-by-side rather than in-place replacement.
- Download code is atomic and checks exact expected byte count plus SHA-256. Runtime ZIP extraction rejects traversal and symbolic links.
- Runtime executable integrity is rechecked before device enumeration/inference; model weights are rehashed before use.
- Hardware probe records current RAM, available RAM, CPU topology/features, disk, OS GPU evidence and conservative reserves. Unknown VRAM remains unknown.
- llama.cpp `--list-devices` output is parsed into exact runtime device IDs. CPU forces `none`; Vulkan never guesses among multiple devices.
- The server binds `127.0.0.1`, uses a random per-session API key, runs `--offline`, one slot, `--no-ui`, `--no-mmproj`, and is owned by the Windows process supervisor.
- One model operation is allowed at a time. Critical pressure blocks startup; constrained pressure reduces controlled context; live critical pressure closes the owned server.
- Controlled evaluation includes deterministic schema adherence, malicious JD injection resistance, evidence-only factual selection and controlled resume-bullet wording. Model output never sets its own pass criteria.
- Per-configuration evidence includes backend/device/context/threads, elapsed time, generation and prompt throughput when available, peak process-tree RSS, live pressure, each quality gate and overall result.
- Selection chooses the fastest measured configuration among those that passed every gate and whose model/runtime files still verify.
- Phase 3 selection creates a persisted 0/5 distinct-resume review gate. There is no Phase 3 JS bridge method for adding approvals or activating automatic tailoring.
- Future activation/cleanup/rollback primitives are implemented as guarded internal boundaries for Phase 4: five distinct persisted approvals required; no caller boolean; no shared/non-app-managed or in-use deletion; all deletion remains beneath the model root; retired metadata stays in SQLite.
- User-triggered upstream metadata check is capped at once every seven days and never downloads or activates a new version.
- UI displays resource evidence, exact download size/license/revision/checksum, runtime devices, per-configuration evaluation results and the pending 0/5 review gate. JavaScript still has no network API.

## Tests staged before final Windows run

Unit/integration coverage now includes:

- Phase 2→3 migration preservation and review-gate tables;
- no download or auto-inference on snapshot/launch;
- explicit weekly update interval;
- exclusive one-operation lock;
- CPU device `none` and explicit/multiple Vulkan device behavior;
- conservative no-candidate result instead of cloud/unsafe fallback;
- exact catalogue size/hash/revision identity;
- pressure thresholds and live critical callback;
- atomic checksum/size downloads and cancellation;
- ZIP traversal and symlink rejection;
- revision-specific installs;
- runtime/model integrity rechecks;
- fastest passing configuration selection;
- duplicate resume review approval counting only once;
- refusal to activate before five distinct approvals;
- refusal to delete shared/non-app-managed weights;
- safe old-revision cleanup after the complete persisted gate;
- rollback to previous validated weights;
- llama.cpp-native schema request and strict local validation;
- Phase 3 UI no-network/explicit-download/device/review-gate controls;
- previous Phase 0/1/2 lifecycle, Windows Job Object, resume/fact and Tectonic tests.

## Current boundary / exact next step

Fast-forward the audited staging head into `phase-3-local-ai-resource-manager` and run its Windows Phase 3 workflow. The final acceptance must include syntax/tests, preserved Phase 2 cached-only Tectonic acceptance, a real checksum-pinned CPU llama.cpp/Qwen3 4B evaluation, source WebView2 smoke, PyInstaller onedir build, packaged self-test and packaged WebView2 smoke. If any check fails, fix the implementation rather than weakening the gate.

Only after that combined tree passes may `ROADMAP.md` be changed from `[~]` to `[x]` and a Phase 3 PR to `main` be marked ready. Phase 4 must remain untouched.
