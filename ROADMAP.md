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

## Local-AI maintenance evaluation [x]

- [x] researched stable llama.cpp v0.4.1 and exact b10964 Windows x64 artifacts;
- [x] catalogued b10964 CPU/Vulkan as maintenance candidates with exact size/SHA-256;
- [x] b10964 CPU passed the existing Windows structured/factual/tailoring/resource evaluation against the pinned Qwen3 4B model;
- [x] b10809 remained selected after candidate evaluation; there was no automatic promotion;
- [x] any future explicit runtime change remains bound to the existing five-distinct-resume review gate.

## Private product evidence

### Five-resume human review gate [~]

- [ ] run `python -m jobpilot.app.main --review-gate-report` on the Windows machine holding the private profile;
- [ ] approve five distinct real tailored resumes under one unchanged current review context;
- [ ] require the privacy-safe report to return exit code 0.

### Measured real-world pilot [!]

- [ ] run the measured pilot from private local data and record armed/confirmed/blocked/review/stale/`UNCERTAIN` outcomes plus elapsed/local-day throughput;
- [ ] do not claim 50 confirmed applications/day without measured evidence.

See `docs/PHASE4_CLOSEOUT.md` and `docs/PHASE9_PILOT_ACCEPTANCE.md`.
