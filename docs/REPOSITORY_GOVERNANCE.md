# Repository governance

## Main branch policy

Protect `main` with:

- pull-request-only changes;
- branch up-to-date requirement before merge;
- required status checks:
  - `windows-ci`
  - `windows-acceptance`
- conversation resolution;
- no force pushes;
- no branch deletion;
- no bypass unless an explicit emergency repository-admin decision is recorded.

The connected repository automation does not expose repository-administration writes, so these settings must be applied by a repository administrator.

## CI dependency policy

Official GitHub Actions are pinned to verified full commit SHAs.

Python CI uses pip 26.2.1, `requirements-lock.in`, `requirements-build.in`, and the committed Windows x64 / CPython 3.13 `pylock.toml`. Normal CI verifies direct pins and locked artifact hashes, then installs the committed lock without re-resolving dependencies.

Regenerate `pylock.toml` only as an explicit dependency-maintenance change with `scripts/update_dependency_lock.ps1`; review the lock diff and run `Windows CI` plus `Windows Acceptance` before merge.

## Workflow policy

- `Windows CI` is the durable PR regression check.
- `Windows Acceptance` is the durable PR capability/package acceptance check.
- `Windows Release` runs on relevant `main` changes and publishes the verified Windows ZIP/SHA-256 pair if the project version tag does not already exist.
- Superseded PR runs use GitHub Actions concurrency cancellation so stale commits do not consume full Windows acceptance capacity.
- Dependency caches are reusable inputs only; release binaries are uploaded as artifacts/releases rather than treated as caches.

## Release policy

Version releases are immutable. A changed build requires a new project version instead of replacing an existing release asset.

## Publisher signing

The repository does not contain a publisher signing certificate or private key. The JobPilot executable remains unsigned by the project publisher until a real protected signing identity is supplied. Never create, commit, or simulate a signing identity merely to satisfy a release check.

The installer independently verifies Microsoft's Authenticode signature before executing a downloaded WebView2 bootstrapper.
