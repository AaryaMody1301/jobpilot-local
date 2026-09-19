$ErrorActionPreference = "Stop"

$PipVersion = "26.2.1"

python -m pip install "pip==$PipVersion"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pip lock --build-constraint requirements-build.in -r requirements-lock.in -o pylock.toml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python scripts/verify_dependency_lock.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "pylock.toml regenerated for Windows x64 / CPython 3.13. Review the diff and run the full Phase 0-9 acceptance matrix before merge."
