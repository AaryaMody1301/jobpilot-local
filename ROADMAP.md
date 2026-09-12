# Roadmap

Status legend: `[ ] planned`, `[~] in progress`, `[x] complete`, `[!] blocked/partial`.

## Phase 0 - Feasibility and architecture [x]

User-visible outcome: reviewed architecture and executable feasibility probes for the highest-risk local/Windows behaviors. No employer automation.

Completed: authoritative project records, trust/data/state architecture, dependency/license research, deterministic lifecycle/application states, managed-path deletion guard, SQLite recovery, Windows Job Object ownership, Tectonic offline boundary, llama.cpp structured-response boundary, controlled Playwright recognition, and Windows acceptance.

Acceptance: `docs/PHASE0_ACCEPTANCE.md`.

## Phase 1 - Runnable desktop foundation [x]

Completed: bundled local pywebview UI, SQLite settings/runtime/activity persistence, Start/Pause/Stop/Close lifecycle, sample-only worker created only by Start, crash recovery, all agreed targeting controls, source/package WebView2 smoke and PyInstaller onedir build.

Acceptance: `docs/PHASE1_ACCEPTANCE.md`.

## Phase 2 - Resume import and approved fact bank [x]

Completed: immutable SHA-256 LaTeX import, native picker boundary, source-linked stable facts and versions, protected non-bullet facts, explicit approve/correct/reject, confirmed template map, app-managed Tectonic 0.17.0, explicit support-cache population followed by mandatory `--only-cached --untrusted` verification, baseline PDF/page geometry evidence, real supplied two-page template validation, and explicit user approval of all factual claims in the supplied resume exactly as written. Private resume/fact values remain outside Git.

Acceptance: `docs/PHASE2_ACCEPTANCE.md`.

## Phase 3 - Local AI and resource manager [x]

Completed: RAM/CPU/disk/GPU evidence and reserves, runtime-reported llama.cpp devices, exact CPU/Vulkan/runtime/model catalogue metadata, explicit checksum-pinned app-managed downloads, one-at-a-time local inference, localhost-only authenticated `--offline` llama.cpp, live pressure handling, structured/factual/malicious-JD/resource evaluation, measured fastest-passing configuration selection, revision-safe model installs, safe replacement/rollback primitives, persisted five-distinct-resume gate, weekly-only explicit update checks, and Windows packaged acceptance.

Pinned baseline: llama.cpp v0.4.0 / b10809 and `ggml-org/Qwen3-4B-GGUF` Q4_K_M revision `2f3b082b1356a6123f7ed71e65aea340da25d53c`. The b10809 README/parser `response_format` discrepancy is pinned to the tested executable parser contract and all output is still independently validated.

Acceptance: `docs/PHASE3_ACCEPTANCE.md`.

## Phase 4 - Evidence-based resume tailoring [!]

4A JD-as-data parsing and structured fact-linked edits. 4B deterministic factual/LaTeX/PDF/layout validation. 4C first-five distinct resume approval gate for the active model. Manual JD input only.

Technical implementation complete:
- [x] preserve merged Phase 3 as the branch base; existing Phase 4 work was audited rather than reset or silently accepted;
- [x] migration `005_phase4_tailoring.sql` for manual JDs and tailoring runs plus additive `006_phase4_tailoring_safety.sql` for template/baseline/profile/review-context fingerprints and tamper-evident manifest metadata;
- [x] manual JD text is normalized and hashed; instruction-like content remains untrusted data; optional source URLs are inert provenance and must be absolute credential-free HTTP(S) URLs;
- [x] selected local model/runtime/device must still have passing Phase 3 evaluation evidence and verified installed artifacts;
- [x] model returns structured plain-text edit intent, approved fact IDs and JD keywords; arbitrary model LaTeX is never rendered;
- [x] every edit must cite an approved fact linked to that exact LaTeX region, preventing claim composition across unrelated bullets;
- [x] every used JD keyword must be present in the supplied JD and supported by field-linked approved evidence;
- [x] unsupported content tokens and removal of existing numeric/date/metric literals fail closed;
- [x] renderer only changes confirmed simple single-line item wording, escapes plain text, rejects embedded LaTeX commands, and verifies unchanged non-edit lines plus protected template structure;
- [x] Tectonic tailoring compile is cached-only and `--untrusted`; no tailoring-time package download is permitted;
- [x] verified master baseline PDF integrity, same page count/geometry, no overfull boxes, extractable text and order-independent expected-content token validation are required;
- [x] stale-run detection covers master hash, fact-bank revision/source integrity, template-map fingerprint, offline baseline fingerprint, targeting/profile fingerprint, selected model/runtime/device, passing evaluation evidence, and runtime/model integrity;
- [x] five-resume review approvals are bound to a validation-context fingerprint; context changes reset prior distinct approvals instead of carrying them forward;
- [x] human approval and distinct-key insertion are one SQLite transaction; approval revocation removes the gate contribution when no other approved run represents that key and reopens a gate below five;
- [x] per-run app-owned audit package contains JD snapshot/provenance, controlled `.tex`/PDF, diff, keyword mapping, fact references/versions, model/evaluation evidence, usage, validation and a manifest with SHA-256/byte length for required components;
- [x] human approval re-verifies source/PDF/manifest/component integrity; tampered or missing audit evidence cannot count toward the gate;
- [x] automatic tailoring can be enabled only when the persisted five-distinct gate is complete **and** its review-context fingerprint still matches the current validated environment;
- [x] Phase 4 UI supports manual JD import, local generation, diff/keyword/fact/validation review, PDF preview, approve/reject and explicit post-5/5 automatic-tailoring activation;
- [x] controlled Windows technical acceptance passed on the final audited PR #7 head; see `docs/PHASE4_CLOSEOUT.md`.

Human completion gate:
- [ ] five **distinct real tailored resumes** for the selected validated model/configuration must be reviewed and explicitly approved by the user under one unchanged review context;
- [ ] automatic tailoring must remain disabled until that 5/5 gate is complete and current.

Acceptance: `docs/PHASE4_ACCEPTANCE.md` and `docs/PHASE4_CLOSEOUT.md`.

Sequencing note: on 2026-09-12 the user explicitly authorized Phase 5 development after the Phase 4 closeout PR was merged. This is a development-order exception only. It does **not** satisfy or bypass the private Phase 4 5/5 gate, and Phase 5 does not enable employer submission.

## Phase 5 - Job discovery and matching [~]

5A normalization/manual import. 5B verified Greenhouse/Lever/Ashby starter registry and discovery. 5C hard eligibility, required/preferred requirements, evidence matching, conservative deduplication, explainable ranking, Brentwood exclusion.

Implemented on `phase-5-job-discovery-matching`:
- [x] additive migration `007_phase5_jobs.sql` for verified board registry and normalized discovered jobs;
- [x] manual job import with absolute credential-free HTTP(S) provenance and untrusted description text;
- [x] compact stdlib-only public GET clients for Greenhouse, Lever, and Ashby using their documented job-board endpoints;
- [x] three verified starter boards plus user-added board identifiers that are persisted only after a live supported payload is returned;
- [x] conservative source/content deduplication;
- [x] hard targeting checks for excluded employers, target-role titles, permanent full-time employment, explicit minimum experience, India city rules, relocation/sponsorship, and explicit remote-US-only restrictions;
- [x] unknown mandatory employment/location/origin/sponsorship conditions enter review instead of being guessed;
- [x] required/preferred requirement extraction and evidence matching use only current approved source-verified resume facts;
- [x] explainable ranking keeps eligibility separate from evidence coverage and is explicitly not called an ATS score or interview probability;
- [x] local jobs UI reuses the existing Phase 4 shell through one bundled Phase 5 layer; JavaScript performs no network fetches;
- [x] employer form filling/submission remains disabled;
- [ ] final Windows Phase 5 workflow and live three-provider discovery acceptance must pass on the final head before this phase becomes `[x]`.

Acceptance: `docs/PHASE5_ACCEPTANCE.md`.

## Phase 6 - Application engine using controlled forms [ ]

6A transactional application journal/single worker. 6B controlled Playwright fixture engine and approved answers. 6C CAPTCHA/challenge/unknown question/duplicate/crash/network/sleep/close recovery suite. No real employers.

## Phase 7 - Supported hiring-platform adapters [ ]

7A Greenhouse, then 7B Lever, then 7C Ashby. Each adapter must pass controlled submissions and read-only live form recognition before the next begins. Unsupported variants are reported, not guessed.

## Phase 8 - End-to-end orchestration [ ]

Connect session-scoped discovery, matching, tailoring, gates, queues, attention lane, submission, resource pressure, stale-package invalidation, history, and daily confirmed counter. The target is 50 confirmed applications with no ceiling and no relaxed requirements.

## Phase 9 - Packaging and user-authorized pilot [ ]

9A Windows onedir package, setup/upgrade docs, local backup/restore, notices, clean-machine tests. 9B separate explicit real-application activation followed by measured pilot and honest acceptance report. Do not claim 50/day without evidence.
