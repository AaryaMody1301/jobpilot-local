$ErrorActionPreference = "Stop"

$PipVersion = "26.2.1"
$GeneratedLock = Join-Path $env:RUNNER_TEMP "jobpilot-pylock.toml"

python -m pip install "pip==$PipVersion"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pip lock --build-constraint requirements-build.in -r requirements-lock.in -o $GeneratedLock
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ((Get-FileHash -Algorithm SHA256 $GeneratedLock).Hash -ne (Get-FileHash -Algorithm SHA256 pylock.toml).Hash) {
    throw "pylock.toml is stale for requirements-lock.in on Windows/Python 3.13; regenerate it with pip $PipVersion"
}

python -m pip install --build-constraint requirements-build.in -r pylock.toml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pip install --no-deps --no-build-isolation -e .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
