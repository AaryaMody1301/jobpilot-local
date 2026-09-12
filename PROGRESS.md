# Progress

## Current phase

Phase 5 - Job discovery and matching.

Status: **implementation complete; final exact-head Windows acceptance is the remaining merge check**. Phase 6 has not started and employer form filling/submission remains disabled.

Phase 4's technical implementation is merged, but its private five-real-resume human gate remains a separate local acceptance condition. The user explicitly authorized Phase 5 development on 2026-09-12 without waiving that gate.

## Phase 5 implementation

- Added migration `007_phase5_jobs.sql` for verified job boards and normalized discovered jobs.
- Added manual job import with credential-free absolute HTTP(S) provenance.
- Added compact stdlib-only public GET clients for Greenhouse, Lever, and Ashby.
- Starter registry uses current real public boards: GitLab (`greenhouse:gitlab`), Nium (`lever:nium`), and Ashby (`ashby:ashby`).
- A user-added board identifier is persisted only after its live public endpoint returns a supported payload.
- Successful board refreshes atomically retain provenance while marking jobs removed from the current feed inactive; failed fetches do not retire previously observed jobs.
- Added conservative deduplication by exact source identity and exact normalized content identity.
- Added hard eligibility checks for employer exclusion, configured role titles, permanent full-time employment, explicit experience minimums, India office-city rules, overseas relocation/sponsorship, and explicit remote-US-only restrictions.
- Unknown mandatory employment/location/origin/sponsorship conditions become `review`; they are not guessed.
- Preferred experience is not promoted into a hard minimum.
- Required/preferred evidence matching reuses the Phase 4 current-approved-fact gate, so inactive historical master facts and stale/missing source evidence cannot influence ranking.
- Ranking exposes role/evidence/clarity components and is not described as an ATS score or interview probability.
- Added a small bundled Phase 5 jobs UI layer that reuses the Phase 4 shell. Remote ATS requests remain in Python; JavaScript performs no fetch/XHR.
- Employer submission remains false throughout the controller/UI state.

## Compact-code/check policy

`AGENTS.md` records the project-wide Ponytail-style rule for later phases: avoid code when possible, then prefer stdlib/native/already-installed dependencies, write the minimum clear code, avoid speculative abstractions, and test only real trust boundaries/product decisions. Security, data integrity, accessibility, and explicit product gates are not removed for compactness.

No implementation code was copied from `Rojios/ponytail`; it is a development-style reference only and is recorded in `THIRD_PARTY_NOTICES.md`.

## Verification

An earlier cohesive Phase 5 head passed Windows run `34686987747`: syntax, the full non-external regression suite, live Greenhouse/Lever/Ashby normalization, source/WebView2 smoke, PyInstaller onedir build, and packaged smoke all succeeded.

The final code additionally tightened current-board retirement, current-master evidence scope, starter-board selection, HTML/entity normalization, URL/field limits, and consequential eligibility edge cases. The final branch head must pass the same focused Phase 5 workflow before the PR is opened, then the pull-request-context Phase 0-5 workflows must be green before merge.

The focused Phase 5 tests cover external payload shapes and consequential matching/dedup/current-feed persistence decisions; they deliberately do not duplicate trivial implementation-detail tests.

## Next boundary

Open and merge the Phase 5 PR only after final exact-head Phase 5 acceptance and pull-request-context Phase 0-5 workflows are green. Do not start Phase 6 without a later explicit user request.
