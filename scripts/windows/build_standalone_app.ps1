param(
    [switch]$InstallerOnly = $false,
    [switch]$PortableOnly = $false
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

& (Join-Path $ProjectRoot "scripts\windows\build_backend_exe.cmd")
if ($LASTEXITCODE -ne 0) {
    throw "Backend build failed."
}

Push-Location (Join-Path $ProjectRoot "frontend")
try {
    if (-not (Test-Path "node_modules")) {
        cmd /c npm install
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend dependency install failed."
        }
    }

    if ($InstallerOnly) {
        cmd /c npm run desktop:installer
    } elseif ($PortableOnly) {
        cmd /c npm run desktop:portable
    } else {
        cmd /c npm run desktop:build
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Desktop packaging failed."
    }
}
finally {
    Pop-Location
}

[ordered]@{
    ok = $true
    release_dir = (Join-Path $ProjectRoot "frontend\release")
} | ConvertTo-Json -Depth 3
