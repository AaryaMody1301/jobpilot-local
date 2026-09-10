# Phase 2 acceptance

Status: **implementation accepted against controlled fixtures; real-resume acceptance pending**.

Phase 2 must remain marked `[!] blocked/partial` until the user's actual LaTeX source and all required local dependencies pass this workflow.

## Functional acceptance

The Phase 2 implementation must demonstrate all of the following without enabling AI tailoring or employer submission:

- master `.tex` import uses a native desktop selection and makes an app-owned immutable byte copy;
- imported source is SHA-256 verified and source tampering is detected;
- changed source bytes create a new retained source version;
- supporting evidence files are registered as immutable hashed sources;
- candidate editable regions retain source line ranges and raw hashes, begin non-editable, and require explicit mapping confirmation;
- any region change invalidates prior mapping confirmation;
- automatically detected statements enter the fact bank as candidates, never approved facts;
- fact correction creates a new version under the same stable ID;
- fact approval rechecks backing-source integrity;
- no onboarding-ready state is possible while candidate facts remain unresolved;
- app-managed Tectonic is version/checksum pinned and downloaded only through an explicit action;
- cache population requires explicit network permission;
- the same baseline must subsequently compile with `--only-cached --untrusted`;
- baseline metadata records page count/geometry, PDF and extracted-text hashes, source metrics, and compile outcome;
- onboarding changes occur only while the desktop session is Idle;
- Close can cancel an app-owned Tectonic install/compile without introducing a background scheduler;
- Phase 1 Start/Pause/Stop/reopen behavior remains intact;
- source and packaged pywebview/WebView2 bridges expose the Phase 2 UI successfully.

## Controlled Windows evidence

Accepted code run: GitHub Actions `34467708811` on commit `5d1f54c20c4ff224caaa2b5206ffbad0aabf61d4`.

Results:

- Python 3.13.15 environment and pinned dependencies: passed;
- Playwright Chromium installation: passed;
- Python and JavaScript syntax validation: passed;
- `pytest -m "not external"`: **67 passed, 1 skipped, 2 deselected**;
- real app-managed Tectonic 0.17.0 installation: passed;
- first controlled compile with package-cache network access: passed;
- second controlled compile using cached resources only: passed;
- controlled baseline: **1 page**, PDF/text hashes recorded;
- controlled template map: **confirmed**;
- controlled fact review: **3 approved, 0 candidate**;
- controlled onboarding-ready gate: **true**;
- source self-test: passed;
- source hidden Edge/WebView2 smoke: passed;
- PyInstaller 6.22.2 onedir build: passed;
- packaged self-test: passed;
- packaged hidden Edge/WebView2 smoke: passed;
- overall workflow: **success**.

The Tectonic network-enabled run was intentionally not accepted as offline-ready. Only the subsequent cached-only compile set `offline_verified=true`.

## Failures caught during implementation

- An obsolete Phase 1 UI test expected literal `PHASE 1`. The test was corrected to preserve the actual invariant—local assets, no HTTP/HTTPS, no `fetch`, no XHR, sample-only lifecycle—while accepting the Phase 2 header.
- The first real Tectonic gate test approved only one of three controlled candidate facts and correctly failed `onboarding_ready`. The acceptance script was fixed to resolve every candidate; the production gate was not weakened.

## Real-resume acceptance still required

The user must provide the actual `.tex` master and any files it references. Phase 2 completion then requires:

1. immutable import and matching stored SHA-256;
2. exact dependency/source-reference inspection;
3. original-template compile with explicitly approved cache population only if necessary;
4. successful cached-only recompile;
5. page count/layout review against the original resume expectations;
6. review of candidate editable regions, including explicit support for any custom resume macros rather than silent template edits;
7. correction/approval/rejection of every candidate fact;
8. final `onboarding_ready=true` with no unsupported template/compiler workaround.

If Tectonic cannot compile the real template without a compiler/layout change, report the exact incompatibility and do not change compiler, template, margins, fonts, or structure without explicit user approval.
