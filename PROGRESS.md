# Progress

## Current phase

Phase 4 - Evidence-based resume tailoring.

Status: **technical implementation and controlled Windows acceptance complete; human review gate 0/5 remains, so Phase 4 is partial** as of 2026-09-11. Phases 0-3 are complete and merged. Phase 5 has not started.

## Verified repository state at Phase 4 start

- Re-read the actual `SPEC.md`, `ROADMAP.md`, `DECISIONS.md`, `PROGRESS.md`, and `AGENTS.md` and reconstructed the requirements from the prior project conversation before changing code.
- Verified Phase 3 PR #6 was merged into `main`; Phase 4 started from merged main commit `96d78e3813df3e44752571b29bdfd6e5789caa4d`.
- Found a pre-existing `phase-4-evidence-tailoring` branch already based on that merged Phase 3 commit. It was preserved and audited rather than reset or assumed correct.
- Created `phase-4-stage` for audit/fixes so the expensive pinned local-model acceptance did not run for every intermediate edit. The real Phase 4 branch was advanced only after a cohesive patch.
- No private resume source or approved personal fact values were committed to Git. The repository retains only controlled fixtures and the prior record that the user approved the factual claims in their private supplied resume.

## Phase 4 requirements preserved

- Manual JD input only. No job discovery is introduced in Phase 4.
- JD content is untrusted data; embedded instructions are ignored as commands and cannot override fact/template/validation rules.
- Resume edits must be evidence-backed by the approved fact bank. No invented skills, tools, years, responsibilities, employers, titles, dates, qualifications, metrics, work authorization, sponsorship, salary or other claims.
- Model output is structured content edits plus fact IDs/keywords; application code renders controlled LaTeX. Arbitrary model-generated LaTeX is not accepted.
- Preserve section order, bullet count, page count, page geometry, template structure, titles/dates and other immutable content. Unsupported/ambiguous/unsafe edits fail closed to original/review.
- Tailoring uses only cached Tectonic resources after the explicit Phase 2 setup boundary.
- Per-run evidence must include JD snapshot/source, `.tex`/PDF, diff, fact references/version, model/configuration evidence and validation.
- The first five **distinct real tailored resumes** for a selected model must be human-reviewed and approved before automatic tailoring can be activated. A replacement model repeats this gate.
- Stale facts/profile/template/baseline/model/validation evidence must not inherit previous approvals or enable automatic mode.
- No browser form filling, employer submission or Phase 5 discovery is enabled.

## Existing Phase 4 branch audit

The pre-existing branch already contained manual JD storage, structured local-model edits, a controlled renderer, cached-only Tectonic compilation, PDF preview/diff UI, a five-resume gate and a Windows workflow. It was not accepted as-is.

The first observed Windows run `34583541897` had four failures: two stale Phase 1 UI assertions and two Phase 4 tests that confused in-memory `TemplateRegion` fields with persisted database region fields. More importantly, the audit found safety gaps not covered by those failing tests:

1. pending tailored resumes tracked master/fact/model staleness but not confirmed template-map, offline-baseline or targeting/profile changes;
2. five-resume approvals were not bound to the validation context, so old approvals could survive a relevant profile/template/fact change;
3. tailored-run approval and distinct-key gate insertion were separate transactions;
4. audit packages lacked a tamper-evident manifest tying all required evidence files to the run;
5. PDF validation checked edited phrases but did not prove that other baseline content survived;
6. the evidence validator could combine approved facts from unrelated bullets when rewriting one field;
7. existing numeric/date/metric literals in an edited field could be dropped without a dedicated deterministic guard;
8. recorded JD source URLs had no syntax/credential safety validation.

No failed check was waived and no factual/resource gate was weakened.

## Phase 4 implementation

### JD trust boundary

- Manual JD text is normalized, capped and SHA-256 hashed.
- Instruction-like markers are recorded for review but remain data, never prompt authority.
- Optional source URLs are inert provenance only in Phase 4 and must be absolute HTTP(S), <=2000 characters, with no embedded credentials. Phase 4 never fetches them.

### Evidence-bound structured edits

- The local model receives the JD explicitly labelled untrusted, the approved editable fields, and approved source-linked facts.
- The response schema contains keyword mappings and plain-text edits with approved fact IDs; output is independently validated locally.
- Each edit must cite the approved fact linked to that exact LaTeX region. Claims from other resume bullets cannot be composed into the field.
- Every used keyword must appear in the JD and be supported by the cited field-linked fact.
- Replacement wording may use only content supported by the original field and its field-linked evidence.
- Existing numeric/date/metric literals are protected from silent removal.
- Only confirmed simple single-line `\\item` wording is automatically rendered. Model LaTeX commands/complex regions are rejected to manual review/original fallback.
- Application code escapes plain text and verifies that unedited lines and protected source metrics remain unchanged.

### Compile and PDF validation

- Tailored compilation requires the verified app-managed Tectonic and always uses the cached-only/untrusted command path; tailoring cannot populate the package cache.
- The stored master baseline PDF is checked against its recorded SHA-256 before comparison.
- Tailored page count and geometry must match the baseline; overfull boxes block acceptance.
- PDF extraction is used only as validation evidence. Because extraction order is not assumed stable, Phase 4 uses an expected token multiset: verified baseline text minus each edited before-phrase plus each validated after-phrase. Missing expected content blocks the run.

### Staleness and five-review gate

- Migration `006_phase4_tailoring_safety.sql` adds template-map, baseline, profile and review-context fingerprints plus audit-manifest metadata without rewriting already-existing migration `005`.
- A review-context fingerprint binds master hash, fact-bank revision, confirmed template-map fingerprint, offline-baseline fingerprint, targeting/profile fingerprint, and exact selected model/runtime/device + passing evaluation evidence.
- Pending review is rejected/staled if any bound evidence changes or fails integrity verification.
- Human approval and insertion of the distinct resume key are one SQLite transaction.
- If the review context changes, previous distinct approvals for that model are reset before a new-context approval counts.
- Duplicate resume keys count once. Approval revocation removes a gate contribution when no other approved run represents that key and reopens a gate below five.
- Automatic tailoring requires both a complete persisted 5/5 gate and an exact match between the gate's review-context fingerprint and the current validated environment.

### Tamper-evident run package

Generated runs store app-managed evidence including JD text/metadata, controlled LaTeX/PDF/log, diff, keyword mapping, fact references with versions/source locators, model/evaluation evidence, usage and deterministic validation. `manifest.json` records run/dependency identities and SHA-256/byte length for required components. Human approval re-verifies the source/PDF/manifest and each required manifest component, so modified/missing evidence cannot count toward the gate.

### UI and phase boundary

- Phase 4 desktop provides manual JD entry, optional inert source URL, local generation, diff/keyword/fact/validation display, PDF preview, approve/reject, and an explicit automatic-tailoring activation control gated by current 5/5 evidence.
- The UI loads bundled local assets, has CSP `connect-src 'none'`, and no JavaScript fetch/XHR path.
- Job discovery and employer submission flags remain false.

## Tests added/fixed

Regression coverage now includes:

- valid field-linked evidence and literal JD keyword mapping;
- malicious/unsupported skill rejection;
- unapproved, unmapped and cross-region fact rejection;
- protected numeric/date/metric preservation;
- LaTeX escaping and complex-command refusal;
- immutable unedited-line/template structure checks;
- invalid/credential-bearing JD source URLs;
- Phase 1 UI compatibility without weakening the no-network asset boundary;
- Phase 3->4 migration plus additive Phase 4 safety migration;
- fact-bank, targeting/profile, template-map and baseline staleness;
- review-context approval reset;
- duplicate distinct-resume counting;
- approval revocation/reopening;
- tampered audit-component refusal;
- previous Phase 0-3 lifecycle, process, resume and local-AI tests.

## Successful Windows technical acceptance

Run `34593289955`, code head `e15ae7dc4aed425cb2675921e2c119b1c961fa2a`:

- Python/JavaScript syntax validation passed;
- `pytest -m "not external"` -> **117 passed, 1 intentional platform-guard skip, 2 external probes deselected in 31.85s**;
- real controlled Phase 4 acceptance downloaded/verified the approved test catalogue, created an offline-verified Tectonic baseline, locally used the pinned Qwen3 4B CPU configuration, and processed a JD containing instruction-like malicious text;
- controlled tailoring result: **1 validated edit**, **1 fact reference**, instruction-like JD marker true, `--device none`, cached-only compile true, **page count 1 -> 1**, no overflow, status `needs_review`;
- review gate remained **0/5 (5 remaining)** and automatic tailoring remained false;
- job discovery false and employer submission false;
- source self-test passed;
- source hidden Edge/WebView2/pywebview smoke passed;
- PyInstaller onedir build passed;
- packaged self-test passed;
- packaged hidden-window smoke passed;
- workflow concluded `success`.

The controlled fixture demonstrates mechanics only. It is not one of the user's five human approvals.

## Current blocker / exact next step

Phase 4 is intentionally `[!] partial`, not complete. Technical implementation is ready for review, but the product requirement requires **five distinct real tailored resumes** for the selected validated local model/configuration to be reviewed and explicitly approved by the user under one unchanged review context.

The next user-facing work is therefore:

1. run/import the user's private approved master/fact bank in the local desktop;
2. supply a real JD manually;
3. generate the local tailored resume;
4. inspect PDF + diff + keyword/fact mapping + validation evidence;
5. approve it only if accurate, otherwise reject/correct facts and regenerate;
6. repeat with four more distinct JDs/resumes under the same current context.

Only when the persisted gate reaches current 5/5 may automatic tailoring be activated and Phase 4 marked complete. Phase 5 must remain untouched until then.
