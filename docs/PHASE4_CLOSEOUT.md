# Human review gate

Status: **private five-resume evidence in progress**.

This file keeps its historical filename for compatibility. It now describes the current product-level human review gate rather than an implementation phase.

## Why this gate remains manual

Synthetic CI proves the deterministic safety path but does not count as human approval. The gate is satisfied only by five distinct real tailored resumes that the user explicitly reviews and approves under one unchanged current validation context.

The validation context binds the active master resume/hash, approved fact-bank revision, confirmed template map, offline baseline, targeting/profile fingerprint, selected model/runtime/device, and passing model-evaluation evidence. A material context change invalidates prior gate evidence rather than silently reusing it.

PR #26 also evaluated llama.cpp v0.4.1/b10964 successfully as a maintenance candidate. That evaluation did not select it: b10809 remained the selected baseline. If a different passing runtime/configuration is explicitly selected later, the review context changes and the five-resume evidence must be current for that configuration.

## Privacy-safe gate report

The authoritative approvals live in the private local SQLite database under `%LOCALAPPDATA%\JobPilotLocal`. Resume/JD/fact values, PDFs, source paths, and audit-package contents must not be committed.

Run on the Windows machine that holds the private JobPilot profile:

```powershell
python -m jobpilot.app.main --review-gate-report
```

The historical `--phase4-gate-report` alias remains accepted.

The report exposes only gate/readiness counts, booleans, the selected model install ID, and a failure reason. It intentionally does not expose private resume or job-description content.

Exit codes:

- `0`: five distinct approvals are persisted **and current** for the selected validation context;
- `2`: the gate is missing, incomplete, invalidated, or stale.

## Exact review procedure

If the report is not complete:

1. Open JobPilot on the Windows machine holding the private profile.
2. Keep the application session idle while reviewing/editing setup state.
3. Confirm resume onboarding is ready: master integrity, cached/offline baseline, template map, and fact review must be current.
4. Confirm the intended validated model/runtime/device configuration is selected. Do not change it between approvals unless intentionally restarting the review context.
5. Use a real job description relevant to the target roles.
6. Generate the tailored resume locally.
7. Inspect the rendered PDF, wording diff, JD keyword mapping, cited fact references, and deterministic validation result.
8. Approve only when every changed claim remains accurate and supported by the current evidence. Reject/correct/regenerate otherwise.
9. Repeat with distinct real job descriptions/resume outputs until the persisted gate reaches 5/5.
10. Run `--review-gate-report` again and require exit code `0`.

Do not paste the private resume, job descriptions, fact bank, or generated PDFs into repository issues, CI logs, pull requests, or source files merely to prove completion.

## What completion enables

A complete current gate establishes local human evidence for the selected tailoring configuration. It does not by itself activate real-employer submission or the measured pilot.

After this gate is verified complete, the only remaining product-evidence item is the separately authorized measured real-world application pilot documented in `docs/PHASE9_PILOT_ACCEPTANCE.md`.
