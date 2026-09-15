# Progress

## Current phase

Phase 8 - End-to-end orchestration.

Status: **implementation complete and exact-head Windows acceptance passed**. Phase 9 has not started. Real employer form filling/submission remains disabled; Phase 8 live provider checks are read-only.

PR #11 merged Phase 7 into `main` at `4922340766bc01a54599083ff7a69f76b6db682a` on 2026-09-13. Phase 4's private five-real-resume human gate remains a separate local acceptance condition and is not waived by later development authorization.

## Phase 8 implementation

- Added additive migration `009_phase8_orchestration.sql` on top of the existing SQLite application journal. No second database, scheduler, state machine or submission engine was introduced.
- Discovery/matching results now enter the existing application state machine as persisted `DISCOVERED` attempts and move transactionally through eligibility, tailoring, review/prepared, queue and application states.
- Existing Phase 5 eligibility remains authoritative: hard failures become `INELIGIBLE`; unknown mandatory conditions become `NEEDS_REVIEW` and require an explicit recorded decision.
- Existing Phase 4 tailoring and model-review gates remain authoritative. Phase 8 will not start unattended tailoring without a validated selected model and never treats later development authorization as completion of the private five-real-resume gate.
- Critical resource pressure pauses new tailoring at a safe pre-submit boundary rather than reducing model/validation/review quality.
- Added immutable `application_packages` that bind one application to the discovered job snapshot, tailoring audit hashes/context and the current exact-context approved-answer fingerprint.
- Freshness is rechecked before controlled queue entry and again before the existing single submission worker can claim a packaged attempt. Changed/deactivated jobs, stale/tampered tailoring evidence or changed approved answers become `STALE` rather than submitted.
- Mandatory application questions continue through the existing Phase 6 exact-context review lane. The immutable package is refreshed only after all required unknown questions are resolved and the attempt safely returns to `QUEUED`.
- Live Greenhouse/Lever/Ashby inspection is read-only. Phase 8 records recognized fields/blockers but exposes no live provider fill/submit action; unsupported providers are reported rather than guessed.
- The existing controlled application worker remains the only submission worker. Development submission still accepts loopback fixtures only, requires explicit positive confirmation and preserves terminal `UNCERTAIN` behavior.
- Added an orchestration attention/history UI plus a local-calendar-day objective showing 50 confirmed real applications. Controlled fixture confirmations are counted separately and never contribute to the real target. No logic stops at 50 or weakens eligibility/factual/review gates to reach it.
- Application launch remains Idle. Discovery/orchestration run only after explicit Start; Pause prevents new orchestration work after the current safe item; Stop/Close cancel pre-submit work using existing boundaries.

## Verification

Accepted Phase 8 runtime head `5b2a10827a2b81533a2017dd9828395ded91a383`, Windows run `34946104772`, concluded `success` on 2026-09-15.

Passed:

- Python and bundled JavaScript syntax validation;
- complete non-external regression suite: 129 passed, 1 skipped, 2 deselected;
- focused Phase 8 controlled end-to-end acceptance covering fresh immutable package preparation, two unknown mandatory answers, review continuation, package refresh, single controlled submit, explicit confirmation and exclusion of the controlled confirmation from the real daily counter;
- Phase 8 stale-package unit coverage proving an approved-answer change prevents a queued package from being claimed and moves it to `STALE`;
- inherited Phase 7 controlled/live-read-only provider acceptance for Greenhouse, Lever and Ashby, including live write guards;
- source self-test and hidden WebView2/pywebview Phase 8 bridge/UI smoke;
- PyInstaller onedir build;
- packaged self-test and packaged hidden-window smoke.

The inherited Phase 7 live evidence on the accepted Phase 8 head remained: Greenhouse/GitLab 29 fields, Lever/Nium 11 fields and Ashby/Ashby 26 fields; each current example exposed CAPTCHA integration and remained conservatively unsupported for automatic submission. No real employer form was filled or submitted.

The first development run exposed only older migration tests whose expected lists stopped at migration `008`; the new Phase 8 stale-package test already passed. Those expectations were updated to include additive migration `009`. The same repair also tightened multi-question answer handling so package refresh occurs only after all mandatory review questions resolve. No failed safety condition was waived.

## Compact-code/check policy

The repository-wide Ponytail rule remains authoritative: prefer no code, then stdlib/native/already-installed dependencies, then the minimum clear implementation. Phase 8 reuses the existing job store/matcher, tailoring service, model/resource manager, application journal/state machine, Playwright dependency, provider adapters and single submission worker.

Checks remain boundary-focused: one orchestration/staleness unit test, one controlled end-to-end acceptance, the inherited Phase 7 provider acceptance, and the existing regression/desktop/package safety net.

## Next boundary

Open and merge the Phase 8 PR only after all pull-request-context Phase 0 through Phase 8 workflows are green. Do not start Phase 9 without a later explicit user request. Phase 9 owns clean-machine packaging/setup/upgrade/backup/restore/notices and, separately, explicit user authorization for any measured real-application pilot.
