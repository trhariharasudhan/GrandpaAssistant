param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ExamplePath = Join-Path $ProjectRoot "backend\data\iot_credentials.example.json"
$TargetPath = Join-Path $ProjectRoot "backend\data\iot_credentials.json"

if (-not (Test-Path $ExamplePath)) {
    throw "IoT example config not found at $ExamplePath"
}

if ((Test-Path $TargetPath) -and -not $Force) {
    Write-Host "IoT config already exists at $TargetPath"
    Write-Host "Use -Force if you want to overwrite it with the example template."
    exit 0
}

Copy-Item -LiteralPath $ExamplePath -Destination $TargetPath -Force
Write-Host "Prepared IoT config template at $TargetPath"
Write-Host "Next: replace placeholder values, then set `"enabled`": true."
