param(
    [switch]$BuildDesktop = $false
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

if ($BuildDesktop) {
    & (Join-Path $ProjectRoot "scripts\windows\build_react_desktop.cmd")
}

$Health = & (Join-Path $ProjectRoot "scripts\windows\check_assistant_health.cmd")
$Artifact = Get-ChildItem -Path (Join-Path $ProjectRoot "frontend\release") -Filter "Grandpa Assistant*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1

$Summary = [ordered]@{
    release_ready = $false
    desktop_artifact = $null
    notes = @()
}

if ($Artifact) {
    $Summary.desktop_artifact = @{
        path = $Artifact.FullName
        size_mb = [Math]::Round($Artifact.Length / 1MB, 1)
        modified_at = $Artifact.LastWriteTime.ToString("s")
    }
} else {
    $Summary.notes += "Desktop artifact is missing. Run with -BuildDesktop or build_react_desktop.cmd."
}

if ($Health -match '"error"\s*:\s*0') {
    $Summary.notes += "Startup doctor reports zero hard errors."
}

if ($Health -match '"ready"\s*:\s*false') {
    $Summary.notes += "Piper still needs a real voice model."
}

if ($Health -match '"placeholder_count"\s*:\s*[1-9]') {
    $Summary.notes += "IoT config still contains placeholder commands or disabled control."
}

$Summary.release_ready = [bool]$Artifact

$payload = [ordered]@{
    summary = $Summary
    raw_health = $Health
}

$payload | ConvertTo-Json -Depth 6
