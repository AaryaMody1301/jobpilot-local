# Progress

## Current phase

Phase 2 - resume import and approved fact bank.

Status: **implemented and controlled-fixture verified; blocked/partial pending the user's actual LaTeX resume** as of 2026-09-10. Phase 0 and Phase 1 are complete and merged to `main`. Phase 3 has not started.

## Verified repository state at phase start

- Re-read `SPEC.md`, `ROADMAP.md`, `DECISIONS.md`, `PROGRESS.md`, and `AGENTS.md` from the merged repository.
- `main` at Phase 2 start: `273b49fa4fe73e3900b11c96e8d965cee769ecaf`, merge of Phase 1 PR #2.
- Phase 2 branch: `phase-2-resume-fact-bank`.
- Existing Phase 0/1 lifecycle, SQLite recovery, Windows Job Object, bundled pywebview UI, targeting settings, and packaging boundaries were preserved.

## Phase 2 work completed

- Added migration `003_phase2_resume_fact_bank.sql` for source documents, template maps/regions, resume baselines, facts/fact versions, and fact-bank revision.
- Added immutable master-resume and supporting-document imports. Files are copied byte-for-byte into `%LOCALAPPDATA%\JobPilotLocal`, SHA-256 verified, deduplicated by content, and never written back to the user's original source path.
- A changed master creates a new retained source version instead of mutating/deleting an older master.
- Added conservative candidate mapping for standard LaTeX `\item` bullets. Each region keeps source line range and raw-text SHA. Regions start non-editable; any mapping change invalidates a previous confirmation.
- Added versioned facts with stable fact IDs, source-document ID, source locator, source SHA, candidate/approved/rejected status, correction history, and fact-bank revision.
- Fact approval re-hashes its backing source first and is refused if the app-owned source is missing or modified.
- Added an explicit app-managed Tectonic 0.17.0 installer for Windows x64. The release archive is size/SHA-256 pinned and unpacked only into the app-owned tool directory.
- Added original-template baseline compilation through the app-owned process supervisor. Network-enabled cache population is an explicit action; offline readiness requires a later `--only-cached --untrusted` compile.
- Added pypdf baseline inspection for page count/page geometry plus PDF/text hashes. Extracted PDF text is a validation signal only; it is not the source of factual truth or assumed to preserve reading order.
- Added source metrics for section order, bullet count, document class, local external references, and shell-escape/write18 signal.
- Added Phase 2 UI for master/supporting import, compiler status, explicit cache actions, baseline state, editable-region confirmation, and fact correction/approval.
- File-system selection stays native: the webview bridge accepts paths only from the native file dialog, not arbitrary JavaScript strings.
- Resume onboarding changes are limited to Idle. Tectonic install/compile operations are cancellable on Close through the app-owned process boundary.
- `onboarding_ready` requires verified master integrity, compiled + cached-only verified baseline, confirmed template map, zero candidate facts, and at least one approved fact.
- Added controlled LaTeX fixture, migration regression tests, source tamper tests, fact-history tests, controlled UI tests, and a real Windows Tectonic acceptance script.

## Verification evidence

Windows GitHub Actions run `34467708811`, commit `5d1f54c20c4ff224caaa2b5206ffbad0aabf61d4`:

- Python **3.13.15** and all pinned project dependencies installed successfully.
- Matching Playwright Chromium installed successfully.
- Python bytecode compilation and `node --check src/jobpilot/ui/app.js` passed.
- `pytest -m "not external"` -> **67 passed, 1 skipped, 2 deselected in 9.13s**. The single skip is the intentional non-Windows installer guard because the job itself is Windows; the two deselected tests are explicitly external Phase 0 probes.
- Real Tectonic acceptance downloaded the pinned Tectonic 0.17.0 Windows x64 archive, populated the Tectonic support cache on the first compile, then recompiled the same controlled resume with cached resources only.
- Controlled Tectonic result: `tectonic_integrity=verified`, `page_count=1`, `offline_verified=true`, `template_map=confirmed`, `approved_facts=3`, `candidate_facts=0`, `onboarding_ready=true`.
- Source `--self-test` passed immutable resume import, fact-version persistence, supporting-source persistence, Phase 1 lifecycle/persistence, and no auto-resume.
- Source hidden Edge/WebView2 smoke passed and exposed the Phase 2 bridge.
- PyInstaller 6.22.2 onedir build completed successfully.
- Packaged `--self-test` passed the same source/persistence assertions.
- Packaged hidden Edge/WebView2 smoke passed.
- Entire workflow concluded `success`.

Two useful failures were found and fixed rather than waived:

1. The first Phase 2 run exposed an obsolete Phase 1 UI wording assertion. It was updated to preserve the actual safety invariant: local bundled assets, sample-only lifecycle, no HTTP/HTTPS, no `fetch`, and no XHR.
2. The next run proved the ready gate correctly rejects unresolved fact candidates. The controlled acceptance had approved only one of three facts; the script was fixed to resolve every candidate instead of weakening the gate.

## Limitations and boundaries

- The user's actual LaTeX resume has not been provided in this chat, so its Tectonic compatibility, page count, fonts, local includes, custom macros, and editable-region mapping are not yet established.
- Candidate region detection currently recognizes standard LaTeX `\item` bullets. Many resume templates define custom commands such as `\resumeItem`; if the actual source uses those, Phase 2 must add an explicit template-specific mapping adapter without changing the master template.
- The current native supporting-source picker accepts PDF/TXT/MD/TEX. If the real resume references `.cls`, `.sty`, fonts, images, or bibliography files, those dependencies must be handled explicitly after inspecting the actual source; JobPilot must not silently replace the compiler or layout.
- GitHub-hosted Windows acceptance uses Windows Server 2025 rather than an end-user Windows 10/11 installation. Clean-machine Windows 10/11 distribution testing remains Phase 9.
- No AI inference, job discovery, resume rewriting, browser form filling, or employer submission is enabled in Phase 2.
- No personal resume or supporting document has been committed to Git.

## Exact next step

Stop at the Phase 2 boundary. Obtain the user's actual `.tex` resume and any local files it references. Import it through the Phase 2 workflow, verify its immutable source hash, run the explicitly approved cache-populating Tectonic compile and then a cached-only compile, inspect exact page/layout/source dependencies, review and confirm the real editable-region mapping, and correct/approve or reject every candidate fact. Only after that real-source acceptance passes may Phase 2 be marked complete. Do not start Phase 3 before a later user request.
