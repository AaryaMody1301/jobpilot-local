# Phase 3 acceptance

Phase 3 adds local hardware/resource management and the controlled local AI runtime. It does **not** enable resume tailoring, job discovery, browser filling, or employer submission.

## Acceptance gates

1. Launch remains idle and starts no model download or inference.
2. Hardware capture records RAM availability, CPU topology/features, free disk, supported GPU evidence, and a conservative single-inference resource budget.
3. Unknown GPU VRAM remains unknown; it is never guessed into an eligibility decision.
4. Runtime/model downloads are possible only through explicit catalogue IDs and are written to app-owned paths.
5. Downloads are atomic and must match the recorded SHA-256; runtime archives also match exact byte size.
6. Archive extraction rejects paths outside the intended app-owned directory.
7. The runtime binds only to loopback, has one server slot, and is launched through the existing owned-process supervisor.
8. Close/cancellation terminates the app-owned llama.cpp process. There is never a process-name-wide kill.
9. One inference/evaluation operation may run at a time.
10. The model must pass local structured-output, malicious-JD/factual adherence, controlled-tailoring, and resource-budget tests. A failed candidate is not selectable.
11. A passing model can only be selected for the later Phase 4 review workflow. Phase 3 leaves automatic tailoring disabled.
12. Replacement cleanup requires a validated replacement plus the future five-resume review gate; deletion is constrained to the app-managed model root. Rollback restores a previously validated model without deleting the failed candidate.
13. Update metadata checks are rate-limited to at most once every seven days and never download a replacement.
14. Existing Phase 0/1 lifecycle and Phase 2 resume/Tectonic safety checks remain green.

## External Windows acceptance

`python scripts/phase3_model_acceptance.py` intentionally performs explicit public test downloads on the CI runner:

- llama.cpp v0.4.0 build b10809 CPU x64 archive;
- ggml-org Qwen3.5-0.8B Q4_0 GGUF.

Both are content pinned. The 0.8B model is used as a small compatibility/evaluation candidate; passing this controlled Phase 3 suite does not waive the Phase 4 five-resume human review gate or establish that it is the best model for a user's hardware.

The user's real resume remained an unresolved Phase 2 acceptance item when Phase 3 was authorized. Phase 3 preserves that limitation rather than manufacturing a completed resume baseline.
