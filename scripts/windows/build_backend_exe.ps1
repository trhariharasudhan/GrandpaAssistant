param(
    [switch]$SkipInstall = $false
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = Join-Path $ProjectRoot ".python311\python.exe"
}
if (-not (Test-Path $PythonExe)) {
    throw "Could not find a project Python runtime."
}

$PyInstallerCheck = & $PythonExe -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('PyInstaller') else 1)"
if ($LASTEXITCODE -ne 0) {
    if ($SkipInstall) {
        throw "PyInstaller is missing. Install it first with: `"$PythonExe`" -m pip install pyinstaller"
    }
    & $PythonExe -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install PyInstaller."
    }
}

& $PythonExe -m PyInstaller --noconfirm --clean --distpath backend\dist --workpath backend\build backend\GrandpaAssistantBackend.spec
if ($LASTEXITCODE -ne 0) {
    throw "Backend executable build failed."
}

$Artifact = Join-Path $ProjectRoot "backend\dist\GrandpaAssistantBackend\GrandpaAssistantBackend.exe"
if (-not (Test-Path $Artifact)) {
    throw "Backend executable was not created."
}

[ordered]@{
    ok = $true
    backend_executable = $Artifact
} | ConvertTo-Json -Depth 3
