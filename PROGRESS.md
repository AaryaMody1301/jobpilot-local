# Progress

## Versioned repair release preparation (28 September 2026)

Project and runtime versions are aligned at `0.2.2`; the release documentation distinguishes this pending build from the immutable published `v0.2.1`. The PR Windows CI/Acceptance checks validate the proposed source, while the Windows Release workflow intentionally runs and publishes only from `main` after the reviewed repair stack is merged. Private five-resume approval and the measured pilot remain separate local evidence gates, and repository-admin protection of `main` is still outstanding.

## Source-integrity recovery (28 September 2026)

An explicit reimport of the exact trusted original bytes now repairs a damaged app-managed master or supporting file when its hash matches the registered source. The damaged copy or symlink is moved into app-owned quarantine; fact IDs and approval history remain. Unsafe managed paths still fail closed, while the desktop snapshot reports mismatch and keeps reimport/Stop available. Supporting integrity failures are recorded when approved facts are checked. Local controlled recovery and symlink tests pass; Windows CI and Acceptance remain required. No source records were reset or deleted.

## Local LaTeX template dependencies (28 September 2026)

Master `.tex` import now collects referenced local template files under the selected source folder with path/symlink/size limits, stores immutable content-hashed revisions, and verifies them before baseline compilation, tailoring, review, and application packaging. Changing an adjacent dependency through explicit reimport preserves older revisions and invalidates the old baseline until a new cached-only compile. Tailoring copies the verified files and records their hashes in the run manifest. The resume and job workspaces show an integrity failure while keeping recovery controls available. Controlled source tests cover versioning, tamper detection and path traversal; Windows Tectonic/model Acceptance must validate actual compilation with a local `\\input` file. No private resume or employer form is involved.

## Hosted form boundary (28 September 2026)

Hosted-form inspection now recognizes hidden resume file inputs, reports outer-page blockers when the form lives in a frame, and rejects unsupported frame hosts. The final submit boundary checks blockers and the frame host again. Confirmation can recognize an explicit success change in the active frame or top page after a delayed response, with a bounded wait; unresolved submissions still become `UNCERTAIN` and are never automatically retried. Local unit checks passed. The controlled browser fixtures run only on loopback; Windows CI and Acceptance must verify the browser path because the local Playwright driver cannot initialize. No employer pages were written.

## Targeting normalization (28 September 2026)

The optional salary minimum now compares explicit annual base-pay ranges only when the user chooses a three-letter currency and the posting uses that same currency. Legacy currencyless settings, missing pay periods, mismatched currencies, and overlapping ranges stay in human review; an annual range entirely below the minimum is ineligible. An explicitly stated experience maximum below the configured target minimum is ineligible, with unsupported or unknown experience still conservatively assessed. Focused local unit tests and JavaScript syntax pass. Windows CI and Acceptance are still required; no automatic employer submissions were made.

## Paginated workspace repair (28 September 2026)

The job, application, manual JD, and tailoring-run workspaces now have explicit pages and full-database search. The application status totals and attention lane no longer derive from the newest 200 attempts. Job source-integrity errors remain visible in the list and read-only detail, with unsafe eligibility downgraded to review. Local isolated regression tests cover 510 jobs, 205 applications, and 36 JDs beyond the former display limits. PR #33 targets `main` to trigger the Windows workflows; the local Playwright driver cannot initialize in this Linux workspace, so the Windows CI and Acceptance browser checks are required before this batch is complete. No real employer applications were submitted.

## Follow-up repair batch (27 September 2026)

PR #31 merged at `484182281e0ed506a28b06f7d9c1987060eb2538` and passed its Windows CI/release workflows. This follow-up branch fixes valid no-change tailoring by copying and offline-compiling the verified original into a per-job audit package; explicit approval is still required and unchanged examples do not count toward the five edited-resume reviews. It also preserves unsaved targeting/application-workspace drafts through desktop refresh and navigation, and rejects malformed individual board postings without discarding their valid siblings (or erasing prior jobs when every posting is malformed).

Local targeted tests and JavaScript syntax checks passed. PR #32 Windows CI and Windows Acceptance passed on `f82de3d`. Full workspace pagination is in the next batch; custom LaTeX dependency bundles, richer supported-form fixtures/iframe handling, deeper source-integrity recovery UX, and normalized salary/experience matching remain open. A new versioned Windows download is needed before merged repairs reach installed `v0.2.1` users. No real employer applications were submitted.

## PR #31 repair work merged (27 September 2026)

The earlier statement that the technical product implementation was complete is no longer a reliable readiness claim. A repository-wide audit found production-path defects despite green Windows checks. PR #31 addressed the desktop model-state contract, human review of exact-context form questions, orchestration transitions and scheduling beyond UI limits, pre-submit rebuilds with preserved history, scoped answer dependencies, Stop/Close worker ownership, final pilot freshness checks, exclusive profile ownership, factual/eligibility conservatism, Lever requirements extraction, selected-config evaluation binding, cheaper display snapshots, and main-only release execution. Dedicated regression cases were added.

That merge is not a claim that live employer automation or all audit findings are solved. Remaining work includes browser variants and iframe support, custom LaTeX dependency bundles, fully paginated workspaces, deeper source-integrity recovery UX, and repository-admin enforcement of required CI/acceptance checks. The gate report is read-only even while the desktop is open. Real employer submissions remain outside synthetic tests. Keep the measured pilot inactive by default and do not expand it until the repair work and private human gates are validated.

## Current repository state

The historical product slices below were implemented and packaged; the repository-wide audit identified defects that remain under repair. Green synthetic checks do not establish private pilot readiness.

Recent cleanup:

- PR #21 merged at `1ee3dfbc0a32a9afb720ec0564c9be7083055d1e`: production runtime entrypoint/bridge cleanup and removal of development sample lifecycle state.
- PR #23 merged at `02836dded7fc7211738405d6acd93cd039cc2d25`: final production UI consolidation, current product copy, active-view rendering, accessibility fixes, and final-shell Playwright coverage.
- PR #24 merged at `3c9122ab24be2a6a2adc8f23db7d698f5071ecbc`: durable CI/acceptance/release workflows and deletion of phase-era repository scaffolding.
- The final engineering closeout removes remaining phase-era runtime/API naming, deletes obsolete sample-work helpers, keeps only compatibility/evidence-history identifiers that must remain stable, and prepares `0.2.1` for a fresh verified release.

## Current CI design

PR #24 replaced ten phase workflows with:

- `Windows CI / windows-ci`;
- `Windows Acceptance / windows-acceptance`;
- `Windows Release / windows-release` plus release publishing on `main`.

The deterministic suite runs once per PR rather than once per historical phase. Full Windows acceptance keeps the real Tectonic, local-model/tailoring, controlled application, provider, orchestration, backup/restore, frozen desktop, and clean install/upgrade boundaries.


## Job/application workspace

PR #25 merged the job/application workspace with migration `010_job_application_workspace.sql`; user-workspace metadata remains separate from application state transitions.

- Jobs can be searched/filtered and inspected from their saved local snapshot, including the JD, evidence match, compensation and deadline metadata when available.
- Lever/Ashby compensation is captured from their public board payloads. Greenhouse pay/deadline metadata is refreshed only on explicit user request from the public per-job endpoint.
- Applications can be searched/filtered and inspected with the exact recorded tailoring run, tailored PDF hash/preview, immutable package ID/manifest hash, journal timestamps, saved JD and URLs.
- Follow-up date, notes and next action are local metadata only; editing is allowed while the session is idle and does not alter the application safety state machine.

## Dependency and model baseline

- Python 3.13.15
- pip 26.2.1
- Playwright 1.63.0
- pypdf 6.19.0
- setuptools 84.0.0
- PyInstaller 6.22.3
- pytest 9.1.1
- pip-audit 2.10.1
- psutil 7.2.2
- pywebview 6.2.1

The committed Windows x64 / CPython 3.13 dependency graph is hash-addressed in `pylock.toml`. Isolated sdist builds are constrained by `requirements-build.in`.

The validated local-AI baseline remains llama.cpp v0.4.0 / b10809 with the accepted Qwen3 4B GGUF revision.

PR #26 merged the stable llama.cpp v0.4.1 / b10964 maintenance evaluation. On the Windows acceptance runner, b10964 CPU passed the same structured/factual/tailoring/resource suite with the pinned Qwen3 4B model; candidate evaluation did not auto-switch the selected b10809 baseline. The model revision remains unchanged.

## Active private gates

The current work item is the five-resume human review gate. Its authoritative evidence lives only in the private local JobPilot database; synthetic CI cannot satisfy it.

Run `python -m jobpilot.app.main --review-gate-report` locally. The report is intentionally privacy-safe and returns exit code 0 only when five distinct real approvals are both persisted and current for the selected resume/facts/profile/template/baseline/model/runtime/device/evaluation context.

After that gate closes, the final remaining item is the measured real-world pilot using individually armed eligible applications. The visible 50/day objective remains a target, not a capability claim.

## Repository administration boundary

The remaining source repairs are proposed in draft PR #32–#38 and are not yet in `main` or a published installer. GitHub repository administration is a separate boundary: the live `main` branch remains unprotected. GitHub-native release immutability is enabled and the `v0.2.1` release is immutable. The connected integration can inspect these settings but does not expose the branch-protection administration write needed to protect `main`.

A repository administrator must still protect `main` with pull-request-only changes, strict `windows-ci` and `windows-acceptance`, conversation resolution, and disabled force-push/deletion. Release immutability is already enabled. Publisher signing remains a separate credential boundary. See `docs/REPOSITORY_GOVERNANCE.md`.
