# Phase 3 acceptance

Phase 3 adds local hardware/resource management and the controlled local AI runtime. It does **not** enable resume tailoring, job discovery, browser filling, or employer submission.

## Acceptance gates

1. Launch remains idle and starts no model download or inference.
2. Hardware capture records current RAM/availability, CPU topology/features, app-root disk capacity, OS GPU evidence, and a conservative single-inference resource budget. Unknown GPU VRAM remains unknown.
3. The installed llama.cpp runtime is the authority for accelerator availability: Vulkan configurations use only exact device IDs returned by `llama-server --list-devices`. Multiple devices require explicit selection; JobPilot never guesses which GPU to use.
4. Runtime/model downloads are possible only through explicit user actions against the versioned catalogue. Every artifact is written under an app-owned path, downloaded atomically, and checked against an exact SHA-256. Runtime archives and the model weight also require their exact recorded byte count.
5. Archive extraction rejects traversal and symbolic-link entries. Destructive cleanup is allowed only beneath the managed tool/model roots.
6. llama.cpp binds only to `127.0.0.1`, receives a per-session random API key, runs `--offline`, uses one server slot, disables the web UI and multimodal projection loading, and is launched through the owned-process supervisor.
7. CPU evaluation is explicitly forced with `--device none`; `-ngl 0` alone is not accepted as proof that a GPU is unused. Vulkan evaluation carries the exact discovered `VulkanN` device ID.
8. Close/cancellation terminates the app-owned llama.cpp process. There is never a process-name-wide kill.
9. One model install/evaluation operation and one inference server may run at a time.
10. Before evaluation, the app applies reserved RAM/disk policy. Constrained memory reduces the controlled context; critical memory blocks startup. A live pressure watcher continues throughout evaluation and closes the owned runtime if pressure becomes critical.
11. Every configuration must independently pass structured-output, malicious-JD/factual adherence, controlled-tailoring, and resource-budget checks. A failed configuration cannot be selected.
12. Evaluation persists backend, exact device ID, context, threads/resource adjustment, elapsed time, generation/prompt throughput when available, peak RSS, and pressure evidence. The fastest passing measured configuration is selected for Phase 4 review.
13. The model catalogue is deliberately small and revisioned. Different upstream model revisions have different install IDs/directories and can coexist during replacement validation; an update can never overwrite the currently validated weights in place.
14. A passing Phase 3 model/configuration creates a persisted **five distinct resume** review gate with 0/5 approvals. Phase 3 has no UI/API that can turn a caller-supplied boolean into a completed gate and leaves automatic tailoring disabled.
15. Future replacement activation requires an installed+validated model, a passing evaluation, the selected configuration, and the persisted completed five-resume gate. Cleanup never deletes non-app-managed/shared or in-use weights, never leaves the model root, and retains database metadata for retired weights.
16. Update metadata checks are user-triggered, rate-limited to at most once every seven days, and never download or automatically trust a newer runtime/model.
17. Existing Phase 0/1 lifecycle and Phase 2 real-template/fact-bank/Tectonic safety checks remain green.

## Pinned Phase 3 catalogue

### llama.cpp

- upstream: `ggml-org/llama.cpp`;
- stable release baseline: `v0.4.0`;
- tested binary build: `b10809`;
- Windows x64 CPU archive: `llama-b10809-bin-win-cpu-x64.zip`, 18,407,457 bytes, SHA-256 `9df3158ed228a641a4b127942d7f459f24c9e13f04682659d05c00c80099b6b5`;
- Windows x64 Vulkan archive: `llama-b10809-bin-win-vulkan-x64.zip`, 35,221,385 bytes, SHA-256 `97e50b3ef0cdd2cb4d5afd446a9006b3496bee6c0d0ba7083d32f36075771870`;
- license: MIT.

### b10809 structured-output wire contract

The exact b10809 README and implementation disagree for `response_format.type = "json_schema"`. The README shows a direct `response_format.schema`, but b10809 `server-common.cpp` actually reads the grammar from `response_format.json_schema.schema`. A real Windows acceptance with the README-shaped direct field returned HTTP-success responses that failed JobPilot's local validator; the older implementation-shaped nested path had passed the real Qwen3 evaluation.

JobPilot therefore pins to the **executable implementation contract** for b10809:

```json
{
  "type": "json_schema",
  "json_schema": {
    "name": "jobpilot_response",
    "strict": true,
    "schema": {"...": "JobPilot schema"}
  }
}
```

This is not a relaxation of validation. llama.cpp grammar enforcement is only a generation aid. JobPilot independently parses the returned content and validates a fail-closed local JSON-schema subset including required fields, types, arrays, enums, string length and `additionalProperties: false`. Unsupported local schema keywords are rejected rather than ignored.

### Model

- logical catalogue ID: `qwen3-4b-q4_k_m`;
- source: `ggml-org/Qwen3-4B-GGUF`;
- pinned revision: `2f3b082b1356a6123f7ed71e65aea340da25d53c`;
- file: `Qwen3-4B-Q4_K_M.gguf`;
- exact size: 2,497,280,640 bytes;
- SHA-256: `ab27b9bfa375a178d6cba48f3ad892b94b7739659dcc7aae8058ce0ffed6b328`;
- license: Apache-2.0;
- controlled Phase 3 context baseline: 4096 tokens;
- text only for JobPilot; no multimodal projection is downloaded or loaded.

The model's source advertises a larger native context, but JobPilot does not equate upstream maximum context with a safe local setting. It uses only the controlled context that passes local resource/quality evaluation.

## External Windows acceptance

`python scripts/phase3_model_acceptance.py` intentionally performs explicit public CI-only test downloads of the pinned CPU runtime and Qwen3 4B Q4_K_M weights. It launches a localhost-only server, runs the deterministic acceptance suite, records measured throughput/RSS/pressure, selects the passing CPU configuration only for the future review gate, verifies that the gate is still 0/5, and verifies that automatic tailoring remains disabled.

GitHub-hosted CI does not establish Vulkan performance or suitability for the user's machine. If the user's Windows PC exposes one or more Vulkan devices through the pinned runtime, each desired device/configuration must be evaluated locally before it can compete with CPU on measured speed and quality.

## Phase boundary

Phase 3 may be marked complete after the combined Phase 0-3 Windows workflows pass on the final Phase 3 branch head and the persistent project records are updated. Phase 4 remains separate: it supplies real JD-driven tailoring, deterministic LaTeX/PDF validation, and the five distinct human-approved tailored resumes that can eventually complete the persisted review gate.
