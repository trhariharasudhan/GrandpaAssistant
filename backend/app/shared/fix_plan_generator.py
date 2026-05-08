from __future__ import annotations

import datetime
from typing import Any

from debug_assistant import build_debug_report
from debug_session import attach_fix_plan


def _utc_now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _looks_tamil(text: str) -> bool:
    raw = str(text or "")
    return any("\u0b80" <= char <= "\u0bff" for char in raw) or any(
        token in raw.lower()
        for token in (" epdi ", " fix panradhu", "idha", "solution", "pannu")
    )


def _resolve_language(language: str, text: str = "") -> str:
    requested = str(language or "auto").strip().lower()
    if requested in {"ta", "tamil"}:
        return "ta"
    if requested in {"en", "english"}:
        return "en"
    return "ta" if _looks_tamil(text) else "en"


def _suggested(command: str, reason: str) -> dict[str, Any]:
    return {
        "command": command,
        "reason": reason,
        "suggestion_only": True,
        "requires_confirmation": True,
    }


def suggest_commands_for_error_family(error_families, error_text, language: str = "auto") -> dict[str, list[dict[str, Any]]]:
    resolved = _resolve_language(language, error_text)
    tamil = resolved == "ta"
    families = set(error_families or [])
    suggested = []
    risky = []

    if "module_not_found" in families:
        suggested.extend([
            _suggested("python -m pip show <missing-package>", "Check whether the package is installed." if not tamil else "Package install aagirukka nu check pannunga."),
            _suggested("python -m pip install <missing-package>", "Install only after confirming the package name and venv." if not tamil else "Package name/venv confirm pannitu mattum install pannunga."),
        ])
    if "import_error" in families:
        suggested.append(_suggested("python -m py_compile <changed-file.py>", "Check syntax/import errors after reviewing the file." if not tamil else "File review pannitu syntax/import check pannunga."))
    if "python_traceback" in families:
        suggested.append(_suggested("python <script-name>.py", "Reproduce only after saving work and confirming the script." if not tamil else "Script confirm pannitu mattum reproduce pannunga."))
    if "npm_node" in families:
        suggested.extend([
            _suggested("npm install", "Refresh dependencies only after reviewing package.json and lockfile." if not tamil else "package.json/lockfile review pannitu dependencies refresh pannunga."),
            _suggested("npm run <script>", "Rerun the failing script only after checking the exact script name." if not tamil else "Exact script name check pannitu run pannunga."),
        ])
    if "git" in families:
        suggested.extend([
            _suggested("git status", "Inspect branch and working tree state." if not tamil else "Branch/working tree state inspect pannunga."),
            _suggested("git pull --rebase origin main", "Use only if your working tree is ready and conflicts can be handled." if not tamil else "Working tree ready-na mattum use pannunga; conflicts handle panna vendum."),
        ])
        risky.append(_suggested("git rebase --continue", "Only after manually resolving conflicts." if not tamil else "Conflicts manual-a resolve pannitu mattum."))
    if "permission_denied" in families:
        suggested.append(_suggested("whoami", "Check which account is running the process." if not tamil else "Endha account-la process run aagudhu nu check pannunga."))
        risky.append(_suggested("Run the app as Administrator", "Admin mode changes permissions and needs explicit confirmation." if not tamil else "Admin mode permission-ai change pannum; confirmation venum."))
    if "file_not_found" in families:
        suggested.extend([
            _suggested("dir <expected-path>", "Check whether the path exists on Windows." if not tamil else "Windows-la path irukka nu check pannunga."),
            _suggested("python -c \"from pathlib import Path; print(Path('<path>').resolve())\"", "Resolve the path before changing code." if not tamil else "Code change panna munnaadi path resolve pannunga."),
        ])
    if "port_in_use" in families:
        suggested.extend([
            _suggested("netstat -ano | findstr :<port>", "Identify which process owns the port." if not tamil else "Port-ai endha process use pannudhu nu identify pannunga."),
            _suggested("Get-Process -Id <pid>", "Inspect the process before deciding anything." if not tamil else "Decision edukka munnaadi process inspect pannunga."),
        ])
        risky.append(_suggested("Stop-Process -Id <pid>", "Stopping a process can interrupt work; confirm first." if not tamil else "Process stop pannina work interrupt aagalam; confirm pannunga."))

    return {"suggested_commands": suggested, "risky_commands": risky}


def suggest_file_checks(error_text, active_window=None, language: str = "auto") -> list[str]:
    resolved = _resolve_language(language, error_text)
    tamil = resolved == "ta"
    checks = []
    lowered = str(error_text or "").lower()
    if "modulenotfounderror" in lowered or "importerror" in lowered or "no module named" in lowered:
        checks.extend([
            "Check requirements.txt or pyproject.toml for the dependency." if not tamil else "Dependency requirements.txt/pyproject.toml-la irukka nu check pannunga.",
            "Check whether the import name differs from the package name." if not tamil else "Import name package name-kku different-a irukka nu paarunga.",
        ])
    if "no such file" in lowered or "filenotfounderror" in lowered or "not found" in lowered:
        checks.extend([
            "Check the referenced path spelling and file extension." if not tamil else "Referenced path spelling and extension check pannunga.",
            "Check whether the path is relative to the current working directory." if not tamil else "Path current working directory relative-a irukka nu check pannunga.",
        ])
    if "permission" in lowered or "access is denied" in lowered:
        checks.append("Check whether the target file is open, locked, or in a protected folder." if not tamil else "Target file open/locked/protected folder-la irukka nu check pannunga.")
    if active_window:
        kind = _compact_text((active_window or {}).get("kind"))
        title = _compact_text((active_window or {}).get("title"))
        if kind or title:
            checks.append(f"Use the active {kind or 'app'} window title as context: {title}" if not tamil else f"Active {kind or 'app'} window title context-a use pannunga: {title}")
    if not checks:
        checks.append("Review the file and line shown closest to the first error." if not tamil else "First error-kku closest file/line-ai review pannunga.")
    return checks


def build_fix_plan_from_debug_report(report, language: str = "auto") -> dict[str, Any]:
    report = report or {}
    resolved = _resolve_language(language or report.get("language", "auto"), report.get("error_text", ""))
    tamil = resolved == "ta"
    error_text = report.get("error_text") or ""
    families = report.get("error_families") or []
    command_plan = suggest_commands_for_error_family(families, error_text, language=resolved)
    active_window = report.get("active_window") if isinstance(report.get("active_window"), dict) else None
    safe_checks = list(report.get("safe_steps") or [])
    if not safe_checks:
        safe_checks = ["Make the full error visible before trying any fix." if not tamil else "Fix try panna munnaadi full error visible pannunga."]
    if "permission_denied" in set(families):
        safe_checks.append("Check file, folder, and app permission before trying elevated actions." if not tamil else "Elevated action try panna munnaadi file/folder/app permission check pannunga.")
    if "port_in_use" in set(families):
        safe_checks.append("Identify the owning process before considering any stop action." if not tamil else "Stop action consider panna munnaadi owning process identify pannunga.")
    summary = (
        "Idhu safe fix plan. Naan command run pannala, files edit pannala."
        if tamil
        else "Here is a safe fix plan. I did not run commands or edit files."
    )
    if report.get("summary"):
        summary += " " + _compact_text(report.get("summary"))
    return {
        "ok": True,
        "language": resolved,
        "summary": summary,
        "safe_checks": safe_checks,
        "suggested_commands": command_plan["suggested_commands"],
        "risky_commands": command_plan["risky_commands"],
        "suggested_file_checks": suggest_file_checks(error_text, active_window=active_window, language=resolved),
        "requires_confirmation": bool(command_plan["suggested_commands"] or command_plan["risky_commands"]),
        "no_command_executed": True,
        "no_file_edited": True,
        "timestamp": _utc_now(),
    }


def build_fix_plan(language: str = "auto") -> dict[str, Any]:
    resolved = _resolve_language(language, "idha epdi fix panradhu" if str(language).lower() in {"ta", "tamil"} else "")
    report = build_debug_report(language=resolved)
    plan = build_fix_plan_from_debug_report(report, language=resolved)
    attach_fix_plan(plan)
    return plan


def format_fix_plan(plan, language: str = "auto") -> str:
    plan = plan or {}
    resolved = _resolve_language(language or plan.get("language", "auto"))
    checks = plan.get("safe_checks") or []
    commands = plan.get("suggested_commands") or []
    risky = plan.get("risky_commands") or []
    file_checks = plan.get("suggested_file_checks") or []
    if resolved == "ta":
        parts = [plan.get("summary") or "Safe fix plan ready."]
        if checks:
            parts.append("Safe checks: " + " | ".join(f"{i + 1}. {item}" for i, item in enumerate(checks[:4])))
        if file_checks:
            parts.append("File checks: " + " | ".join(file_checks[:3]))
        if commands:
            parts.append("Suggested commands mattum: " + " | ".join(item["command"] for item in commands[:4]))
        if risky:
            parts.append("Risky commands confirmation venum: " + " | ".join(item["command"] for item in risky[:3]))
        parts.append("Naan command run pannala, file edit pannala.")
        return " ".join(parts)
    parts = [plan.get("summary") or "Safe fix plan ready."]
    if checks:
        parts.append("Safe checks: " + " | ".join(f"{i + 1}. {item}" for i, item in enumerate(checks[:4])))
    if file_checks:
        parts.append("File checks: " + " | ".join(file_checks[:3]))
    if commands:
        parts.append("Suggested commands only: " + " | ".join(item["command"] for item in commands[:4]))
    if risky:
        parts.append("Risky commands need confirmation: " + " | ".join(item["command"] for item in risky[:3]))
    parts.append("I did not run commands or edit files.")
    return " ".join(parts)
