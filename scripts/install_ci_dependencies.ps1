$ErrorActionPreference = "Stop"

$PipVersion = "26.2.1"

python -m pip install "pip==$PipVersion"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python scripts/verify_dependency_lock.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pip install --build-constraint requirements-build.in -r pylock.toml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pip install --no-deps --no-build-isolation -e .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
