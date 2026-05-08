from __future__ import annotations

import os
import subprocess
import sys
from typing import Any

from debug_learning_summary import build_debug_learning_summary
from startup_diagnostics import collect_startup_diagnostics
from utils.paths import backend_path, project_path


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _result(key: str, title: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    normalized = status if status in {"ok", "warning", "error"} else "warning"
    return {
        "key": key,
        "title": title,
        "status": normalized,
        "ok": normalized != "error",
        "detail": _compact_text(detail),
        **extra,
    }


def _run_read_only(argv: list[str], key: str, title: str, timeout: int = 8) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            argv,
            cwd=project_path(),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        detail = (completed.stdout or completed.stderr or "").strip().splitlines()
        return _result(
            key,
            title,
            "ok" if completed.returncode == 0 else "warning",
            detail[0] if detail else f"{title} completed with return code {completed.returncode}.",
            command=" ".join(argv),
            returncode=completed.returncode,
        )
    except subprocess.TimeoutExpired:
        return _result(key, title, "warning", f"{title} timed out.", command=" ".join(argv))
    except Exception as error:
        return _result(key, title, "warning", f"{title} could not run: {error}", command=" ".join(argv))


def checklist_from_learning_summary(summary, language="auto"):
    families = {item.get("family"): item.get("count", 0) for item in (summary or {}).get("common_error_families", [])}
    items = [
        {"key": "dependency_venv", "title": "Dependency and virtual environment check", "reason": "Prevent missing imports and interpreter drift."},
        {"key": "git_status", "title": "Git status check", "reason": "Prevent branch or working-tree surprises."},
        {"key": "port_readiness", "title": "Backend port readiness check", "reason": "Prevent port already in use issues."},
        {"key": "permission_readiness", "title": "Permission readiness check", "reason": "Check current account and runtime paths."},
        {"key": "file_path_readiness", "title": "File and path readiness check", "reason": "Verify important project paths exist."},
        {"key": "validation_script", "title": "Backend validation script availability", "reason": "Ensure release validation can be run."},
        {"key": "ollama_optional", "title": "Ollama optional readiness", "reason": "Local AI is optional but useful."},
    ]
    if families.get("npm_node", 0):
        items.append({"key": "node_optional", "title": "Node/npm optional awareness", "reason": "Node issues appeared in debug history; backend validation remains Python-first."})
    return items


def build_preflight_checklist(language="auto"):
    learning = build_debug_learning_summary(language=language)
    return {
        "ok": True,
        "language": language or "auto",
        "checklist_items": checklist_from_learning_summary(learning, language=language),
        "learning_summary": learning,
        "no_destructive_action": True,
    }


def _diagnostic_by_key(diagnostics: dict[str, Any], key: str) -> dict[str, Any]:
    for item in diagnostics.get("items", []) or []:
        if item.get("key") == key:
            return item
    return {}


def run_preflight_checklist(language="auto"):
    payload = build_preflight_checklist(language=language)
    diagnostics = collect_startup_diagnostics(use_cache=False, allow_create_dirs=False)
    results = []
    warnings = []

    python_item = _diagnostic_by_key(diagnostics, "python_runtime")
    results.append(_result(
        "dependency_venv",
        "Dependency and virtual environment check",
        "ok" if python_item.get("status") == "ok" else "warning",
        python_item.get("detail") or f"Python executable: {sys.executable}",
        python_executable=sys.executable,
    ))
    results.append(_run_read_only(["git", "status", "--short"], "git_status", "Git status check"))
    results.append(_run_read_only(["cmd.exe", "/c", "netstat", "-ano", "|", "findstr", ":8765"], "port_readiness", "Backend port readiness check"))

    data_item = _diagnostic_by_key(diagnostics, "data_dir")
    log_item = _diagnostic_by_key(diagnostics, "log_dir")
    permission_status = "ok" if data_item.get("status") == "ok" and log_item.get("status") == "ok" else "warning"
    results.append(_result(
        "permission_readiness",
        "Permission readiness check",
        permission_status,
        f"{data_item.get('detail', 'Data path unknown')} {log_item.get('detail', 'Log path unknown')}",
    ))

    required_paths = [
        backend_path("desktop_backend_entry.py"),
        backend_path("main.py"),
        backend_path("app", "api", "web_api.py"),
        project_path("scripts", "dev", "full_backend_validation.py"),
    ]
    missing_paths = [path for path in required_paths if not os.path.exists(path)]
    results.append(_result(
        "file_path_readiness",
        "File and path readiness check",
        "warning" if missing_paths else "ok",
        "Missing required path(s): " + ", ".join(missing_paths) if missing_paths else "Core backend paths are present.",
        missing_paths=missing_paths,
    ))

    validation_script = project_path("scripts", "dev", "full_backend_validation.py")
    results.append(_result(
        "validation_script",
        "Backend validation script availability",
        "ok" if os.path.exists(validation_script) else "warning",
        f"Validation script is available at {validation_script}." if os.path.exists(validation_script) else f"Validation script is missing: {validation_script}",
    ))

    ollama_item = _diagnostic_by_key(diagnostics, "ollama_api")
    ollama_status = "ok" if ollama_item.get("status") == "ok" else "warning"
    results.append(_result(
        "ollama_optional",
        "Ollama optional readiness",
        ollama_status,
        ollama_item.get("detail") or "Ollama readiness was not reported.",
        optional=True,
    ))

    for item in payload["checklist_items"]:
        if item["key"] == "node_optional":
            results.append(_result("node_optional", "Node/npm optional awareness", "warning", item["reason"], optional=True))

    warnings = [item for item in results if item.get("status") == "warning"]
    recommended = []
    if warnings:
        recommended.append("Review warning checks before starting a debugging session.")
    if any(item.get("key") == "validation_script" and item.get("status") == "warning" for item in warnings):
        recommended.append("Restore scripts/dev/full_backend_validation.py before release validation.")
    if any(item.get("key") == "ollama_optional" and item.get("status") == "warning" for item in warnings):
        recommended.append("Start Ollama only if local AI responses are needed.")
    recommended.append("Run full backend validation before committing release changes.")
    return {
        **payload,
        "check_results": results,
        "warnings": warnings,
        "recommended_next_steps": list(dict.fromkeys(recommended)),
        "no_destructive_action": True,
    }


def summarize_preflight_checklist(payload, language="auto"):
    payload = payload or {}
    results = payload.get("check_results") or []
    if not results:
        items = payload.get("checklist_items") or []
        return "Debug checklist ready: " + ", ".join(item.get("title", item.get("key", "check")) for item in items[:7])
    warnings = payload.get("warnings") or []
    parts = [f"Debug preflight checked {len(results)} item(s)."]
    if warnings:
        parts.append("Warnings: " + ", ".join(item.get("title", item.get("key", "check")) for item in warnings[:5]) + ".")
    else:
        parts.append("No warning checks found.")
    next_steps = payload.get("recommended_next_steps") or []
    if next_steps:
        parts.append("Next: " + next_steps[0])
    parts.append("No destructive actions were run.")
    return " ".join(parts)
