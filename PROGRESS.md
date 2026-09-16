# Progress

## Current phase

Phase 9 - Packaging and user-authorized pilot.

Status: **distribution/recovery and the separately authorized measured-pilot write path are technically implemented and hardened; Phase 9 remains in progress because no measured real-world application pilot has yet been run**.

PR #13 merged the Phase 9 distribution/recovery boundary into `main` at `837d5d1bdacccdabe325b2bc196d5c3628845451`. After that merge, the user gave a later separate instruction to start the next Phase 9 boundary, satisfying the repository's authorization requirement for pilot implementation. PR #14 then merged that write path. Phase 4's private five-real-resume human gate remains a separate local acceptance condition and is not waived.

## Phase 9 distribution/recovery

The merged Phase 9A boundary provides:

- a verified Windows 10/11 x64 onedir distribution with per-user setup and rollback-safe upgrade;
- hermetic Playwright Chromium and WebView2 prerequisite handling;
- release SHA-256 integrity metadata;
- portable local backup/restore for database/documents/application artifacts while preserving machine-specific models/tools/browser/cache state;
- restart-bound restore with a pre-restore safety backup;
- distribution/browser/WebView notices.

Accepted Phase 9A technical head: `b5ebda60793e3f61a25885b4370ebf5242d2e705`, Windows run `35056956675`.

## User-authorized measured-pilot implementation

The pilot implementation intentionally reuses the existing Phase 6-8 state machine, immutable packages, provider adapters and **single application worker**. It does not introduce a second scheduler or a second submit worker.

Current behavior:

- project-level pilot implementation authorization is recorded, but every process launch starts with the live lane inactive;
- activation is allowed only while Idle and requires the exact local phrase `ENABLE MEASURED REAL APPLICATION PILOT`;
- activation is memory-only and never survives restart;
- every real application must have a current immutable `PREPARED` package and a fresh read-only live-form inspection before it can be armed;
- only supported Greenhouse/Lever/Ashby HTTPS hosted-form hosts are accepted;
- CAPTCHA, login/verification, payment, assessment, unsupported required fields and ambiguous submit controls remain blockers;
- a maximum of five distinct real applications can be armed during one launch;
- the worker can claim only application IDs explicitly armed in the current launch;
- deactivation, restart and restore staging rewind queued never-submitted real work to `PREPARED`, clear its prior live inspection and require inspection plus arming again;
- immediately before any live write, package freshness and the live form are checked again;
- the current tailored PDF is resolved from app-managed storage and re-hashed immediately before upload, and is uploaded only to a recognized resume/CV upload; another required file field blocks rather than guessing;
- missing mandatory application answers use the existing exact-context human review lane;
- optional fields are not invented; they are filled only when an exact-context approved answer already exists;
- Stop/deactivation is checked again at the final pre-submit boundary;
- after the submit click, any ambiguous exception or absent **new post-submit** positive employer confirmation becomes terminal `UNCERTAIN` with no automatic retry;
- only newly observed explicit positive confirmation counts as a confirmed real application.

The provider write capability is isolated behind an explicit live-write adapter mode. Default live provider adapters preserve the established fail-closed `adapter writes are disabled for live employer pages` contract used by Phase 7 acceptance.

## Verification

Original accepted technical pilot head: `06a2f31d47dc3dbe09bcf0eda3fd34bf0278d0e5`.

Original Windows run: `35072562186` (`Phase 9 acceptance`), conclusion `success`.

That acceptance passed the full technical write-path, provider, packaging and distribution gates then present in the repository.

### Post-merge audit hardening

A later repository-wide release audit found two defects that the original controlled tests did not exercise:

1. the live engine read a nonexistent `pdf_path` value even though tailoring persists `pdf_relpath`, so a real resume upload would fail before form filling;
2. provider confirmation accepted generic success-like page text without proving that the success state appeared after the submit click.

PR #15 repairs both without weakening any gate. The live engine now resolves `pdf_relpath` through the managed tailoring store, verifies the persisted PDF SHA-256 immediately before upload, and fails closed on missing/tampered/escaped artifacts. Hosted-form adapters capture a pre-submit URL/marker/success-phrase baseline and only confirm when new success evidence appears after submission.

The hardening also refreshes the validated packaging stack to Playwright 1.63.0 / Chromium revision 1243 / Chrome for Testing 153.0.8010.12, pypdf 6.18.1 and PyInstaller 6.22.3, adds pinned `pip-audit` 2.10.1 to CI, corrects the packaged pilot README boundary, and makes the Phase 9 workflow run on final `main` pushes.

Exact hardening head: `75205774ad8cf444fe9081073b59c3e951849a50`.

Exact-head Phase 0 through Phase 9 workflows all passed. Relevant final runs include:

- Phase 3 real local llama.cpp/model acceptance: `35077829489`;
- Phase 4 real local tailoring acceptance: `35077829627`;
- Phase 7 current provider recognition/controlled-submit acceptance: `35077829494`;
- Phase 8 orchestration/staleness acceptance: `35077829506`;
- Phase 9 full Windows release acceptance: `35077829573`.

Phase 9 run `35077829573` additionally passed the dependency vulnerability audit, new resume-artifact/confirmation hardening tests, source and packaged desktop checks, hermetic Chromium PyInstaller build, verified distribution build, clean install/in-place upgrade, and artifact upload. Actions artifact `10439455880` is 381,619,153 bytes with digest `sha256:b10e206459f58fe479a72941769e6b71cc187c38a0b1afe467ceec172afdff2d`.

No failed safety condition was waived.

## Provider/API choice

The measured pilot continues through supported hosted applicant forms. Public Greenhouse/Lever/Ashby programmatic application APIs require employer-side integration credentials/permissions rather than candidate credentials, so JobPilot does not ask the candidate for employer API keys or pretend those server integrations are an applicant authentication mechanism.

## Remaining product evidence

Two deliberately non-synthetic gates remain outside repository/CI completion:

- Phase 4 requires five **distinct real** tailored resumes to be explicitly approved in the user's private local JobPilot database under one current validation context. CI-controlled tailoring cannot count toward this gate.
- Phase 9 requires a **measured real-world pilot** from the user's local/private JobPilot data using individually user-armed eligible applications. Record armed/confirmed/blocked/review/stale/`UNCERTAIN` outcomes and elapsed/local-day throughput.

The visible 50/day objective remains a target rather than a capability claim until measured real-pilot evidence supports it.

See `docs/PHASE4_CLOSEOUT.md` and `docs/PHASE9_PILOT_ACCEPTANCE.md` for the exact private closeout procedures and acceptance boundaries.
