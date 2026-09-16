# Phase 9 measured-pilot activation acceptance

Date: 2026-09-16

Status: **accepted for the user-authorized real-application write-path implementation only**. The measured real-world pilot has not yet been run, no real employer form was filled/submitted by this acceptance, and Phase 9 remains in progress.

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
12. the current tailored PDF is uploaded only to a recognized resume/CV file field; another required file upload blocks instead of guessing;
13. missing mandatory non-file answers move the application to the existing `NEEDS_REVIEW` lane using exact live-field context fingerprints;
14. the final pre-submit boundary checks Stop/deactivation again before the click;
15. submit exceptions or missing positive confirmation after the click become `UNCERTAIN`.

Optional live fields are left unchanged unless an exact-context approved answer already exists. The pilot does not synthesize or guess application answers.

## Provider/API boundary

The public employer APIs are not treated as applicant credentials:

- Greenhouse's application POST is an employer/custom-career-site integration authenticated with the employer's Job Board API key;
- Lever's programmatic apply path similarly requires employer/admin integration credentials and its hosted application form remains the normal applicant surface;
- Ashby's application submission API requires candidate-write API permissions.

JobPilot therefore continues through the supported hosted applicant forms and keeps provider-specific host/blocker recognition in front of the write path. The code does not ask the candidate for an employer API key and does not bypass CAPTCHA or other challenges.

## Technical head and Windows acceptance

Accepted technical head: `06a2f31d47dc3dbe09bcf0eda3fd34bf0278d0e5`

Windows workflow: `35072562186` (`Phase 9 acceptance`), conclusion `success`.

The exact-head workflow passed:

- Python and bundled JavaScript syntax validation;
- complete non-external regression suite: **135 passed, 1 skipped, 2 deselected**;
- four focused pilot safety tests covering explicit host-scoped live write mode, per-launch activation reset, explicit arming/re-arming, and CAPTCHA-blocked inspection rejection;
- portable backup/restore acceptance while proving the authorized pilot remains inactive after launch/restore;
- inherited Phase 8 controlled orchestration/staleness acceptance;
- inherited Phase 7 Greenhouse/Lever/Ashby controlled-submit plus current live read-only recognition/write-guard acceptance;
- source Phase 9 self-test and hidden WebView2/pywebview UI smoke;
- hermetic Playwright Chromium PyInstaller build;
- frozen self-test, browser smoke and hidden-window smoke without a global Playwright browser environment;
- verified Windows distribution creation;
- clean per-user install and in-place upgrade with private-data preservation;
- installed application self-test, bundled-browser smoke and hidden-window smoke;
- Windows x64 distribution artifact upload.

The built release archive was 377,754,213 bytes with archive SHA-256 `3d3d85c796d7c7475557e8432c82ae856299d27819de937ed5a4abd74ed5a6b3`. The Actions artifact was uploaded as `jobpilot-local-phase9-windows-x64` (artifact ID `10437151583`) with Actions artifact digest `sha256:31c837ebf5f10b95da628584eeef516ba6e5f1b2c4a417ca4d06bc2ed2056ebf`.

## Current live-provider evidence

The inherited live read-only check on the accepted technical head remained conservative:

- Greenhouse/GitLab: 29 visible fields, CAPTCHA blocker, default live write guard active;
- Lever/Nium: 11 visible fields, CAPTCHA blocker, default live write guard active;
- Ashby/Ashby: 26 visible fields, CAPTCHA blocker, default live write guard active.

Controlled loopback confirmations still passed for all three. Those specific live examples are therefore not eligible for automatic pilot submission, and acceptance did not weaken that result.

## Development findings repaired before acceptance

The first pilot development run failed the inherited Phase 7 gate even though current form recognition still worked. The cause was an accidental change to the exact fail-closed exception wording asserted by the established provider contract. The original `adapter writes are disabled for live employer pages` contract was restored; the new live-write capability exists only behind the separate explicit `allow_live_submit=True` mode used by the armed pilot worker.

A separate design review found that a live application armed before restart/deactivation could otherwise remain queued for a later activation. The repair restricts live claiming to the current launch's armed IDs and rewinds queued live work to `PREPARED` whenever activation resets. The old read-only inspection is also cleared, forcing a new current-launch inspection before re-arming.

No failed safety condition was waived.

## Measured pilot still pending

This technical acceptance did **not** fill or submit a real employer form. CI uses controlled loopback writes plus read-only live provider checks only.

The next Phase 9 boundary is a measured real-world pilot from the user's local/private JobPilot data. Pilot evidence must record, at minimum:

- number of individually armed applications;
- confirmed real submissions;
- blocked/unsupported applications and blocker reasons;
- mandatory-answer review stops;
- stale-package stops;
- `UNCERTAIN` outcomes;
- elapsed/local-day throughput and quality observations.

The visible 50/day objective remains a target only. Phase 9 cannot be marked complete and the product cannot claim 50 confirmed applications/day until measured real-pilot evidence supports that statement.
