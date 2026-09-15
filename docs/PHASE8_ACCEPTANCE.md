# Phase 8 acceptance

## Boundary

Phase 8 connects the existing discovery, matching, tailoring, review, application and history components into one explicit-session workflow. It does **not** authorize real employer submission.

Real Greenhouse, Lever and Ashby pages remain read-only in Phase 8. The provider adapters may inspect supported hosts, fields and blockers, but their write methods still fail closed outside app-controlled loopback fixtures. Any real-application activation/pilot belongs to Phase 9 and requires separate explicit user authorization.

The private Phase 4 five-real-resume gate also remains independently authoritative. Later-phase development authorization does not count as those approvals and does not enable automatic tailoring.

## Implementation

Phase 8 reuses existing modules rather than adding another orchestration framework:

- Phase 5 `JobStore`, public-board retrieval, deduplication, hard eligibility and evidence-backed scoring;
- Phase 4 `TailoringService`, deterministic resume validation, audit packages, stale-context checks and human/automatic-tailoring gates;
- Phase 3 model/resource manager and one-inference ownership;
- Phase 6 application journal/state machine, exact-context answer review, single submission worker, duplicate prevention, crash recovery and irreversible submit/confirm boundary;
- Phase 7 Greenhouse, Lever and Ashby hosted-form adapters.

Additive migration `009_phase8_orchestration.sql` extends `application_attempts` with orchestration links/metadata and adds `application_packages`. SQLite remains authoritative and existing explicit transactions serialize multi-table state changes.

### Eligibility and attention

A discovered job is persisted at `DISCOVERED`, moves through `ELIGIBILITY_CHECK`, and then uses the existing Phase 5 result:

- hard eligibility failure -> `INELIGIBLE`;
- unknown mandatory condition -> `NEEDS_REVIEW` until a recorded human eligible/ineligible decision;
- eligible -> `ELIGIBLE` and may proceed toward tailoring.

No eligibility rule is relaxed to improve volume.

### Tailoring and resource gates

Phase 8 will not run unattended tailoring without a selected validated local model. It reuses the Phase 4 review-context binding and automatic-tailoring gate. Until automatic tailoring is current, first-five review work remains bounded by the existing human-review requirement.

Critical memory pressure pauses new tailoring at a safe pre-submit checkpoint. It does not select weaker validation, skip review, or lower evidence requirements.

### Immutable application package and staleness

A prepared application package records a canonical manifest tying together:

- the discovered job ID/provider/source identity/content hash/apply URL;
- the linked tailoring run and its manifest/PDF/master/fact-bank/model/runtime/device/review-context evidence;
- the current exact-context approved application-answer fingerprint.

The package manifest is SHA-256 hashed. Freshness is verified before a controlled package enters the queue and again before the existing single submission worker claims it. The attempt becomes `STALE` instead of submitting when the job is inactive/changed, the tailoring run/audit evidence is stale or fails integrity checks, the tailored PDF/manifest changed, or approved application answers changed.

Unknown mandatory application questions still use the Phase 6 attention lane. When multiple unknown mandatory answers exist, the package is refreshed only after all are resolved and the attempt has safely returned to `QUEUED`.

### Submission boundary

Only the existing application worker can cross `READY_TO_SUBMIT -> SUBMITTING`. Phase 8 does not add another worker or retry path. Development submission targets remain absolute credential-free loopback HTTP(S) URLs. Explicit positive confirmation is required for `CONFIRMED`; ambiguity after submit remains terminal `UNCERTAIN` and is never automatically retried.

### Live provider recognition

A prepared real-employer package may be inspected read-only while Idle. Supported providers reuse the Phase 7 adapter `inspect()` method. Phase 8 records fields, blockers and submit-control shape but exposes no live fill/submit action. Unsupported providers are reported as unsupported rather than guessed.

### Daily objective and history

The Phase 8 UI adds persisted application history and an attention lane for eligibility reviews, tailoring prerequisites/reviews, stale/blocked/uncertain outcomes, live blockers and Phase 9 activation waits.

The local-calendar-day objective is 50 **confirmed real** applications. Confirmed controlled fixtures are displayed separately and excluded. The target is not a ceiling and no orchestration logic weakens eligibility, approved-fact, validation or review gates to reach it.

## Focused acceptance

Accepted runtime code head: `5b2a10827a2b81533a2017dd9828395ded91a383`.

Accepted Windows workflow run: `34946104772` on 2026-09-15.

The focused Phase 8 acceptance uses only a loopback form. It proved:

1. an eligible discovered-job snapshot can link to a validated prepared resume package;
2. the immutable package is freshness-checked before queue entry;
3. the existing worker detects two unknown required fields and pauses at `NEEDS_REVIEW`;
4. approving the first answer does not prematurely requeue the attempt;
5. approving the final required answer safely returns the attempt to `QUEUED` and refreshes the immutable package with the current answer fingerprint;
6. the single controlled worker fills approved answers, persists the irreversible submit boundary, submits once and requires an explicit positive confirmation;
7. the confirmed fixture is counted as controlled and does not increment the real local-day 50 target.

A separate focused unit check changes the approved-answer set after a package was queued. The next claim refuses the stale package and moves the attempt to `STALE` before any browser submit work.

## Full accepted Windows evidence

Run `34946104772` passed:

- Python and bundled JavaScript syntax validation;
- non-external regression suite: **129 passed, 1 skipped, 2 deselected**;
- focused Phase 8 controlled end-to-end orchestration acceptance;
- inherited Phase 7 controlled/live-read-only acceptance for Greenhouse, Lever and Ashby;
- source self-test;
- hidden Edge WebView2/pywebview Phase 8 bridge/UI smoke;
- PyInstaller onedir build;
- packaged self-test;
- packaged hidden-window smoke.

The inherited live provider evidence on this head remained:

- Greenhouse/GitLab: 29 visible application fields, blocker `captcha`, live write guard true;
- Lever/Nium: 11 visible application fields, blocker `captcha`, live write guard true;
- Ashby/Ashby: 26 visible application fields, blocker `captcha`, live write guard true.

All three current live examples were therefore recognized but conservatively unsupported for automatic submission. This is an expected safety result, not a waived acceptance condition.

## Development issues resolved

The first Phase 8 workflow run reached the new unit test successfully but six older migration tests still expected the repository migration list to end at `008_phase6_applications.sql`. Those bookkeeping assertions were updated for additive migration `009_phase8_orchestration.sql`; migration behavior was not hidden or weakened.

The same repair tightened multi-question application-answer handling so an immutable package refresh occurs only after all mandatory review questions are resolved. The repaired exact head passed the complete workflow. No failed safety check was waived.

## Next boundary

Phase 9 may begin only after a later explicit user request. It owns clean-machine packaging/setup/upgrade/backup/restore/notices and, separately, explicit real-application activation plus a measured pilot. Phase 8 acceptance does not authorize real employer filling or submission.
