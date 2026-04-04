$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

$PythonExe = @(
    (Join-Path $ProjectRoot ".python311\python.exe"),
    (Join-Path $ProjectRoot ".venv\Scripts\python.exe"),
    "python"
) | Where-Object { $_ -eq "python" -or (Test-Path $_) } | Select-Object -First 1

if (-not $PythonExe) {
    throw "Could not find a usable Python runtime in .python311, .venv, or PATH."
}

@'
import json
import os
import sys

repo_root = os.getcwd()
sys.path.insert(0, os.path.join(repo_root, "backend", "app", "shared"))

from iot_registry import validate_iot_config

print(json.dumps(validate_iot_config(test_connectivity=True), indent=2))
'@ | & $PythonExe -
