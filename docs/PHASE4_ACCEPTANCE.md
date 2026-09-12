# Phase 4 acceptance

Phase 4 adds evidence-based local resume tailoring from manually supplied job descriptions. It does **not** add job discovery, application-form filling, or employer submission.

## Product boundary

- Job descriptions enter only through explicit manual text input in Phase 4. An optional source URL is recorded as inert provenance and is never fetched by Phase 4.
- Job-description text is untrusted data. Instruction-like text inside it cannot override system rules, approved facts, template boundaries, or validation.
- The selected llama.cpp/model configuration must already have passed Phase 3 quality/resource evaluation and its installed artifacts must still pass integrity verification.
- Model output is structured plain-text edit intent plus approved fact IDs and JD keywords. The model never writes arbitrary LaTeX.
- Every generated resume remains review-only until the selected model has accumulated five **distinct** human-approved tailored resumes in the current validation context.
- No CI fixture or model self-assessment can count as a human review approval.
- Phase 5 discovery and all employer submission paths remain disabled.

## Evidence and edit gates

1. The private active master resume must still pass the Phase 2 onboarding gate: immutable source integrity, cached-only Tectonic baseline, confirmed template map, and resolved fact bank.
2. Only regions explicitly marked editable in the confirmed template map may change.
3. Phase 4 automatically rewrites only simple, single-line `\\item` wording regions. Complex regions containing LaTeX commands are returned for manual review/original fallback rather than model editing.
4. Each edit must cite an approved current fact linked to that exact LaTeX region. Claims from unrelated resume bullets cannot be composed into a different bullet.
5. Each used JD keyword must be present in the supplied JD, mapped to approved evidence, and supported by the fact linked to the edited field.
6. Replacement wording may use only content supported by the original field and its field-linked approved facts. Unsupported content causes the run to fail closed.
7. Numeric/date/metric literals already present in an edited field are protected and may not be silently removed or changed by automatic wording edits.
8. Every unedited LaTeX line must remain byte-equivalent after newline normalization. Section order, bullet count, document class, external inputs, and shell-escape/write18 posture must remain unchanged.
9. Plain-text replacement values are escaped by application code before controlled rendering. Hidden text, arbitrary LaTeX, model-added commands, and keyword stuffing are not accepted.

## Compile and PDF gates

1. Tailored LaTeX compiles only through the verified app-managed Tectonic installation with cached resources and `--untrusted`; tailoring never populates the package cache from the network.
2. The stored baseline PDF must still exist below the app-owned root and match its recorded SHA-256 before comparison.
3. Tailored page count must equal the baseline page count.
4. Page geometry must remain within the controlled tolerance of the baseline.
5. An overfull hbox/vbox in the Tectonic log blocks the tailored resume.
6. The output PDF must contain extractable text.
7. PDF content validation is order-independent because pypdf extraction order is not a source-of-truth guarantee. The expected token multiset is the verified baseline text minus each edited `before` phrase plus each validated `after` phrase. Missing expected content blocks the run.
8. The source and PDF hashes are persisted with the run.

## Staleness and human-review gates

A pending tailored resume becomes stale and cannot be approved when any relevant dependency changes or fails integrity verification, including:

- active master resume identity/hash;
- fact-bank revision or approved fact source integrity;
- confirmed template-map fingerprint;
- offline baseline fingerprint;
- targeting/profile fingerprint;
- selected model/runtime/device configuration;
- passing model-evaluation evidence;
- model or runtime artifact integrity.

The five-resume gate is bound to a review-context fingerprint built from those dependencies. If that context changes, previously accumulated distinct approvals are invalidated/reset before a new approval can count. Approval of a tailored run and insertion of its distinct resume key are one SQLite transaction. Revoking an approved run removes its gate contribution when no other approved run represents the same distinct resume key, and a gate that falls below five is reopened.

Automatic tailoring can be enabled only when the persisted gate is complete **and** its review-context fingerprint still matches the current validated environment. A stale completed gate is not sufficient.

## Per-run audit package

A successful/blocked generated run stores its app-managed evidence package under the application artifact root. The package contains, when applicable:

- `jd.txt` and `jd.json` with JD hash/source provenance;
- controlled `resume.tex` and compiled `resume.pdf`;
- Tectonic log;
- `diff.json`;
- `keyword_mapping.json`;
- `fact_references.json` with fact versions/source locators;
- `model.json` with pinned install/configuration/evaluation evidence;
- `model_usage.json`;
- `validation.json`;
- `manifest.json` containing the run/dependency fingerprints and SHA-256/byte length of required evidence components.

Human approval re-verifies the source/PDF/manifest hashes and every required manifest component. Tampered or missing audit evidence cannot count toward the five-resume gate.

## Controlled Windows acceptance

The Phase 4 workflow must run on the final branch head and:

1. install pinned Python dependencies and matching Playwright Chromium;
2. pass Python/JavaScript syntax checks;
3. pass all non-external Phase 0-4 tests, including Windows Job Object, migration, local UI, evidence, staleness, tamper, and review-gate regressions;
4. preserve the real Phase 2 Tectonic cache/offline acceptance and Phase 3 local-AI safety boundaries through the combined suite;
5. run `scripts/phase4_tailoring_acceptance.py`, which explicitly downloads/verifies the already-approved test catalogue in CI, establishes a controlled offline resume baseline, locally evaluates the pinned CPU model, and tailors a controlled resume from a JD containing a malicious instruction-like sentence;
6. require a useful evidence-backed edit, no unsupported injected Kubernetes claim, cached-only compile, same page count, no overflow, complete fact/diff/audit evidence, and **0/5** human approvals afterward;
7. pass source self-test and hidden WebView2/pywebview bridge smoke;
8. build the Windows PyInstaller onedir package and pass packaged self-test and hidden-window smoke.

The CI-controlled generated resume proves mechanics only. It cannot complete the human gate and does not establish quality on the user's actual five job descriptions.

## Human completion boundary

After the technical workflow is green, Phase 4 remains partial until the user reviews five distinct real tailored resumes produced from their local approved fact bank and selected validated model configuration. Each resume must be explicitly approved (or corrected/rejected and regenerated) through the Phase 4 review UI. Only five distinct approved resume keys in one current review context complete the gate.

Phase 5 must not start until that Phase 4 human-review gate is complete and Phase 4 is explicitly accepted/merged.
