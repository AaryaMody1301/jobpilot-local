# Repository governance

Current product code is tested through the Phase 0-9 pull-request matrix. Repository administration must preserve that boundary.

## Main branch policy

Protect `main` with these settings:

- require a pull request before merge; for a single-maintainer repository, zero mandatory approving reviews is acceptable, but direct pushes must not bypass the PR path;
- require branches to be up to date before merge;
- require these unique status checks:
  - `windows-phase0`
  - `windows-phase1`
  - `windows-phase2`
  - `windows-phase3`
  - `windows-phase4`
  - `windows-phase5`
  - `windows-phase6`
  - `windows-phase7`
  - `windows-phase8`
  - `windows-phase9`
- require conversation resolution;
- do not allow force pushes;
- do not allow branch deletion;
- do not allow bypass of the rules unless an explicit emergency repository-admin decision is recorded.

The connected GitHub automation used during development does not expose repository-administration writes, so this setting must be applied from GitHub repository settings by an administrator.

## Immutable workflow dependencies

Workflow actions are pinned to verified full commit SHAs. Major-version comments are retained only to make maintenance readable. Dependency changes must update the SHA after verifying that it belongs to the official action repository.

Python CI uses pip 26.2.1, `requirements-lock.in`, `requirements-build.in`, and the committed Windows x64 / CPython 3.13 `pylock.toml`. Normal CI verifies the direct pins and locked artifact hashes, then installs that committed lock without re-resolving dependencies. Regenerate `pylock.toml` only as an explicit dependency-maintenance change with `scripts/update_dependency_lock.ps1`; review the lock diff and run the complete Phase 0-9 matrix before merge.

## Release policy

A successful Phase 9 push on `main` publishes the current project version as a GitHub Release only when that version tag is absent. Release assets are the verified Windows ZIP and SHA-256 sidecar produced by the same passing Phase 9 run.

Version releases are immutable. A changed build requires a new project version instead of replacing an existing release asset.

## Publisher signing

The repository does not contain a publisher signing certificate or private key. The JobPilot executable therefore remains unsigned by the project publisher until a real protected signing identity is supplied. Never create, commit, or simulate a signing identity merely to satisfy a release check.

The installer independently verifies Microsoft's Authenticode signature before executing a downloaded WebView2 bootstrapper.
