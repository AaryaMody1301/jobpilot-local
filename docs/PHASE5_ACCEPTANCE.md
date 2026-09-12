# Phase 5 acceptance

Phase 5 adds public job discovery, normalization, local eligibility/matching, conservative deduplication, and explainable ranking. It does **not** open employer application forms or submit applications.

## Discovery boundary

- Supported public feeds are Greenhouse Job Board GET, Lever Postings GET, and Ashby public Job Postings GET.
- JavaScript does not fetch remote content. Python performs explicit HTTPS requests and validates the response shape before normalization.
- Board identifiers contain only simple slug characters. User-added boards are persisted only after their public endpoint returns a supported payload.
- The versioned starter registry contains one verified board for each supported provider and may be extended through the UI.
- Manual jobs require employer, title, description, and an absolute credential-free HTTP(S) source URL.
- Job text and ATS payloads are untrusted data. They never become instructions.

## Matching boundary

Hard eligibility and evidence ranking are separate.

A job is ineligible when a known hard condition conflicts with targeting, including an excluded employer, non-target role title, known non-permanent employment, explicit minimum experience above the configured target, disallowed India office location, disabled overseas relocation, explicit lack of required sponsorship, or explicit US-only remote work.

Unknown mandatory employment/location/origin/sponsorship information is `review`, not silently accepted or rejected.

Required/preferred statements are extracted deterministically from explicit requirement language. Evidence coverage uses only current `approved` facts whose backing source still verifies. The numeric ranking is only an ordering aid with visible component reasons; it is not labelled an ATS score or interview probability.

Duplicates are removed conservatively by exact provider/board/job identity and exact normalized content identity. Similar titles are not guessed to be duplicates.

## Compact implementation rule

Phase 5 follows the repository's Ponytail-style rule:

- no new runtime dependency for JSON GETs; Python stdlib `urllib` is sufficient;
- one discovery/matching/store module rather than speculative provider class hierarchies;
- one small UI layer reuses the existing Phase 4 shell;
- checks target payload trust boundaries and product decisions rather than implementation-detail coverage.

## Focused checks

The Phase 5 workflow must pass, on the final head:

1. Python and bundled JavaScript syntax validation;
2. the existing `pytest -m "not external"` regression suite, including one focused Phase 5 test module covering the three provider payload shapes plus eligibility/evidence/dedup decisions;
3. `scripts/phase5_discovery_acceptance.py`, which reads one verified public board from Greenhouse, Lever, and Ashby and requires each response to normalize successfully;
4. source self-test and hidden WebView2/pywebview smoke, including the injected Phase 5 jobs UI;
5. PyInstaller onedir build plus packaged self-test and packaged hidden-window smoke.

The existing Phase 0-4 pull-request workflows remain independent regression gates. No check may be waived to mark Phase 5 complete.

## Phase 4 sequencing exception

The Phase 4 technical implementation is merged, but its private five-real-resume human gate remains independently authoritative until proven complete by the local gate report. On 2026-09-12 the user explicitly authorized Phase 5 development before that private gate was recorded complete. This exception changes development order only: Phase 5 does not enable automatic tailoring by itself and employer submission remains disabled.

## Completion boundary

Phase 5 may be marked complete when the final branch head passes the focused Phase 5 workflow and the existing Phase 0-4 PR regression workflows. Phase 6 must not start without a later explicit user request.
