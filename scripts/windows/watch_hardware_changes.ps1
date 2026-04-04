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
import time

repo_root = os.getcwd()
sys.path.insert(0, os.path.join(repo_root, "backend", "app", "shared"))

from device_manager import DEVICE_MANAGER

print("Watching hardware changes. Insert or remove a USB drive, microphone, webcam, or other device.")
print("Press Ctrl+C to stop.\n")

DEVICE_MANAGER.refresh(emit_events=False)
last_seen = set()

while True:
    status = DEVICE_MANAGER.refresh(emit_events=True)
    events = status.get("recent_events") or []
    fresh = []
    for item in events[-6:]:
        event_key = (
            item.get("timestamp"),
            item.get("device_id"),
            item.get("status"),
            item.get("message"),
        )
        if event_key in last_seen:
            continue
        last_seen.add(event_key)
        fresh.append(item)

    for item in fresh:
        print(json.dumps(item, ensure_ascii=False))

    time.sleep(2.0)
'@ | & $pythonExe -
