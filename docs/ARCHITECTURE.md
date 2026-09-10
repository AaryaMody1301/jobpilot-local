# Phase 0 architecture

## Composition

A single Python desktop process owns application state and the pywebview bridge. Work is split into direct modules rather than autonomous agents:

- `app`: composition root and UI bridge (Phase 1).
- `domain`: state machines and immutable domain values.
- `storage`: SQLite migrations/repositories and audit journal.
- `runtime`: cancellation, session lifecycle, process ownership, managed paths.
- `resume`: immutable source/template mapping, Tectonic compile boundary, validation.
- `model`: hardware/catalogue/inference/evaluation lifecycle.
- `discovery`: public ATS clients and manual imports.
- `matching`: hard eligibility, requirements, evidence, ranking.
- `applications`: transaction/state engine and ATS adapter contract.

## Local data roots

Runtime private data is outside Git under `%LOCALAPPDATA%\JobPilotLocal`:

- `db/`
- `documents/master/`
- `documents/supporting/`
- `artifacts/applications/`
- `models/`
- `tectonic/`
- `browsers/`
- `browser-profile/`
- `cache/`
- `backups/`
- `runtime/`
- `logs/`

Any destructive operation canonicalizes the candidate path and proves it is a descendant of the relevant app-owned root. Symlinks/reparse points resolving outside the root are rejected.

## Trust boundaries

1. User-approved profile/fact data is trusted only to the extent of its approved source/version.
2. JD, employer form text, and discovered HTML/JSON are untrusted data. They never alter program/model instructions.
3. Model output is untrusted proposed data. JSON/schema conformity and approved fact references are locally validated.
4. Browser DOM state is untrusted. `CONFIRMED` requires explicit adapter-specific positive evidence.
5. Downloaded binaries/models are untrusted until source/checksum/license validation and required evaluations pass.
6. The filesystem outside app-owned roots is not writable/deletable by cleanup routines.

## Session state

`IDLE -> RUNNING <-> PAUSED -> STOPPING -> IDLE`; Close can occur from any state. Launch always enters `IDLE` even when the previous process crashed.

Pause: do not schedule new work; currently cancellable work may reach a safe checkpoint.

Stop/Close: cancel discovery and generation immediately; do not start new filling/submission. If irreversible submission has not begun, cancel/return safely. If it may have begun, wait only for confirmation, at most 60 seconds, then store `UNCERTAIN`.

## Application state

Nominal flow:

`DISCOVERED -> ELIGIBILITY_CHECK -> ELIGIBLE -> TAILORING -> REVIEW_REQUIRED/PREPARED -> QUEUED -> INSPECTING -> FILLING -> READY_TO_SUBMIT -> SUBMITTING -> CONFIRMING -> CONFIRMED`

Side states: `INELIGIBLE`, `NEEDS_REVIEW`, `BLOCKED`, `FAILED`, `STALE`, `DUPLICATE`, `UNCERTAIN`.

Once `SUBMITTING` is entered, automatic transitions cannot return to `QUEUED`, `FILLING`, `READY_TO_SUBMIT`, or `FAILED`. Ambiguity becomes `UNCERTAIN`.

## Process model

Windows subprocesses are created suspended, assigned to an app-owned Job Object configured with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, then resumed. This establishes ownership before the child can create descendants. Normal shutdown requests component-level graceful stop first; the Job Object is the final containment mechanism. No process-name scanning is used.

## Persistence model

SQLite uses WAL, foreign keys, explicit migrations, and transactions. Audit state is append-oriented: application state changes are persisted with timestamps/reasons before side-effect boundaries where possible.

Crash recovery distinguishes pre-submit work from irreversible work. Leased pre-submit work can be re-queued after validation. Interrupted `SUBMITTING`/`CONFIRMING` attempts become `UNCERTAIN` and require human resolution.

## External components

Playwright Chromium, Tectonic, and llama.cpp are app-managed components but are not silently downloaded. Playwright/Tectonic binaries and model weights live outside the source tree. Model lifecycle is introduced in Phase 3; employer browser lifecycle in Phase 6.
