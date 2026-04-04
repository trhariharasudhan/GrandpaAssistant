$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

$pythonExe = @(
    (Join-Path $repoRoot ".python311\python.exe"),
    (Join-Path $repoRoot ".venv\Scripts\python.exe"),
    "python"
) | Where-Object { $_ -eq "python" -or (Test-Path $_) } | Select-Object -First 1

if (-not $pythonExe) {
    throw "Could not find a usable Python runtime in .python311, .venv, or PATH."
}

@'
import json
import os
import sys

repo_root = os.getcwd()
sys.path.insert(0, os.path.join(repo_root, "backend"))

from app.shared.startup_diagnostics import collect_startup_diagnostics

print(json.dumps(collect_startup_diagnostics(use_cache=False, allow_create_dirs=False), indent=2))
'@ | & $pythonExe -
