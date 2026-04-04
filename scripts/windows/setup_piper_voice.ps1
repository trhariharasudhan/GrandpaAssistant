param(
    [string]$ModelPath = "",
    [string]$ConfigPath = "",
    [switch]$AutoConfigure = $true
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PiperDir = Join-Path $ProjectRoot "backend\data\piper"
$VoicesDir = Join-Path $ProjectRoot "backend\data\voices"
$ModelsDir = Join-Path $ProjectRoot "models\piper"
$PythonExe = @(
    (Join-Path $ProjectRoot ".python311\python.exe"),
    (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
    "python"
) | Where-Object { $_ -eq "python" -or (Test-Path $_) } | Select-Object -First 1

foreach ($Path in @($PiperDir, $VoicesDir, $ModelsDir)) {
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

if ($ModelPath) {
    if (-not (Test-Path $ModelPath)) {
        throw "Model path not found: $ModelPath"
    }
    $TargetModel = Join-Path $PiperDir (Split-Path $ModelPath -Leaf)
    Copy-Item -LiteralPath $ModelPath -Destination $TargetModel -Force
    Write-Host "Copied Piper model to $TargetModel"

    if ($ConfigPath) {
        if (-not (Test-Path $ConfigPath)) {
            throw "Config path not found: $ConfigPath"
        }
        $TargetConfig = Join-Path $PiperDir (Split-Path $ConfigPath -Leaf)
        Copy-Item -LiteralPath $ConfigPath -Destination $TargetConfig -Force
        Write-Host "Copied Piper config to $TargetConfig"
    }
}

$DetectedModels = Get-ChildItem -Path $PiperDir, $VoicesDir, $ModelsDir -Filter *.onnx -Recurse -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Piper setup folders:"
Write-Host " - $PiperDir"
Write-Host " - $VoicesDir"
Write-Host " - $ModelsDir"
Write-Host ""

if ($DetectedModels) {
    Write-Host "Detected Piper models:"
    foreach ($Item in $DetectedModels) {
        Write-Host " - $($Item.FullName)"
    }
    Write-Host ""
    if ($AutoConfigure -and $PythonExe) {
        Write-Host "Running auto configure..."
        @'
import json
import os
import sys

repo_root = os.getcwd()
sys.path.insert(0, os.path.join(repo_root, "backend", "app"))
sys.path.insert(0, os.path.join(repo_root, "backend", "app", "features"))
sys.path.insert(0, os.path.join(repo_root, "backend", "app", "shared"))

from voice.speak import autoconfigure_piper_model, piper_setup_payload

ok, message = autoconfigure_piper_model()
print(json.dumps({"ok": ok, "message": message, "piper": piper_setup_payload()}, indent=2))
'@ | & $PythonExe -
        Write-Host ""
    }
    Write-Host "Next assistant commands:"
    Write-Host " - auto configure piper"
    Write-Host " - use piper voice"
    Write-Host " - piper setup status"
} else {
    Write-Host "No Piper .onnx models detected yet."
    Write-Host "Put a model and its matching .json file in one of the folders above, then run:"
    Write-Host " - auto configure piper"
}
