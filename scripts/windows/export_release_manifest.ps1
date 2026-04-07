$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$Version = ""
$PackageJson = Join-Path $ProjectRoot "frontend\package.json"
if (Test-Path $PackageJson) {
    $Version = (Get-Content -Path $PackageJson -Raw | ConvertFrom-Json).version
}

$ReleaseDir = Join-Path $ProjectRoot "frontend\release"
$Artifact = $null
if ($Version) {
    $ExpectedPath = Join-Path $ReleaseDir ("Grandpa Assistant " + $Version + ".exe")
    if (Test-Path $ExpectedPath) {
        $Artifact = Get-Item -LiteralPath $ExpectedPath
    }
}
if (-not $Artifact) {
    $Artifact = Get-ChildItem -Path $ReleaseDir -Filter "Grandpa Assistant*.exe" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}
if (-not $Artifact) {
    throw "Portable desktop artifact not found. Build it first with build_react_desktop.cmd."
}

$Checksum = (Get-FileHash -Path $Artifact.FullName -Algorithm SHA256).Hash
$ManifestPath = Join-Path $Artifact.DirectoryName "release-manifest.json"
$Health = & (Join-Path $ProjectRoot "scripts\windows\check_assistant_health.cmd")

$Manifest = [ordered]@{
    product_name = "Grandpa Assistant"
    version = $Version
    artifact = @{
        path = $Artifact.FullName
        size_mb = [Math]::Round($Artifact.Length / 1MB, 1)
        sha256 = $Checksum
        modified_at = $Artifact.LastWriteTime.ToString("s")
    }
    validation = @{
        checklist = (Join-Path $ProjectRoot "docs\REAL_WORLD_VALIDATION_CHECKLIST.md")
        health_summary = $Health
    }
}

$Manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $ManifestPath -Encoding UTF8
Get-Content -Path $ManifestPath
