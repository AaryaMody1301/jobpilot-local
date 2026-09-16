# Progress

## Current phase

Phase 9 - Packaging and user-authorized pilot.

Status: **distribution/recovery is accepted and the separately authorized measured-pilot write path is technically implemented/accepted; Phase 9 remains in progress because no measured real-world application pilot has yet been run**.

PR #13 merged the Phase 9 distribution/recovery boundary into `main` at `837d5d1bdacccdabe325b2bc196d5c3628845451`. After that merge, the user gave a later separate instruction to start the next Phase 9 boundary, satisfying the repository's authorization requirement for pilot implementation. Phase 4's private five-real-resume human gate remains a separate local acceptance condition and is not waived.

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
- the current tailored PDF is uploaded only to a recognized resume/CV upload; another required file field blocks rather than guessing;
- missing mandatory application answers use the existing exact-context human review lane;
- optional fields are not invented; they are filled only when an exact-context approved answer already exists;
- Stop/deactivation is checked again at the final pre-submit boundary;
- after the submit click, any ambiguous exception or absent positive employer confirmation becomes terminal `UNCERTAIN` with no automatic retry;
- only explicit positive confirmation counts as a confirmed real application.

The provider write capability is isolated behind an explicit live-write adapter mode. Default live provider adapters preserve the established fail-closed `adapter writes are disabled for live employer pages` contract used by Phase 7 acceptance.

## Verification

Accepted technical pilot head: `06a2f31d47dc3dbe09bcf0eda3fd34bf0278d0e5`.

Windows run: `35072562186` (`Phase 9 acceptance`), conclusion `success`.

Passed:

- Python and bundled JavaScript syntax validation;
- complete non-external regression suite: **135 passed, 1 skipped, 2 deselected**;
- four focused Phase 9 pilot safety tests;
- backup/restore acceptance proving the authorized pilot is still inactive by default after launch/restore;
- inherited Phase 8 controlled orchestration and package-staleness acceptance;
- inherited Phase 7 Greenhouse/Lever/Ashby controlled submit plus current live read-only recognition/write guards;
- source self-test and hidden WebView2/pywebview Phase 9 pilot UI smoke;
- hermetic Playwright Chromium PyInstaller build;
- frozen self-test, bundled-browser smoke and hidden-window smoke;
- verified Windows distribution archive build;
- clean per-user install and in-place upgrade with private local-data preservation;
- installed-app self-test, bundled-browser smoke and hidden-window smoke;
- uploaded Windows x64 artifact plus SHA-256 sidecar.

The accepted release archive was 377,754,213 bytes with SHA-256 `3d3d85c796d7c7475557e8432c82ae856299d27819de937ed5a4abd74ed5a6b3`. Actions artifact `10437151583` was finalized with digest `sha256:31c837ebf5f10b95da628584eeef516ba6e5f1b2c4a417ca4d06bc2ed2056ebf`.

Current inherited live examples remain conservative: Greenhouse/GitLab (29 fields), Lever/Nium (11 fields) and Ashby/Ashby (26 fields) each exposed CAPTCHA integration and therefore remained unsupported for pilot submission. No real employer form was filled or submitted by acceptance.

## Development findings

The first pilot run exposed a regression only in the exact inherited Phase 7 exception text: form recognition still worked, but the default live-write guard wording had changed. The established `adapter writes are disabled for live employer pages` contract was restored; explicit live writes remain available only to the separately armed Phase 9 worker.

A separate review found that queued real work could have survived restart/deactivation and later become claimable without being armed again. The repair limits claims to current-launch armed IDs and rewinds queued live work to `PREPARED` whenever activation resets. It also clears the prior read-only form inspection, requiring a fresh current-launch inspection before re-arming.

No failed safety condition was waived.

## Provider/API choice

The measured pilot continues through supported hosted applicant forms. Public Greenhouse/Lever/Ashby programmatic application APIs require employer-side integration credentials/permissions rather than candidate credentials, so JobPilot does not ask the candidate for employer API keys or pretend those server integrations are an applicant authentication mechanism.

## Next boundary

Run a **measured real-world pilot from the user's local/private JobPilot data** using eligible current packages. Record armed/confirmed/blocked/review/stale/`UNCERTAIN` outcomes and elapsed/local-day throughput. Phase 9 remains `[~]`, and the visible 50/day objective remains a target rather than a capability claim until measured real-pilot evidence supports it.

See `docs/PHASE9_PILOT_ACCEPTANCE.md` for the exact technical boundary and acceptance evidence.
