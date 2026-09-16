param(
    [string]$InstallRoot = "",
    [switch]$SkipShortcut
)

$ErrorActionPreference = "Stop"
$SourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ManifestPath = Join-Path $SourceRoot "distribution-manifest.json"

if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "distribution-manifest.json is missing"
}
$Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Manifest.format -ne "jobpilot-windows-distribution" -or [int]$Manifest.format_version -ne 1) {
    throw "unsupported JobPilot distribution manifest"
}

$Expected = @($Manifest.files | ForEach-Object { [string]$_.path } | Sort-Object)
$Actual = @(Get-ChildItem -LiteralPath $SourceRoot -File -Recurse -Force |
    Where-Object { $_.FullName -ne $ManifestPath } |
    ForEach-Object {
        $_.FullName.Substring($SourceRoot.Length).TrimStart([char[]]@('\','/')).Replace('\','/')
    } | Sort-Object)
$Diff = Compare-Object -ReferenceObject $Expected -DifferenceObject $Actual
if ($Diff) {
    throw "distribution contents do not match the signed file manifest"
}

foreach ($Entry in $Manifest.files) {
    $Relative = ([string]$Entry.path).Replace('/', '\')
    $Source = Join-Path $SourceRoot $Relative
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
        throw "distribution file is missing: $($Entry.path)"
    }
    $Item = Get-Item -LiteralPath $Source
    if ([int64]$Item.Length -ne [int64]$Entry.bytes) {
        throw "distribution file size mismatch: $($Entry.path)"
    }
    $Hash = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Hash -ne ([string]$Entry.sha256).ToLowerInvariant()) {
        throw "distribution file hash mismatch: $($Entry.path)"
    }
}

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "Programs\JobPilotLocal"
}
$InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$Parent = Split-Path -Parent $InstallRoot
New-Item -ItemType Directory -Force -Path $Parent | Out-Null

$Stage = Join-Path $Parent (".JobPilotLocal-stage-" + [guid]::NewGuid().ToString("N"))
$Previous = $null
$HadExisting = Test-Path -LiteralPath $InstallRoot
New-Item -ItemType Directory -Force -Path $Stage | Out-Null

try {
    $AppSource = Join-Path $SourceRoot "app"
    if (-not (Test-Path -LiteralPath (Join-Path $AppSource "jobpilot-local.exe") -PathType Leaf)) {
        throw "packaged JobPilot executable is missing"
    }
    Get-ChildItem -LiteralPath $AppSource -Force | Copy-Item -Destination $Stage -Recurse -Force

    $Legal = Join-Path $Stage "legal"
    New-Item -ItemType Directory -Force -Path $Legal | Out-Null
    foreach ($Name in @("LICENSE", "THIRD_PARTY_NOTICES.md", "BROWSER_NOTICES.md")) {
        Copy-Item -LiteralPath (Join-Path $SourceRoot $Name) -Destination (Join-Path $Legal $Name) -Force
    }
    Copy-Item -LiteralPath $ManifestPath -Destination (Join-Path $Stage "distribution-manifest.json") -Force

    $Metadata = [ordered]@{
        app_version = [string]$Manifest.app_version
        installed_at = [DateTimeOffset]::UtcNow.ToString("o")
        distribution_sha256 = [string]$Manifest.archive_payload_sha256
        install_scope = "per-user"
        data_root = (Join-Path $env:LOCALAPPDATA "JobPilotLocal")
    }
    $Metadata | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Stage "install-metadata.json") -Encoding UTF8

    if ($HadExisting) {
        $Previous = Join-Path $Parent (".JobPilotLocal-prev-" + [guid]::NewGuid().ToString("N"))
        Move-Item -LiteralPath $InstallRoot -Destination $Previous
    }
    try {
        Move-Item -LiteralPath $Stage -Destination $InstallRoot
    }
    catch {
        if ($Previous -and (Test-Path -LiteralPath $Previous) -and -not (Test-Path -LiteralPath $InstallRoot)) {
            Move-Item -LiteralPath $Previous -Destination $InstallRoot
            $Previous = $null
        }
        throw
    }
    if ($Previous -and (Test-Path -LiteralPath $Previous)) {
        Remove-Item -LiteralPath $Previous -Recurse -Force
        $Previous = $null
    }

    if (-not $SkipShortcut) {
        $ShortcutDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
        New-Item -ItemType Directory -Force -Path $ShortcutDir | Out-Null
        $ShortcutPath = Join-Path $ShortcutDir "JobPilot Local.lnk"
        $Shell = New-Object -ComObject WScript.Shell
        $Shortcut = $Shell.CreateShortcut($ShortcutPath)
        $Shortcut.TargetPath = Join-Path $InstallRoot "jobpilot-local.exe"
        $Shortcut.WorkingDirectory = $InstallRoot
        $Shortcut.Description = "JobPilot Local"
        $Shortcut.Save()
    }
}
catch {
    if (Test-Path -LiteralPath $Stage) {
        Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue
    }
    if ($Previous -and (Test-Path -LiteralPath $Previous) -and -not (Test-Path -LiteralPath $InstallRoot)) {
        Move-Item -LiteralPath $Previous -Destination $InstallRoot -ErrorAction SilentlyContinue
    }
    throw
}

[ordered]@{
    action = $(if ($HadExisting) { "upgrade" } else { "install" })
    app_version = [string]$Manifest.app_version
    install_root = $InstallRoot
    user_data_preserved = $true
    shortcut_created = (-not $SkipShortcut)
} | ConvertTo-Json -Compress | Write-Output
