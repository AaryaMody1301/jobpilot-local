# Progress

## Current phase

Phase 5 - Job discovery and matching.

Status: **implementation complete and focused Windows acceptance passed**. Phase 6 has not started and employer form filling/submission remains disabled.

Phase 4's technical implementation is merged, but its private five-real-resume human gate remains a separate local acceptance condition. The user explicitly authorized Phase 5 development on 2026-09-12 without waiving that gate.

## Phase 5 implementation

- Added migration `007_phase5_jobs.sql` for verified job boards and normalized discovered jobs.
- Added manual job import with credential-free absolute HTTP(S) provenance.
- Added compact stdlib-only public GET clients for Greenhouse, Lever, and Ashby.
- Added one verified starter board per provider; a user-added identifier is persisted only after its live public endpoint returns a supported payload.
- Added conservative deduplication by exact source identity and exact normalized content identity.
- Added hard eligibility checks for employer exclusion, configured role titles, permanent full-time employment, explicit experience minimums, India office-city rules, overseas relocation/sponsorship, and explicit remote-US-only restrictions.
- Unknown mandatory employment/location/origin/sponsorship conditions become `review`; they are not guessed.
- Required/preferred evidence matching uses only approved facts whose backing source still verifies.
- Ranking exposes role/evidence/clarity components and is not described as an ATS score or interview probability.
- Added a small bundled Phase 5 jobs UI layer that reuses the Phase 4 shell. Remote ATS requests remain in Python; JavaScript performs no fetch/XHR.
- Employer submission remains false throughout the controller/UI state.

## Compact-code/check policy

`AGENTS.md` now records the project-wide Ponytail-style rule for later phases: avoid code when possible, then prefer stdlib/native/already-installed dependencies, write the minimum clear code, avoid speculative abstractions, and test only real trust boundaries/product decisions. Security, data integrity, accessibility, and explicit product gates are not removed for compactness.

No implementation code was copied from `Rojios/ponytail`; it is a development-style reference only and is recorded in `THIRD_PARTY_NOTICES.md`.

## Verification

Phase 5 Windows run `34686987747`, head `76398acef947a7c09df83db40fa06b82103f04f0`, concluded `success` on 2026-09-12.

Passed:

- Python and JavaScript syntax validation;
- `pytest -m "not external"` regression suite;
- live public Greenhouse, Lever, and Ashby discovery-contract acceptance;
- source self-test;
- source hidden WebView2/pywebview smoke including the Phase 5 jobs UI;
- PyInstaller onedir build;
- packaged self-test;
- packaged hidden-window smoke.

The focused Phase 5 test module intentionally checks only the three external payload shapes and the consequential matching/dedup decisions; it does not duplicate trivial implementation-detail tests.

## Next boundary

Merge the Phase 5 PR only after its final pull-request-context Phase 0-5 workflows are green. Do not start Phase 6 without a later explicit user request.
