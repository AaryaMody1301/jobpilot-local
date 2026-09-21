# Implementation history

This file keeps the durable historical build record after removal of phase-specific CI/workflow scaffolding. Git history retains the detailed acceptance documents and exact historical workflow definitions.

## Foundation

The project established a Windows/local-first architecture with SQLite recovery, app-owned process/file boundaries, pywebview desktop shell, explicit Start/Pause/Stop/Close lifecycle, and Windows packaging/smoke coverage.

## Resume evidence system

JobPilot added immutable LaTeX master import, Tectonic baseline compilation with offline-cache verification, explicit editable-region mapping, source-linked fact versions, protected non-editable facts, and human fact approval.

## Local AI and tailoring

The app added checksum-pinned llama.cpp/Qwen artifacts, hardware/resource evidence, explicit CPU/Vulkan configuration evaluation, one-inference ownership, resource-pressure shutdown, field-local evidence-backed resume edits, deterministic LaTeX/PDF validation, malicious-JD handling, tamper-evident run packages, and the five-distinct-resume human review gate.

The validated baseline remains llama.cpp v0.4.0 / b10809. Later v0.1.1/v0.1.2 repairs reduced prompt context to field-local evidence and derived long CPU inference timeouts from measured evaluation throughput.

## Job discovery and application engine

JobPilot added normalized/manual discovery, verified public Greenhouse/Lever/Ashby job feeds, conservative deduplication and eligibility/matching, then a transactional single-worker application journal with exact-context approved-answer reuse, duplicate prevention, controlled localhost form execution, fail-closed challenge handling, bounded retry rules, and terminal `UNCERTAIN` outcomes.

## Supported provider adapters and orchestration

Greenhouse, Lever, and Ashby hosted-form adapters were validated against controlled writes and read-only live recognition. End-to-end orchestration connected discovered jobs, eligibility review, evidence-backed tailoring, immutable packages, package staleness checks, application attention/history, and the single application worker.

## Distribution and measured pilot

The project added hermetic Playwright Chromium packaging, per-user setup, rollback-safe upgrade, WebView2 prerequisite handling, SHA-256 release metadata, portable backup/restore, and immutable GitHub version releases.

A later separately authorized measured-pilot path allows real hosted-form writes only after per-launch phrase activation, fresh read-only inspection, and per-application arming. Eligibility, answer review, package freshness, provider blockers, resume hash verification, Stop/deactivation, and post-click confirmation checks remain authoritative.

## Repository cleanup

- PR #21 removed development sample runtime state and made the current production entrypoint/bridge explicit.
- PR #23 collapsed the phase-injected UI into one production shell and added final-shell regression coverage.
- PR 3 replaces the historical phase workflow matrix with durable CI/acceptance/release workflows and removes obsolete phase-only repository scaffolding.

The only unfinished evidence is private/local: the five-real-resume human gate and the measured real-world pilot.
