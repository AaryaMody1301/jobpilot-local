# Progress

## Current phase

Phase 7 - Supported hiring-platform adapters.

Status: **implementation complete and exact-head Windows acceptance passed**. Phase 8 has not started. Real employer form filling/submission remains disabled; Phase 7 live checks are read-only.

PR #10 merged Phase 6 into `main` at `28a2dd4ec4d5c6ec5227eaf6029dcf50342234af` on 2026-09-13. Phase 4's private five-real-resume human gate remains a separate local acceptance condition and is not waived by later development authorization.

## Phase 7 implementation

- Added one compact shared hosted-form adapter implementation under the existing `jobpilot.applications` package instead of adding provider frameworks or a second browser engine.
- Added Greenhouse host support for `job-boards.greenhouse.io` and `boards.greenhouse.io`.
- Added Lever host support for `jobs.lever.co` and `jobs.eu.lever.co`.
- Added Ashby host support for `jobs.ashbyhq.com`.
- Provider targets must be absolute credential-free HTTP(S) URLs on the exact supported host list.
- Live mode is read-only: `fill()` and `submit()` fail closed unless the adapter is explicitly created for a loopback controlled fixture. No real employer form was filled or submitted during Phase 7.
- Visible form fields, required status, supported input types and a single submit control are recognized using the existing Playwright dependency.
- Supported controlled input types are text/email/tel/url/number/date/file/checkbox/radio plus textarea/select. Required unsupported controls become blockers rather than guessed answers.
- CAPTCHA, login/verification, actual card/billing controls, assessment controls and unsupported required fields remain conservative blockers.
- Explicit positive confirmation is still required after a controlled submit.
- A live Nium field containing the ordinary word `payment` exposed an over-broad payment detector during acceptance. The detector was narrowed to actual credit-card/payment controls and the controlled fixture now includes `payment_experience` to prevent regression.

## Sequential provider gates

Phase 7 followed the roadmap order; the next provider was not started until the prior provider passed both required gates:

- 7A Greenhouse: code head `87c9138157f5ed42e0c4772e747867070e53a114`, Windows run `34744776048`, success.
- 7B Lever: code head `6e350b76fe284441436978d3ee71d69028d8b014`, Windows run `34744964533`, success.
- 7C Ashby plus final payment-classifier repair: accepted code head `3a95d0a32755c94b21ec77c209749986718167a6`, Windows run `34745312735`, success.

## Final verification

Accepted Phase 7 Windows run `34745312735` passed:

- Python and bundled JavaScript syntax validation;
- the complete non-external regression suite: 128 passed, 1 skipped, 2 deselected;
- one provider acceptance covering controlled submit/explicit confirmation plus read-only live form recognition for Greenhouse, Lever and Ashby;
- live write guards for all three providers;
- source self-test and hidden WebView2/pywebview smoke;
- PyInstaller onedir build;
- packaged self-test and packaged hidden-window smoke.

The final live recognition evidence was:

- Greenhouse/GitLab: 29 visible application fields, one submit control, CAPTCHA blocker;
- Lever/Nium: 11 visible application fields, one submit control, CAPTCHA blocker;
- Ashby/Ashby: 26 visible application fields, one submit control, CAPTCHA blocker.

All three current live examples were therefore recognized but conservatively reported unsupported for automatic submission. This is an expected safety result, not a waived check.

## Compact-code/check policy

The repository-wide Ponytail rule remains authoritative: prefer no code, then stdlib/native/already-installed dependencies, then the minimum clear implementation. Phase 7 reuses the existing `ApplicationAdapter` protocol, Playwright dependency and Phase 5 public-board discovery instead of introducing new packages or provider-specific engines.

Checks remain boundary-focused: one consolidated provider acceptance plus the existing regression and desktop/package safety net. No provider-specific test matrix was added merely to increase test count.

## Next boundary

Open and merge the Phase 7 PR only after the final pull-request-context workflows are green. Do not start Phase 8 without a later explicit user request. Phase 8 is responsible for connecting discovery, matching, tailoring gates, provider adapters, queues, attention/history and submission orchestration.
