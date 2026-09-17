# Phase 9 measured-pilot activation acceptance

Date: 2026-09-17

Status: **repository implementation and technical hardening accepted; measured real-world pilot evidence is still pending.** No acceptance step in CI fills or submits a real employer form.

## Authorization boundary

The user separately authorized implementation of the measured real-application pilot after the distribution/recovery boundary was merged. That authorization permits the live-write implementation but does not waive any existing product gate.

In particular:

- Phase 4 automatic tailoring still requires five distinct explicitly approved real tailored resumes under the current validation context;
- job eligibility must be resolved rather than guessed;
- the immutable application package must be current immediately before claim/write;
- mandatory application answers must be exact-context human-approved values;
- CAPTCHA/challenge, login/verification, payment, assessment and unsupported form shapes remain hard blockers;
- only the existing single application worker may cross the submit boundary;
- an ambiguous post-click outcome remains terminal `UNCERTAIN` and is never automatically retried;
- only explicit positive employer confirmation counts as a confirmed real application.

## Accepted implementation

The pilot path is deliberately narrow:

1. every JobPilot launch starts with the real-employer lane inactive;
2. local activation requires the exact phrase `ENABLE MEASURED REAL APPLICATION PILOT` while JobPilot is Idle;
3. activation is in-memory only and is not persisted across restart;
4. a prepared real application must first receive a fresh read-only live-form inspection in the current launch;
5. the inspection must identify a supported Greenhouse, Lever or Ashby HTTPS hosted-form target, no blocker, and exactly one supported submit control;
6. each application must then be armed individually by the user;
7. at most five distinct real applications can be armed during one launch;
8. only IDs armed in the current launch can be claimed by the live lane;
9. deactivation, restore staging or restart returns never-submitted queued live work to `PREPARED`, clears its old live inspection and requires fresh inspection plus re-arming;
10. the existing application worker remains the sole worker for both controlled fixtures and the measured live lane, with controlled fixtures retaining priority;
11. immediately before any live write, the worker rechecks package freshness and re-inspects the live form;
12. the current tailored PDF is resolved from its app-managed relative path, its persisted SHA-256 is verified immediately before upload, and it is uploaded only to a recognized resume/CV file field; another required file upload blocks instead of guessing;
13. missing mandatory non-file answers move the application to the existing `NEEDS_REVIEW` lane using exact live-field context fingerprints;
14. the final pre-submit boundary checks Stop/deactivation again before the click;
15. confirmation state is recaptured immediately before the submit click;
16. after the click, `CONFIRMED` requires newly observed positive evidence relative to that immediate pre-submit baseline;
17. submit exceptions or missing positive confirmation after the click become terminal `UNCERTAIN`.

Optional live fields are left unchanged unless an exact-context approved answer already exists. The pilot does not synthesize or guess application answers.

## Provider/API boundary

The public employer APIs are not treated as applicant credentials:

- Greenhouse's application POST is an employer/custom-career-site integration authenticated with the employer's Job Board API key;
- Lever's programmatic apply path similarly requires employer/admin integration credentials and its hosted application form remains the normal applicant surface;
- Ashby's application submission API requires candidate-write API permissions.

JobPilot therefore continues through supported hosted applicant forms and keeps provider-specific host/blocker recognition in front of the write path. The code does not ask the candidate for an employer API key and does not bypass CAPTCHA or other challenges.

## Final repository-level hardening

PR #16, `Final JobPilot technical closeout hardening`, closed the remaining repository findings from the 2026-09-17 deep audit:

- hosted-form adapters now recapture the URL/success-marker/success-phrase baseline immediately before the submit click, eliminating the delayed pre-submit success-text false-positive window;
- a focused regression verifies that success-like text appearing after inspection but before submit cannot confirm an application;
- final Playwright UI interaction coverage verifies backup/restore, pilot activation/deactivation and explicit per-application arming at the minimum 960x660 viewport;
- pypdf was refreshed to 6.19.0 and the build backend was pinned to setuptools 84.0.0 for reproducible source builds;
- third-party notices record the final dependency baseline and explicitly keep newer llama.cpp releases metadata-only until their established local evaluation/replacement gates are satisfied.

PR #16 exact head: `2004157ad079ffdfe51f17f86155b8b2027f09d7`.

All Phase 0 through Phase 9 pull-request workflows passed on that exact head. PR #16 merged into `main` at `f5df77697b667f14df55583d94058f175ece5074` on 2026-09-17. The subsequent Phase 0, Phase 4 and Phase 9 push workflows on that merge were also observed completing successfully before final cleanup.

The accepted dependency/build baseline is Playwright 1.63.0, pypdf 6.19.0, setuptools 84.0.0, PyInstaller 6.22.3, pytest 9.1.1 and pip-audit 2.10.1.

No failed safety condition was waived.

## Current live-provider evidence

The live-provider acceptance remains intentionally read-only. It verifies current supported form recognition and the default live-write guard, while controlled loopback fixtures exercise writes. Any current page exposing CAPTCHA/challenge, authentication, payment, assessment, unsupported required inputs or ambiguous submit controls remains ineligible for measured submission.

## Measured pilot still pending

Technical acceptance did **not** fill or submit a real employer form. CI uses controlled loopback writes plus read-only live provider checks only.

The remaining Phase 9 product gate is a measured real-world pilot from the user's local/private JobPilot data. Pilot evidence must record, at minimum:

- number of individually armed applications;
- confirmed real submissions;
- blocked/unsupported applications and blocker reasons;
- mandatory-answer review stops;
- stale-package stops;
- `UNCERTAIN` outcomes;
- elapsed/local-day throughput and quality observations.

The visible 50/day objective remains a target only. Phase 9 cannot be marked complete and the product cannot claim 50 confirmed applications/day until measured real-pilot evidence supports that statement.
