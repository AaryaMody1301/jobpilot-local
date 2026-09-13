# Progress

## Current phase

Phase 6 - Application engine using controlled forms.

Status: **implementation complete and focused Windows acceptance passed**. Phase 7 has not started. Real employer form filling/submission remains disabled.

PR #9 merged Phase 5 into `main` at `29234991ca824eb6d5f4d1892079360c3241431b` on 2026-09-12. Phase 4's private five-real-resume human gate remains a separate local acceptance condition and is not waived by later development authorization.

## Phase 6 implementation

- Added additive migration `008_phase6_applications.sql` for controlled-attempt leasing/retry metadata, exact-context approved answers, and mandatory-question review records.
- Reused the existing Phase 0 application state machine/journal and existing `jobpilot.applications` package rather than adding a second workflow model or parallel package.
- Added one compact application-engine module containing the transactional journal, localhost trust boundary, exact-context answer fingerprint, controlled Playwright engine, and one worker. No new dependency or provider abstraction was added.
- Targets must be absolute credential-free localhost/loopback HTTP(S). Real employer targets are rejected before Playwright and non-loopback HTTP(S) browser requests are aborted.
- Playwright runs on the single application-worker thread with one dedicated persistent JobPilot profile.
- Unknown mandatory supported questions enter review and are reusable only when question key + semantic context hash match exactly; other queued controlled fixtures continue.
- CAPTCHA/assessment/login/verification/payment/unsupported markers block before submit.
- Pre-submit network/browser failures are safely bounded-retryable; interrupted pre-submit attempts recover to queued. Browser-internal error pages caused by a dropped localhost connection remain retryable, while explicit external HTTP(S) escapes remain blocked.
- `SUBMITTING` is persisted immediately before the click; only an explicit positive confirmation marker can become `CONFIRMED`. Post-submit ambiguity becomes terminal `UNCERTAIN`.
- Phase 6 UI is a small bundled layer on top of the existing shell and exposes the single worker, review lane, and controlled journal. JavaScript performs no remote networking.
- Greenhouse, Lever, and Ashby employer-form adapters are deliberately not implemented; they remain Phase 7.

## Compact-code/check policy

The repository-wide Ponytail rule remains authoritative: prefer no code, then stdlib/native/already-installed dependencies, then the minimum clear implementation. Phase 6 uses the already-pinned Playwright dependency and existing SQLite/application state machinery instead of a new automation framework.

Checks are limited to consequential boundaries: one focused journal/state test plus one localhost Playwright acceptance. The full existing regression suite and desktop/package smokes remain the integration safety net.

## Verification

Phase 6 Windows run `34743335410`, code head `8d1cb12d1a5ff096ecfc8b8df470777ee3b99c43`, concluded `success` on 2026-09-13.

Passed:

- Python and bundled JavaScript syntax validation;
- the complete non-external regression suite;
- controlled localhost Playwright acceptance covering successful review/fill/confirmation, exact-context answer reuse, an unknown mandatory question while other work continues, CAPTCHA blocking, pre-submit network retry, duplicate prevention, single-worker submission, persistent profile creation, and ambiguous post-submit `UNCERTAIN`;
- source self-test and hidden WebView2/pywebview smoke;
- PyInstaller onedir build;
- packaged self-test and packaged hidden-window smoke.

No failed acceptance condition was waived. Earlier development runs exposed and fixed a workflow-expression error, an existing-package integration mistake, and the transient localhost navigation classification edge before this accepted head.

## Next boundary

Open and merge the Phase 6 PR only after the final pull-request-context Phase 0-6 workflows are green. Do not start Phase 7 without a later explicit user request.
