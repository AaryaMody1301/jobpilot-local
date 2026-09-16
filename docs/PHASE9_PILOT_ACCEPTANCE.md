# Phase 9 measured-pilot activation acceptance

Date: 2026-09-16

Status: **accepted for the user-authorized real-application write-path implementation and post-audit technical hardening only**. The measured real-world pilot has not yet been run, no real employer form was filled/submitted by this acceptance, and Phase 9 remains in progress.

## Authorization boundary

After the Phase 9 distribution/recovery PR was merged, the user gave a later separate instruction to start the next Phase 9 boundary. That instruction authorizes implementation of the measured real-application pilot path.

Authorization does not waive any existing product gate. In particular:

- Phase 4 automatic tailoring still requires five distinct explicitly approved real tailored resumes under the current validation context;
- job eligibility must be resolved rather than guessed;
- the immutable application package must still be current immediately before claim/write;
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
15. the adapter compares confirmation state against a pre-submit baseline, and only newly observed positive confirmation after the click can produce `CONFIRMED`;
16. submit exceptions or missing positive confirmation after the click become `UNCERTAIN`.

Optional live fields are left unchanged unless an exact-context approved answer already exists. The pilot does not synthesize or guess application answers.

## Provider/API boundary

The public employer APIs are not treated as applicant credentials:

- Greenhouse's application POST is an employer/custom-career-site integration authenticated with the employer's Job Board API key;
- Lever's programmatic apply path similarly requires employer/admin integration credentials and its hosted application form remains the normal applicant surface;
- Ashby's application submission API requires candidate-write API permissions.

JobPilot therefore continues through the supported hosted applicant forms and keeps provider-specific host/blocker recognition in front of the write path. The code does not ask the candidate for an employer API key and does not bypass CAPTCHA or other challenges.

## Original technical acceptance

Accepted technical head: `06a2f31d47dc3dbe09bcf0eda3fd34bf0278d0e5`

Windows workflow: `35072562186` (`Phase 9 acceptance`), conclusion `success`.

The original exact-head workflow passed the then-current non-external regression, focused pilot safety, backup/restore, Phase 8 orchestration, Phase 7 provider recognition/controlled-submit, source/frozen/installed desktop, browser, distribution and install/upgrade checks.

That acceptance did not exercise the real resume-upload path end-to-end and did not require post-submit confirmation to be new relative to a baseline. A later release audit found those gaps before a measured pilot was run.

## Post-audit hardening acceptance

PR #15 fixes the two release blockers identified by that audit:

- `LiveHostedFormEngine` now reads the persisted `pdf_relpath`, resolves it only through `TailoringStore.absolute_path()`, requires the stored `pdf_sha256`, and re-hashes the file immediately before browser upload. Missing, escaped or tampered artifacts fail closed before any employer write.
- hosted-form confirmation now captures the pre-submit URL, explicit success-marker count and known success phrases during inspection. After the click, `CONFIRMED` requires newly appearing success evidence; success-like text that was already on the page does not count.

Focused regression coverage verifies both the managed resume path/hash boundary and the static-success-text false-positive case.

The same hardening refreshes the validated release dependencies to Playwright 1.63.0, pypdf 6.18.1 and PyInstaller 6.22.3, adds pinned `pip-audit` 2.10.1, updates the bundled browser notices to Playwright Chromium revision 1243 / Chrome for Testing 153.0.8010.12, corrects the packaged pilot README, and runs the Phase 9 acceptance workflow on final `main` pushes.

Exact hardening head: `75205774ad8cf444fe9081073b59c3e951849a50`.

All Phase 0 through Phase 9 workflows passed on that exact head. Key runs:

- Phase 3: `35077829489` — real local llama.cpp/model acceptance passed;
- Phase 4: `35077829627` — real local tailoring acceptance, source/package self-tests and window smokes passed;
- Phase 7: `35077829494` — controlled submit plus current Greenhouse/Lever/Ashby live read-only recognition passed;
- Phase 8: `35077829506` — orchestration and stale-package boundaries passed;
- Phase 9: `35077829573` — dependency audit, deterministic regression suite, focused pilot/hardening tests, backup/restore, inherited provider/orchestration gates, source/frozen/installed smokes, hermetic browser build, verified distribution, clean install/upgrade and artifact upload all passed.

The hardening Actions artifact is `jobpilot-local-phase9-windows-x64`, artifact ID `10439455880`, 381,619,153 bytes, digest `sha256:b10e206459f58fe479a72941769e6b71cc187c38a0b1afe467ceec172afdff2d`.

No failed safety condition was waived.

## Current live-provider evidence

The live-provider acceptance remains intentionally read-only. It verifies current supported form recognition and the default live-write guard, while controlled loopback fixtures exercise writes. Any current page exposing CAPTCHA/challenge, authentication, payment, assessment, unsupported required inputs or ambiguous submit controls remains ineligible for measured submission.

## Measured pilot still pending

This technical acceptance did **not** fill or submit a real employer form. CI uses controlled loopback writes plus read-only live provider checks only.

The remaining Phase 9 product gate is a measured real-world pilot from the user's local/private JobPilot data. Pilot evidence must record, at minimum:

- number of individually armed applications;
- confirmed real submissions;
- blocked/unsupported applications and blocker reasons;
- mandatory-answer review stops;
- stale-package stops;
- `UNCERTAIN` outcomes;
- elapsed/local-day throughput and quality observations.

The visible 50/day objective remains a target only. Phase 9 cannot be marked complete and the product cannot claim 50 confirmed applications/day until measured real-pilot evidence supports that statement.
