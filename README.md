# jobpilot-local

`jobpilot-local` is a local-first Windows desktop assistant for job discovery, evidence-backed resume tailoring, application tracking, and explicitly user-authorized hosted-form automation.

## Current status

The repository implementation is technically complete through distribution and the measured-pilot write path. Two private product-evidence gates remain intentionally outside CI:

- five distinct real tailored resumes must be explicitly approved under one current validation context before automatic tailoring is considered locally validated;
- the measured real-world application pilot must be run from private local candidate data before any throughput claim is made.

Repository engineering cleanup is complete through capability-oriented runtime composition. Version 0.2.1 is the final cleanup release line; private product-evidence gates remain deliberately local.

## Product boundaries

- Windows 10/11 x64 desktop application.
- Local SQLite state, local model/runtime, and app-managed browser/tool storage.
- No cloud AI, hosted database, telemetry, paid proxy/API, CAPTCHA solver, remote UI script, or cloud sign-in.
- JDs, ATS payloads, employer pages, and model output are untrusted data.
- Resume edits must remain supported by the immutable master resume or approved sourced facts.
- Real-employer writes are disabled on every launch until the measured pilot is explicitly activated.
- CAPTCHA/challenge, login/verification, payment, assessment, unsupported required fields, stale packages, and ambiguous submit controls remain fail-closed.
- `UNCERTAIN` submission outcomes are terminal and are never automatically retried.
- The visible 50/day objective is a target, not an established capability.


## Job and application workspace

The desktop keeps job research and application tracking local:

- search/filter saved jobs and inspect the persisted job-description snapshot and evidence match;
- show public compensation/deadline metadata when exposed by the supported provider, with explicit per-job Greenhouse metadata refresh;
- search/filter application history while keeping the exact tailoring run and immutable package tied to each attempt;
- preview the exact tailored PDF recorded for an application;
- store local follow-up date, notes, and next action without changing the automation/application state machine.

## Distribution

Verified Windows releases contain:

- a PyInstaller onedir application;
- hermetic Playwright Chromium;
- per-user setup under `%LOCALAPPDATA%\Programs\JobPilotLocal`;
- rollback-safe program upgrades that preserve `%LOCALAPPDATA%\JobPilotLocal`;
- WebView2 prerequisite handling;
- portable backup/restore with integrity validation;
- per-file release manifest hashes and a ZIP SHA-256 sidecar.

Install a release by extracting `JobPilotLocal-<version>-win-x64.zip` and running `setup.cmd`. Version 0.2.1 contains the final repository-engineering cleanup.

The project executable is not publisher Authenticode-signed because no publisher certificate/private key is stored in the repository or CI. The installer independently verifies Microsoft's signature on any downloaded WebView2 bootstrapper.

## Measured real-application pilot

The live lane is deliberately narrow. Each process launch starts inactive. Activation requires the exact local phrase `ENABLE MEASURED REAL APPLICATION PILOT`, a fresh read-only supported-form inspection, and explicit arming of each prepared application. At most five distinct real applications may be armed per launch.

Eligibility, approved-answer, package-freshness, resume-hash, provider-blocker, Stop/deactivation, and confirmation gates remain authoritative after activation. Only new explicit positive confirmation observed after the submit click counts as `CONFIRMED`; ambiguous outcomes become `UNCERTAIN`.

See `docs/PHASE9_PILOT_ACCEPTANCE.md` for the measured-pilot handoff and safety boundary.

## Human resume-review gate

Check the current local review gate without exposing resume/JD/fact content:

```powershell
python -m jobpilot.app.main --review-gate-report
```

The historical `--phase4-gate-report` alias is retained for compatibility. The report contains only gate/readiness counts and booleans; private resume/JD/fact content is not emitted.

See `docs/PHASE4_CLOSEOUT.md` for the private five-resume procedure.

## Run from source

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install "pip==26.2.1"
python -m pip install --build-constraint requirements-build.in -r pylock.toml
python -m pip install --no-deps --no-build-isolation -e .
$env:PLAYWRIGHT_BROWSERS_PATH="$env:LOCALAPPDATA\JobPilotLocal\browsers"
python -m playwright install chromium
python -m jobpilot.app.main
```

Private candidate data, browser sessions, generated application packages, backups, databases, and model weights must never be committed.

## CI and release

The repository has three durable GitHub Actions workflows:

- **Windows CI** — locked dependency verification/audit, source syntax, deterministic tests, and source browser/WebView smoke;
- **Windows Acceptance** — resume toolchain, local-model/tailoring, controlled application engine, supported ATS adapters, orchestration, backup/restore, packaged desktop, and clean install/upgrade acceptance;
- **Windows Release** — `main`-only verified Windows packaging, install/upgrade verification, artifact upload, and one-time version-tag release publishing.

Official GitHub Actions are pinned to full commit SHAs. Python CI installs the committed Windows x64 / CPython 3.13 `pylock.toml` without dependency re-resolution.

## Local AI baseline

The validated default remains llama.cpp v0.4.0 / build b10809 with the checksum-pinned Qwen3 4B GGUF catalogue entry. The current stable v0.4.1 / build b10964 Windows CPU/Vulkan binaries are catalogued only as maintenance candidates. Installing/evaluating a candidate never switches the selected runtime automatically; replacement still requires explicit local selection and the existing five-distinct-resume review gate. The newer Qwen3.5-4B line is multimodal and is not treated as a drop-in replacement for JobPilot's text-only/no-mmproj boundary.

## Project records

- `SPEC.md` — v1 product requirements.
- `ROADMAP.md` — current engineering roadmap.
- `DECISIONS.md` — durable engineering decisions.
- `PROGRESS.md` — current implementation/verification handoff.
- `AGENTS.md` — repository implementation rules, including the Ponytail-style compact-code policy.
- `docs/IMPLEMENTATION_HISTORY.md` — condensed historical build record.
- `docs/REPOSITORY_GOVERNANCE.md` — branch/check/release policy.
- `docs/PHASE4_CLOSEOUT.md` — private five-resume closeout procedure.
- `docs/PHASE9_PILOT_ACCEPTANCE.md` — measured real-world pilot procedure.

## License

Original JobPilot Local code is MIT licensed. External binaries, browsers, Python packages, model weights, and other third-party components retain their own licenses and notices. See `THIRD_PARTY_NOTICES.md` and `packaging/BROWSER_NOTICES.md`.
