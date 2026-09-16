# Progress

## Current phase

Phase 9 - Packaging and user-authorized pilot.

Status: **distribution/recovery implementation complete and Windows acceptance passed; Phase 9 remains in progress because real-application pilot activation has not been authorized or started**.

PR #12 merged Phase 8 into `main` at `3c43836983b28a09df0ae8163725356a6571a53c`. Phase 4's private five-real-resume human gate remains a separate local acceptance condition and is not waived by Phase 9 development.

## Phase 9 distribution/recovery implementation

- Added a verified Windows 10/11 x64 onedir distribution with a per-user `setup.cmd` / PowerShell installer and in-place upgrade path. Program files live separately from `%LOCALAPPDATA%\JobPilotLocal`, so upgrades do not replace private JobPilot data.
- Playwright Chromium is installed with `PLAYWRIGHT_BROWSERS_PATH=0` before PyInstaller packaging and is verified from the frozen executable with the browser environment removed. The installed app therefore does not depend on a user-global Playwright browser cache.
- Setup checks for the Evergreen Microsoft Edge WebView2 Runtime. If it is absent, setup downloads Microsoft's official Evergreen Bootstrapper, requires a valid Microsoft Authenticode signature, installs it silently, and rechecks availability before installing JobPilot.
- Distribution contents have a format/version manifest with per-file byte length and SHA-256 integrity metadata, plus an archive SHA-256 sidecar. Installer upgrades stage new program files, move the prior install aside, and restore it if replacement fails.
- Added portable local backup/restore for the SQLite database, private documents and generated/application artifacts. Models, tools, Playwright/browser profile state, Tectonic/cache data, runtime files and logs are deliberately excluded as machine-specific or reproducible state.
- Backup creation uses SQLite's backup API and file hashes. Restore rejects unsafe archive paths, symbolic links, unexpected roots, manifest/file mismatches, incompatible newer schema migrations and failed SQLite integrity checks.
- Restore is restart-bound: a verified archive is staged under the managed runtime root, further mutations are blocked, and the payload is applied before the next database open. A pre-restore safety backup is created and machine-specific roots are preserved.
- Added Phase 9 desktop distribution/recovery UI and native backup/restore file dialogs.
- There is intentionally no pilot-activation method or UI action. `pilot_authorized`, `pilot_activation_available`, and real-employer submission remain false.

## Verification

Accepted Phase 9A technical head `b5ebda60793e3f61a25885b4370ebf5242d2e705`, Windows run `35056956675`.

Passed:

- Python and bundled JavaScript syntax validation;
- complete non-external regression suite: 131 passed, 1 skipped, 2 deselected;
- portable backup -> mutation -> staged restore -> restart/apply roundtrip, including pre-restore safety backup and preservation of machine-specific model state;
- explicit proof that the Phase 9 real-application pilot remains locked;
- inherited Phase 8 controlled orchestration and stale-package boundary;
- inherited Phase 7 Greenhouse/Lever/Ashby controlled submission plus live read-only recognition/write guards;
- source self-test and hidden WebView2/pywebview Phase 9 bridge/UI smoke;
- PyInstaller onedir build with hermetic Playwright Chromium;
- frozen Chromium launch with `PLAYWRIGHT_BROWSERS_PATH` removed;
- packaged self-test and hidden-window smoke;
- verified Windows distribution archive build;
- clean per-user install followed by in-place upgrade with `%LOCALAPPDATA%\JobPilotLocal` preservation;
- installed-app self-test, bundled-browser smoke and hidden-window smoke;
- uploaded Windows x64 distribution artifact plus SHA-256 sidecar.

The inherited live provider evidence remains conservative: current Greenhouse/GitLab, Lever/Nium and Ashby examples expose CAPTCHA integration and remain unsupported for automatic live submission. No real employer form was filled or submitted.

The first Phase 9 development run found one integration defect: staging a restore also blocked the read-only snapshot needed to render the UI. The repair separated snapshot reads from mutation guards; Start and inherited mutating actions remain blocked until restart applies the restore. No safety condition was weakened or waived.

## Compact-code/check policy

The repository-wide Ponytail rule remains authoritative. Phase 9 distribution/recovery uses Python stdlib `sqlite3`, `zipfile`, `hashlib`, filesystem primitives, PowerShell, the existing PyInstaller/Playwright dependencies, and the existing pywebview bridge. No updater framework, cloud backup service, second database, second browser framework, or pilot execution engine was added.

## Next boundary

After this distribution/recovery PR is merged, Phase 9 remains `[~]` until a later **separate explicit user authorization** starts the real-application pilot. That pilot must preserve the Phase 4 gate, eligibility/factual quality, CAPTCHA/challenge/assessment/payment blockers, terminal `UNCERTAIN` behavior, and evidence-based confirmation counting. Never claim 50/day without measured real-pilot evidence.
