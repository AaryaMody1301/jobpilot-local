# Phase 6 acceptance - controlled application engine

Phase 6 builds the application engine only against app-controlled localhost fixtures. It does **not** implement Greenhouse, Lever, or Ashby employer adapters and it does not permit real employer submissions. Those boundaries remain Phase 7+ work.

## Scope

### 6A - transactional journal and one worker

- SQLite is authoritative for every application transition.
- `job_identity` remains unique and duplicate queue requests return the existing attempt.
- Exactly one application worker is created by explicit Start; launch remains Idle with no hidden scheduler.
- Pause prevents a new claim but does not interrupt the currently executing attempt.
- Stop/Close cancels pre-submit work. Once Submit may have started, the engine observes a bounded confirmation window; ambiguity is `UNCERTAIN` and is never automatically retried.
- Interrupted `INSPECTING`, `FILLING`, or `READY_TO_SUBMIT` controlled work is safely requeued after a crash. The existing Phase 0 recovery rule converts interrupted `SUBMITTING`/`CONFIRMING` work to `UNCERTAIN`.

### 6B - controlled Playwright fixture engine and approved answers

- Playwright 1.62.0 is already pinned; Phase 6 adds no dependency.
- The worker owns one synchronous Playwright instance on its own thread and one persistent browser context using JobPilot's dedicated browser profile.
- A Phase 6 target must be absolute HTTP(S), credential-free, and syntactically target `localhost` or a loopback IP. Browser routing blocks non-loopback HTTP(S) subresources and redirects are revalidated.
- Controlled forms declare supported fields with `data-jobpilot-key`, `data-jobpilot-label`, optional `data-jobpilot-context`, and a single `data-jobpilot-submit` control.
- Reusable answers are keyed by the question key plus a SHA-256 semantic context containing label, control type, context marker, and select options. Similar-looking but changed questions do not silently reuse an answer.
- Unknown mandatory supported questions enter the review lane while the single worker continues with other queued controlled fixtures.

### 6C - conservative challenge/recovery behavior

- `data-jobpilot-block` represents challenge classes such as CAPTCHA, assessment, login/verification, payment, or unsupported forms and transitions to `BLOCKED` before submit.
- Unsupported required fields not using the controlled contract are blocked rather than guessed.
- Pre-submit browser/network failures use a small bounded retry only for localhost fixture reliability; a dropped connection that leaves Chromium on an internal error page remains retryable, while an explicit external HTTP(S) escape is blocked.
- Immediately before the click the journal records `SUBMITTING`. A successful click records `CONFIRMING`.
- Only `[data-jobpilot-confirmation="success"]` establishes `CONFIRMED`. Any click/confirmation timeout or exception after the submit boundary becomes `UNCERTAIN`.

## Precise checks

Ponytail-style checks are deliberately small:

1. `tests/unit/test_phase6_applications.py` checks the consequential journal rules: external target rejection, duplicate prevention, exact-context answer reuse, review requeue, pre-submit crash recovery, and terminal `UNCERTAIN` recovery.
2. `scripts/phase6_application_acceptance.py` runs one localhost-only Playwright fixture server covering successful review/fill/confirm, unknown mandatory question while other work continues, CAPTCHA blocking, pre-submit network retry, ambiguous post-submit `UNCERTAIN`, single-worker submission, duplicate prevention, and persistent profile creation.
3. The existing full non-external regression suite protects earlier phases, followed by source/package self-tests and hidden WebView2 smoke.

No getter/setter test matrix, provider adapter matrix, or real employer submission is part of Phase 6.

## Playwright evidence

Official Playwright documentation is authoritative for Phase 6 browser behavior: browser binaries are version-coupled and can be placed with `PLAYWRIGHT_BROWSERS_PATH`; persistent contexts require a separate user-data directory and should not automate a normal browser profile; and Playwright's synchronous API is not thread-safe, so the application worker owns its Playwright instance on one thread.

## Accepted Windows evidence

Run `34743335410` on code head `8d1cb12d1a5ff096ecfc8b8df470777ee3b99c43` concluded `success` on 2026-09-13. It passed syntax validation, the complete non-external regression suite, the controlled localhost Playwright acceptance, source desktop self/window checks, PyInstaller onedir build, and packaged self/window checks.

Final completion additionally requires the pull-request-context Phase 0-6 workflows to be green on the documentation-only final PR head. The Phase 4 private five-real-resume gate remains independent and is not silently waived by Phase 6 acceptance.
