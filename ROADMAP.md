# Roadmap

Status legend: `[ ] planned`, `[~] in progress`, `[x] complete`, `[!]` private evidence pending.

## Completed product foundation [x]

The Windows desktop foundation, immutable resume/fact system, local AI/resource manager, evidence-backed tailoring, public Greenhouse/Lever/Ashby discovery, controlled application engine, supported hosted-form adapters, orchestration, backup/restore, Windows distribution, and explicitly user-authorized measured-pilot write path are implemented.

Historical build sequencing is condensed in `docs/IMPLEMENTATION_HISTORY.md`.

## Repository cleanup [~]

- [x] PR #21: production entrypoint/bridge cleanup and removal of sample-development runtime state.
- [x] PR #23: one final production UI shell, removal of phase-injected UI and development fixture controls, active-view rendering, accessibility cleanup, and final-shell regression coverage.
- [~] PR 3: durable CI/release workflows, deletion of obsolete phase entrypoints/bridges/UI/probes, capability-named acceptance scripts, and documentation cleanup.

## Job/application workspace [ ]

After repository cleanup:

- expose job/application detail in one workspace;
- show saved JD snapshot, employer/title/location/compensation/deadline when available;
- keep the exact tailored resume/application package associated with the application;
- add search/filter/grouping around current job/application state;
- expose follow-up date, notes, and next action without weakening automation gates.

## Local-AI maintenance evaluation [ ]

Evaluate newer llama.cpp releases independently. Do not replace the validated v0.4.0/b10809 runtime unless exact artifacts, license/checksum metadata, quality/resource evaluation, and replacement review-gate requirements pass.

## Private product evidence [!]

These are not repository-development blockers and cannot be satisfied by synthetic CI:

- five distinct real tailored resumes must be explicitly approved under one current local review context;
- run the measured real-world application pilot from private local data and record armed/confirmed/blocked/review/stale/`UNCERTAIN` outcomes plus elapsed/local-day throughput;
- do not claim 50 confirmed applications/day without measured evidence.

See `docs/PHASE4_CLOSEOUT.md` and `docs/PHASE9_PILOT_ACCEPTANCE.md`.
