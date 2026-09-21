# Roadmap

Status legend: `[ ] planned`, `[~] in progress`, `[x] complete`, `[!]` private evidence pending.

## Completed product foundation [x]

The Windows desktop foundation, immutable resume/fact system, local AI/resource manager, evidence-backed tailoring, public Greenhouse/Lever/Ashby discovery, controlled application engine, supported hosted-form adapters, orchestration, backup/restore, Windows distribution, and explicitly user-authorized measured-pilot write path are implemented.

Historical build sequencing is condensed in `docs/IMPLEMENTATION_HISTORY.md`.

## Repository cleanup [x]

- [x] PR #21: production entrypoint/bridge cleanup and removal of sample-development runtime state.
- [x] PR #23: one final production UI shell, removal of phase-injected UI and development fixture controls, active-view rendering, accessibility cleanup, and final-shell regression coverage.
- [x] PR #24: durable CI/release workflows, deletion of obsolete phase entrypoints/bridges/UI/probes, capability-named acceptance scripts, and documentation cleanup.

## Job/application workspace [x]

The current feature slice implements:

- [x] searchable/filterable saved-job workspace with the persisted JD snapshot and evidence explanation;
- [x] employer/title/location/workplace/employment plus compensation/deadline when the public provider exposes them;
- [x] explicit on-demand Greenhouse pay/deadline refresh instead of N+1 detail requests during board discovery;
- [x] searchable/filterable application workspace tied to the exact tailoring run and immutable package;
- [x] exact tailored-resume preview from the application's recorded run;
- [x] local follow-up date, notes, and next action metadata without adding another application state machine;
- [x] merged as PR #25 after Windows CI and Windows Acceptance passed.

## Local-AI maintenance evaluation [~]

- [x] research the current stable llama.cpp release and exact Windows x64 artifacts;
- [x] catalogue v0.4.1/b10964 CPU/Vulkan as maintenance candidates with exact size/SHA-256;
- [~] run the existing Windows quality/resource evaluation against b10964 using the current pinned Qwen3 4B model;
- [ ] keep b10809 as the validated baseline unless the candidate passes and a user explicitly selects it;
- [ ] any selected replacement must complete the existing five-distinct-resume review gate before automatic tailoring can use it.

## Private product evidence [!]

These are not repository-development blockers and cannot be satisfied by synthetic CI:

- five distinct real tailored resumes must be explicitly approved under one current local review context;
- run the measured real-world application pilot from private local data and record armed/confirmed/blocked/review/stale/`UNCERTAIN` outcomes plus elapsed/local-day throughput;
- do not claim 50 confirmed applications/day without measured evidence.

See `docs/PHASE4_CLOSEOUT.md` and `docs/PHASE9_PILOT_ACCEPTANCE.md`.
