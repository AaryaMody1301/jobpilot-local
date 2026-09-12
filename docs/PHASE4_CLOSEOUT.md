# Phase 4 closeout

Status: **implementation merged; human completion gate pending verification**.

This record reconciles the final audited Phase 4 implementation with the repository state after PR #7 was merged on 2026-09-12.

## Final audited implementation evidence

PR #7 final head: `582a00797bf68fe8d5d1d7076905c9e88c86d0e2`.

All pull-request-context Phase 0-4 workflows passed on that exact head. Phase 4 Windows run `34598042842` recorded:

- Python/JavaScript syntax validation passed;
- `pytest -m "not external"`: **123 passed, 1 intentional platform-guard skip, 2 external probes deselected**;
- real controlled local Qwen3 4B CPU inference and cached-only Tectonic tailoring passed;
- instruction-like JD text remained untrusted data;
- hidden Unicode in JD text and model replacement text was blocked/normalized as designed;
- evidence-derived anti-keyword-stuffing checks passed;
- one validated wording edit was backed by one field-linked approved fact reference;
- page count remained unchanged and no overflow was detected;
- expected PDF content validation passed and the UI reads the persisted validation field;
- controlled run status remained `needs_review`;
- controlled human gate remained 0/5; automatic tailoring remained disabled;
- Phase 5 discovery and employer submission remained disabled;
- source/package self-tests, WebView2 smokes and PyInstaller onedir build passed.

The controlled CI result never counts as one of the five human approvals.

## Merge-state correction

PR #7 was merged as implementation even though its own human-completion gate was open. Therefore:

- **merged** means the Phase 4 implementation is present on `main`;
- **complete** still requires five distinct real human-approved tailored resumes under one unchanged current review context;
- Phase 5 must remain disabled until that gate is verified complete.

## Privacy-safe local gate verification

The authoritative five-resume approvals live in the private local SQLite database under `%LOCALAPPDATA%\JobPilotLocal`; private resume/JD/fact values are intentionally not committed.

Run:

```powershell
python -m jobpilot.app.main --phase4-gate-report
```

The report intentionally exposes only phase/gate/model-status booleans and counts. It does not expose JD text, resume content, fact values, PDFs, source paths, or audit-package contents.

Exit codes:

- `0`: the persisted 5/5 gate is complete **and current** for the selected validated master/facts/profile/template/baseline/model/runtime/device/evaluation context;
- `2`: the gate is missing, incomplete, invalidated, or stale.

A successful report is necessary to close Phase 4. It does not enable employer submission or Phase 5 by itself.

## Exact remaining human procedure

If the report is not complete:

1. open JobPilot on the Windows machine holding the private local profile;
2. confirm resume/fact onboarding and selected local model remain valid;
3. paste a real job description manually;
4. generate the tailored resume locally;
5. inspect PDF, wording diff, JD keyword mapping, fact references and deterministic validation;
6. approve only if the output is accurate, otherwise reject/correct/regenerate;
7. repeat until five **distinct** real resumes are approved under one unchanged review context;
8. rerun `--phase4-gate-report` and require exit code `0`;
9. only then update `ROADMAP.md` / `PROGRESS.md` from Phase 4 `[!]` to `[x]` and begin Phase 5 on a later explicit request.

## CI closeout repair

The Phase 4 workflow now runs on:

- pushes to `main`;
- pushes to `phase-4-*` branches;
- pull requests targeting `main`;
- manual `workflow_dispatch`.

This ensures future merged Phase 4 baseline changes receive the same acceptance path instead of relying only on the pre-merge PR head.
