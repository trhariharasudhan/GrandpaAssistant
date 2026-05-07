from __future__ import annotations

import datetime
import json
import urllib.error
import urllib.request
from typing import Any

from startup_diagnostics import collect_startup_diagnostics
from utils.paths import backend_data_path


LAST_BACKEND_VALIDATION_PATH = backend_data_path("last_backend_validation.json")
OPTIONAL_READINESS_CHECKS = {"voice_dependencies", "ollama", "ocr", "camera_vision"}


def _utc_timestamp() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _load_last_backend_validation_status() -> dict[str, Any]:
    try:
        with open(LAST_BACKEND_VALIDATION_PATH, "r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _api_health_status() -> dict[str, Any]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/api/health", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8", errors="ignore"))
        if payload.get("ok"):
            return {"key": "api_health", "name": "API health", "status": "ok", "detail": "API health is responding on 127.0.0.1:8765."}
        return {"key": "api_health", "name": "API health", "status": "warning", "detail": "API health responded, but did not report ok."}
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        return {"key": "api_health", "name": "API health", "status": "warning", "detail": f"API health is not reachable right now: {error}"}


def _diagnostic_item(diagnostics: dict[str, Any], key: str) -> dict[str, Any]:
    for item in diagnostics.get("items", []):
        if item.get("key") == key:
            return item
    return {"status": "warning", "detail": f"{key} was not reported by startup diagnostics."}


def _release_status(key: str, status: str) -> str:
    if key in OPTIONAL_READINESS_CHECKS and status == "error":
        return "warning"
    return status if status in {"ok", "warning", "error"} else "warning"


def _check(key: str, name: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    release_status = _release_status(key, _compact_text(status).lower() or "warning")
    return {
        "key": key,
        "name": name,
        "status": release_status,
        "ok": release_status != "error",
        "detail": _compact_text(detail),
        **extra,
    }


def _validation_check() -> tuple[dict[str, Any], str]:
    validation = _load_last_backend_validation_status()
    validation_ok = validation.get("overall_ok")
    if not validation:
        detail = "No full backend validation status has been recorded yet."
        return _check("last_validation", "Last validation", "warning", detail, payload={}), "Run scripts/dev/full_backend_validation.py before release."

    failed = validation.get("failed_sections") or []
    checked_at = validation.get("checked_at", "unknown time")
    detail = (
        f"Last validation passed at {checked_at}."
        if validation_ok
        else f"Last validation failed at {checked_at}; failed sections: {', '.join(failed) or 'unknown'}."
    )
    status = "ok" if validation_ok else "error"
    next_action = _compact_text(validation.get("next_action")) or "Review the last validation result."
    return _check("last_validation", "Last validation", status, detail, payload=validation), next_action


def build_backend_stability_payload(
    *,
    pending_confirmations: dict[str, Any] | None = None,
    latest_pending_confirmation: dict[str, Any] | None = None,
    api_health: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        diagnostics = collect_startup_diagnostics(use_cache=False, allow_create_dirs=False)
    except Exception as error:
        diagnostics = {
            "ok": False,
            "items": [],
            "summary": f"Startup diagnostics unavailable: {error}",
        }

    api_check = api_health or _api_health_status()
    voice = _diagnostic_item(diagnostics, "voice_input")
    ollama = _diagnostic_item(diagnostics, "ollama_api")
    ocr = _diagnostic_item(diagnostics, "tesseract")
    camera = _diagnostic_item(diagnostics, "camera_vision")
    data_dir = _diagnostic_item(diagnostics, "data_dir")
    log_dir = _diagnostic_item(diagnostics, "log_dir")

    pending_map = pending_confirmations if isinstance(pending_confirmations, dict) else {}
    latest_pending_id = ""
    if isinstance(latest_pending_confirmation, dict):
        latest_pending_id = _compact_text(latest_pending_confirmation.get("id"))
    pending_detail = f"{len(pending_map)} pending action(s)."
    if latest_pending_id:
        pending_detail += f" Latest pending id is {latest_pending_id}."

    validation_check, validation_next_action = _validation_check()
    checks = [
        _check("api_health", "API health", api_check.get("status", "warning"), api_check.get("detail", "")),
        _check("voice_dependencies", "Voice dependencies", voice.get("status", "warning"), voice.get("detail", "")),
        _check("ollama", "Ollama", ollama.get("status", "warning"), ollama.get("detail", "")),
        _check("ocr", "OCR", ocr.get("status", "warning"), ocr.get("detail", "")),
        _check("camera_vision", "Camera and vision", camera.get("status", "warning"), camera.get("detail", "")),
        _check("runtime_data_path", "Runtime data path", data_dir.get("status", "warning"), data_dir.get("detail", "")),
        _check("runtime_log_path", "Runtime log path", log_dir.get("status", "warning"), log_dir.get("detail", "")),
        _check("command_confirmations", "Command confirmations", "ok", pending_detail, pending_count=len(pending_map), latest_pending_id=latest_pending_id),
        validation_check,
    ]
    warnings = [item for item in checks if item["status"] == "warning"]
    failures = [item for item in checks if item["status"] == "error"]
    next_actions = []
    if failures:
        next_actions.append("Fix failed backend stability checks before release.")
    if warnings:
        next_actions.append("Review warning checks before testing the affected optional features.")
    next_actions.append(validation_next_action)
    if not failures and not warnings:
        next_actions.append("Release lock is clear. Continue with small, tested backend changes.")

    return {
        "overall_ok": not failures,
        "timestamp": _utc_timestamp(),
        "checks": checks,
        "warnings": warnings,
        "failures": failures,
        "next_actions": list(dict.fromkeys(action for action in next_actions if action)),
        "diagnostics_summary": diagnostics.get("summary", ""),
    }


def format_backend_stability_text(payload: dict[str, Any]) -> str:
    checks = payload.get("checks", []) if isinstance(payload, dict) else []
    warnings = payload.get("warnings", []) if isinstance(payload, dict) else []
    failures = payload.get("failures", []) if isinstance(payload, dict) else []
    headline = "Backend stability: release lock is clear." if payload.get("overall_ok") else "Backend stability: release lock is blocked."
    parts = [headline]
    if warnings:
        parts.append("Warnings: " + ", ".join(item.get("name", item.get("key", "check")) for item in warnings) + ".")
    if failures:
        parts.append("Failures: " + ", ".join(item.get("name", item.get("key", "check")) for item in failures) + ".")
    parts.extend(
        f"{item.get('name', item.get('key', 'Check'))}: {item.get('status', 'warning')}. {item.get('detail', '')}"
        for item in checks
    )
    next_actions = payload.get("next_actions") or []
    if next_actions:
        parts.append("Next action: " + str(next_actions[0]))
    return " ".join(_compact_text(part) for part in parts if _compact_text(part))
