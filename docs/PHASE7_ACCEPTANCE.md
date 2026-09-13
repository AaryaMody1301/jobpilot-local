# Phase 7 acceptance - supported hiring-platform adapters

Date: 2026-09-13

Accepted code head: `3a95d0a32755c94b21ec77c209749986718167a6`

Accepted Windows workflow run: `34745312735`

## Scope

Phase 7 implements the provider-specific hosted-form recognition boundary only. It does not connect those adapters to the Phase 6 application worker; end-to-end orchestration remains Phase 8. It does not authorize or perform real employer submissions; explicit real-application activation and pilot evidence remain Phase 9.

The roadmap order was enforced:

1. Greenhouse passed controlled submission/confirmation plus read-only current-form recognition before Lever work started.
2. Lever passed the same gates before Ashby work started.
3. Ashby passed the same gates before Phase 7 closeout.

Unsupported variants are reported, not guessed.

## Provider contracts

### Greenhouse

Supported live hosts:

- `job-boards.greenhouse.io`
- `boards.greenhouse.io`

Official Job Board API documentation distinguishes public job-board GET access from application POST, which requires employer credentials. JobPilot therefore uses public discovery plus visible hosted-form recognition and does not use an employer-authenticated application POST API.

Reference: https://developers.greenhouse.io/job-board.html

### Lever

Supported live hosts:

- `jobs.lever.co`
- `jobs.eu.lever.co`

Lever's public Postings API exposes hosted job/application URLs, while direct application submission requires authenticated API access and is rate-limited. Lever's own documentation recommends its hosted application form for normal candidate applications. JobPilot therefore recognizes the hosted form and does not build an authenticated application API client.

References:

- https://github.com/lever/postings-api
- https://hire.lever.co/developer/documentation

### Ashby

Supported live host:

- `jobs.ashbyhq.com`

Ashby's public Job Postings API exposes `jobUrl`/`applyUrl`; `applicationForm.submit` requires `candidatesWrite`. JobPilot therefore recognizes the public hosted application page and does not use the authenticated submit API.

References:

- https://developers.ashbyhq.com/docs/public-job-posting-api
- https://developers.ashbyhq.com/reference/applicationformsubmit

## Write boundary

The same adapter classes have two explicit modes:

- live mode: exact supported provider hosts, read-only recognition only;
- controlled mode: localhost/loopback only, used by acceptance to exercise fill/submit/confirmation.

`fill()` and `submit()` fail closed unless controlled mode is enabled and the current page is still loopback. Calling `submit()` during live recognition is used only to prove the guard raises before any click.

No real employer form was filled or submitted by Phase 7 acceptance.

## Form recognition

The shared adapter recognizes visible:

- text, email, telephone, URL, number and date inputs;
- file inputs;
- checkbox and radio inputs;
- textarea and select controls;
- required state from browser-required/ARIA/visible required markers;
- exactly one supported visible submit control.

Required unsupported controls become blockers. Values are never inferred from field position or silently guessed.

## Conservative blockers

Phase 7 reports and stops on:

- CAPTCHA integrations;
- password/one-time-code login or verification challenges;
- assessment/test controls;
- actual card/billing/payment controls;
- unsupported required controls;
- missing or ambiguous submit controls.

A live Nium form exposed an ordinary field whose name contained `payment`. An early detector incorrectly classified that wording as a payment request. The accepted code narrows payment detection to actual credit-card/payment controls and hosted payment frames. The controlled acceptance includes an optional `payment_experience` field to prove ordinary employment wording does not trigger the blocker.

## Sequential acceptance evidence

### 7A Greenhouse

Accepted before Lever implementation:

- code head: `87c9138157f5ed42e0c4772e747867070e53a114`
- Windows run: `34744776048`
- controlled loopback fill/submit/explicit confirmation: passed
- current GitLab Greenhouse hosted-form recognition: passed read-only
- live write guard: passed
- regression/source/package checks: passed

### 7B Lever

Accepted before Ashby implementation:

- code head: `6e350b76fe284441436978d3ee71d69028d8b014`
- Windows run: `34744964533`
- Greenhouse and Lever controlled/live recognition gates: passed
- current Nium Lever hosted-form recognition: passed read-only
- live write guard: passed
- regression/source/package checks: passed

### 7C Ashby and final classifier repair

Final accepted head:

- code head: `3a95d0a32755c94b21ec77c209749986718167a6`
- Windows run: `34745312735`

Passed:

- Python and bundled JavaScript syntax validation;
- complete non-external regression suite: 128 passed, 1 skipped, 2 deselected;
- controlled loopback fill/submit/positive-confirmation acceptance for Greenhouse, Lever and Ashby;
- read-only current hosted-form recognition for all three providers;
- live write guards for all three providers;
- source self-test and hidden WebView2/pywebview smoke;
- PyInstaller onedir build;
- packaged self-test and packaged hidden-window smoke.

## Current live evidence

The final accepted run recognized these current application pages without writing to them:

- Greenhouse / GitLab: `https://job-boards.greenhouse.io/gitlab/jobs/8556658002` - 29 visible fields, one submit control, blocker `captcha`;
- Lever / Nium: `https://jobs.lever.co/nium/b74e88a1-896b-4366-a0c2-cb159d803840/apply` - 11 visible fields, one submit control, blocker `captcha`;
- Ashby / Ashby: `https://jobs.ashbyhq.com/ashby/7458d4e9-da2e-47bd-98cb-adfda43d42b2/application` - 26 visible fields, one submit control, blocker `captcha`.

Therefore all three current examples are **recognized but unsupported for automatic submission** under the product's CAPTCHA stop rule. This is the intended conservative outcome. No CAPTCHA solving or bypass is implemented.

## Check rationale

Phase 7 deliberately uses one consolidated provider acceptance rather than a provider-by-provider test matrix. It checks the consequential boundaries:

- provider host recognition;
- controlled write permission;
- fill + submit + explicit confirmation;
- current live form recognition;
- fail-closed live writes;
- challenge/blocker classification;
- ordinary `payment` wording does not masquerade as a billing control.

The existing non-external regression suite and desktop/package smokes remain the integration safety net. No test was added merely to increase count.

## Remaining boundaries

- Phase 4's private five-real-resume review gate remains authoritative.
- Phase 8 must connect discovery, matching, tailoring/gates, queues, attention/history, provider adapters and application execution.
- Phase 9 requires separate explicit user authorization before any real-application pilot.
- `UNCERTAIN` remains terminal for automatic retry.
