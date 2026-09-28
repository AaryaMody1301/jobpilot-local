# Roadmap

Status legend: `[ ] planned`, `[~] in progress`, `[x] complete`, `[!]` private evidence pending.

## Post-audit repairs [~]

PR #38 is the single repair and `0.2.2` release-preparation PR. It contains all changes from the superseded draft PRs #32–#37; those drafts do not need to be merged separately. The combined source at `7fd1bd7` passed Windows CI and Windows Acceptance. Final checks must also pass after the documentation consolidation.

- [x] PR #31: desktop and orchestration response/state fixes, package freshness and session ownership, evidence/eligibility guards, selected evaluation binding, and main-only release execution.
- [x] Validated unchanged-master application packages, browser draft retention, and partial-malformed-board recovery.
- [x] Paginated job, application, JD, and tailoring workspaces; complete application totals and visible evidence-integrity errors.
- [x] Annual salary/currency and explicit experience-range targeting, conservatively reviewing unknown compensation.
- [x] Hidden resume inputs, nested frame blockers/host validation, and delayed iframe confirmation.
- [x] Immutable local LaTeX dependency revisions copied into baseline and tailoring packages, with integrity/approval invalidation.
- [x] Explicit same-hash master/supporting-source recovery with quarantine and preserved approvals.
- [ ] Broader real-form compatibility beyond the controlled supported shapes.
- [~] Review and merge only PR #38, then require the `main` Windows release path to pass before treating `0.2.2` as delivered; `v0.2.1` is immutable and predates PR #31.

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

## Repository engineering closeout [x]

- [x] capability-oriented controller, inference, orchestration, pilot, runtime-helper, state-flag, and activity naming;
- [x] obsolete development sample-work database helpers removed while immutable migration history remains untouched;
- [x] obsolete public phase snapshot/review-report fields removed; the documented `--phase4-gate-report` CLI alias remains only for backward compatibility;
- [x] durable `Windows CI`, `Windows Acceptance`, and `Windows Release` workflows retained;
- [x] JobPilot Local `0.2.1` prepared so this final cleanup can publish from its own merge commit rather than reuse the existing `v0.2.0` tag.

## Repository administration [~]

These are GitHub repository settings, not source-code work:

- [ ] protect `main` with pull-request-only changes, strict/up-to-date `windows-ci` and `windows-acceptance`, conversation resolution, and no force-push/deletion;
- [x] GitHub release immutability enabled; `v0.2.1` is published with GitHub-native `immutable: true`.

The connected GitHub integration can verify these settings. Release immutability is now enabled; the integration still does not expose the repository-administration write needed to protect `main`.

## Private product evidence

### Five-resume human review gate [~]

- [ ] run `python -m jobpilot.app.main --review-gate-report` on the Windows machine holding the private profile;
- [ ] approve five distinct real tailored resumes under one unchanged current review context;
- [ ] require the privacy-safe report to return exit code 0.

### Measured real-world pilot [!]

- [ ] run the measured pilot from private local data and record armed/confirmed/blocked/review/stale/`UNCERTAIN` outcomes plus elapsed/local-day throughput;
- [ ] do not claim 50 confirmed applications/day without measured evidence.

See `docs/PHASE4_CLOSEOUT.md` and `docs/PHASE9_PILOT_ACCEPTANCE.md`.
