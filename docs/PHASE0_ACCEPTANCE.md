# Phase 0 acceptance

## Automated checks

Run:

```powershell
pytest -m "not external"
```

Required assertions:

1. Valid session/application transitions are accepted and invalid ones rejected.
2. No automatic transition exists from `UNCERTAIN` back to a submission path.
3. Close/Stop before irreversible submit has no confirmation wait; after irreversible submit it permits at most 60 seconds and unresolved status maps to `UNCERTAIN`.
4. SQLite migration is idempotent, WAL/foreign keys are active, pre-submit leased work safely recovers, and interrupted `SUBMITTING`/`CONFIRMING` becomes `UNCERTAIN`.
5. Managed deletion rejects the model root itself, parent traversal, and symlinks/reparse points resolving outside the managed model root.
6. Tectonic normal compile command contains `--only-cached` and `--untrusted`; only an explicit onboarding/cache flag permits resource fetching.
7. llama.cpp request construction uses a schema constraint and returned content must pass local strict structure validation.
8. Controlled application fixture inspection is read-only and detects required fields/challenge markers without clicking Submit.
9. On Windows, closing the Job Object terminates its owned process tree while an unrelated process remains alive.

## Optional external probes

These do not run silently because they require separately installed/approved software or model files.

### Tectonic

Set `JOBPILOT_TECTONIC_EXE` to a Tectonic 0.17.0 executable and run:

```powershell
pytest -m external tests/integration/test_tectonic_external.py
```

The test compiles a controlled cached document only. A fresh empty cache is expected to fail under `--only-cached`; cache population is a separate explicitly approved action.

### llama.cpp

Set:

- `JOBPILOT_LLAMA_SERVER_EXE`
- `JOBPILOT_TEST_MODEL_GGUF`

and run the external llama integration tests. Phase 0 does not download a model. Structural validation remains local even if llama.cpp reports schema-constrained output.

## Windows CI

`.github/workflows/phase0.yml` executes the non-external suite on `windows-latest` with Python 3.13 and installs only the pinned Python dependencies plus Playwright Chromium needed for controlled browser recognition. No real employer URL is opened and no model is downloaded.

## Phase boundary

Phase 0 can be marked complete when the non-external Windows checks pass and no architecture blocker remains. Actual resume/Tectonic compatibility is intentionally deferred until the user's LaTeX source is supplied in Phase 2; hardware/model quality is Phase 3.
