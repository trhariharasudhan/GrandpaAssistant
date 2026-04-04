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

from fastapi.testclient import TestClient
from fastapi_chat import app
from app.shared.startup_diagnostics import collect_startup_diagnostics

doctor = collect_startup_diagnostics(use_cache=False, allow_create_dirs=False)

with TestClient(app) as client:
    validation = client.get("/settings/validation")
    piper = client.get("/voice/piper/status")
    status = client.get("/status")
    devices = client.get("/devices")
    rescan = client.post("/devices/rescan")
    iotValidation = client.get("/iot/validate")
    ask = client.post("/ask", json={"prompt": "what devices are connected?", "mode": "auto"})

payload = {
    "doctor": doctor,
    "api_smoke": {
        "settings_validation": {
            "status_code": validation.status_code,
            "request_id": validation.headers.get("x-request-id", ""),
            "ok": validation.json().get("ok"),
        },
        "piper": {
            "status_code": piper.status_code,
            "ok": piper.json().get("ok"),
            "ready": piper.json().get("piper", {}).get("ready"),
            "model_count": len(piper.json().get("piper", {}).get("available_models") or []),
        },
        "status": {
            "status_code": status.status_code,
            "ok": status.json().get("ok"),
        },
        "devices": {
            "status_code": devices.status_code,
            "ok": devices.json().get("ok"),
            "device_count": len(devices.json().get("devices") or []),
        },
        "rescan": {
            "status_code": rescan.status_code,
            "ok": rescan.json().get("ok"),
            "event_count": rescan.json().get("status", {}).get("event_count"),
            "device_count": len(rescan.json().get("devices") or []),
        },
        "iot_validation": {
            "status_code": iotValidation.status_code,
            "ok": iotValidation.json().get("ok"),
            "validation_ok": iotValidation.json().get("validation", {}).get("ok"),
            "placeholder_count": iotValidation.json().get("validation", {}).get("placeholder_count"),
        },
        "ask": {
            "status_code": ask.status_code,
            "ok": ask.json().get("ok"),
            "route": ask.json().get("route", ""),
            "model": ask.json().get("model", ""),
        },
    },
}

print(json.dumps(payload, indent=2))
'@ | & $pythonExe -
