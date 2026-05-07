from __future__ import annotations

import datetime
import re
from typing import Any

from screen_awareness import summarize_screen_context
from window_awareness import summarize_active_window


ERROR_FAMILIES = (
    ("module_not_found", (r"ModuleNotFoundError", r"No module named")),
    ("import_error", (r"\bImportError\b", r"cannot import name")),
    ("python_traceback", (r"Traceback \(most recent call last\)", r"\bFile \".+\", line \d+")),
    ("npm_node", (r"\bnpm ERR!\b", r"\bnode\b", r"package\.json")),
    ("git", (r"\bfatal:", r"\bgit\b", r"merge conflict", r"rebase")),
    ("permission_denied", (r"Permission denied", r"Access is denied", r"EACCES")),
    ("file_not_found", (r"FileNotFoundError", r"No such file or directory", r"not found")),
    ("port_in_use", (r"address already in use", r"port .* already in use", r"EADDRINUSE", r"WinError 10048")),
)


def _utc_now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _looks_tamil(text: str) -> bool:
    raw = str(text or "")
    return any("\u0b80" <= char <= "\u0bff" for char in raw) or any(
        token in raw.lower()
        for token in (" enna ", " idhu", " pannu", "seri", "debug pannu", "enna error")
    )


def _resolve_language(language: str, text: str = "") -> str:
    requested = str(language or "auto").strip().lower()
    if requested in {"ta", "tamil"}:
        return "ta"
    if requested in {"en", "english"}:
        return "en"
    return "ta" if _looks_tamil(text) else "en"


def _extract_error_text(screen_payload: dict[str, Any]) -> str:
    error_detection = screen_payload.get("error_detection")
    if isinstance(error_detection, dict):
        lines = error_detection.get("lines")
        if isinstance(lines, list) and lines:
            return "\n".join(_compact_text(line) for line in lines if _compact_text(line))
    lines = screen_payload.get("lines")
    if isinstance(lines, list) and lines:
        return "\n".join(_compact_text(line) for line in lines if _compact_text(line))
    return _compact_text(screen_payload.get("text") or screen_payload.get("summary"))


def _detect_families(error_text: str) -> list[str]:
    families = []
    for family, patterns in ERROR_FAMILIES:
        if any(re.search(pattern, error_text or "", flags=re.IGNORECASE) for pattern in patterns):
            families.append(family)
    if "module_not_found" in families and "import_error" not in families:
        families.append("import_error")
    return families


def summarize_error_text(error_text: str, language: str = "auto") -> str:
    resolved = _resolve_language(language, error_text)
    compact = _compact_text(error_text)
    if not compact:
        return "Visible-a clear error text illa." if resolved == "ta" else "I do not see clear error text right now."
    families = _detect_families(compact)
    if resolved == "ta":
        if families:
            return f"Visible error {', '.join(families)} category pola theriyuthu: {compact[:180]}"
        return f"Visible error text idhu: {compact[:180]}"
    if families:
        return f"The visible error looks like {', '.join(families)}: {compact[:180]}"
    return f"The visible error text is: {compact[:180]}"


def infer_likely_causes(error_text: str, window_payload: dict[str, Any] | None = None, language: str = "auto") -> list[str]:
    resolved = _resolve_language(language, error_text)
    tamil = resolved == "ta"
    families = _detect_families(error_text)
    causes = []
    if "module_not_found" in families:
        causes.append("Required Python package is not installed or the active interpreter/venv is different." if not tamil else "Python package install aagala illa vera interpreter/venv use aagudhu.")
    if "import_error" in families and "module_not_found" not in families:
        causes.append("Import name or module path may be wrong, renamed, or circular." if not tamil else "Import name/path wrong-a irukkalaam, rename aagirukkalaam, illa circular import irukkalaam.")
    if "python_traceback" in families:
        causes.append("A Python exception is being raised from the file and line shown in the traceback." if not tamil else "Traceback-la kaamikra file/line-la Python exception varudhu.")
    if "npm_node" in families:
        causes.append("Node/npm dependency, script, or package configuration may be failing." if not tamil else "Node/npm dependency, script, illa package config fail aagudhu.")
    if "git" in families:
        causes.append("Git operation needs attention, such as conflicts, auth, branch state, or repository status." if not tamil else "Git-la conflict/auth/branch/repo status issue irukkalaam.")
    if "permission_denied" in families:
        causes.append("The process may not have permission for that file, folder, port, or command." if not tamil else "Andha file/folder/port/command-ku permission illama irukkalaam.")
    if "file_not_found" in families:
        causes.append("The referenced file or path may be missing, misspelled, or relative to a different working directory." if not tamil else "File/path missing, spelling wrong, illa vera working directory-la irukkalaam.")
    if "port_in_use" in families:
        causes.append("Another process is already using the same port." if not tamil else "Adhe port-ai vera process already use pannudhu.")
    if not causes:
        app_kind = ((window_payload or {}).get("active_window") or window_payload or {}).get("kind")
        if app_kind:
            causes.append(f"The issue appears in the current {app_kind} context, but the exact error family is unclear." if not tamil else f"Issue current {app_kind} context-la irukku, aana exact family clear illa.")
        else:
            causes.append("The visible text does not match a known error family yet." if not tamil else "Visible text known error family match aagala.")
    return causes


def suggest_safe_debug_steps(error_text: str, window_payload: dict[str, Any] | None = None, language: str = "auto") -> dict[str, list[str]]:
    resolved = _resolve_language(language, error_text)
    tamil = resolved == "ta"
    families = _detect_families(error_text)
    safe_steps = []
    risky_steps = []
    if "module_not_found" in families:
        safe_steps.extend([
            "Check the exact missing module name in the traceback." if not tamil else "Traceback-la missing module name exact-a paarunga.",
            "Verify the app is using the expected virtual environment." if not tamil else "Expected virtual environment use aagudha nu verify pannunga.",
            "Review requirements files before installing anything." if not tamil else "Install panna munnaadi requirements files review pannunga.",
        ])
        risky_steps.append("Installing packages changes the environment; ask before running pip or npm." if not tamil else "pip/npm install environment-ai change pannum; run panna munnaadi confirm pannunga.")
    if "port_in_use" in families:
        safe_steps.extend([
            "Identify which port is mentioned in the error." if not tamil else "Error-la endha port mention pannirukku nu paarunga.",
            "Check whether another copy of the app is already running." if not tamil else "App vera copy already run aagudha nu check pannunga.",
        ])
        risky_steps.append("Stopping processes can interrupt work; confirm before killing anything." if not tamil else "Process stop pannina work interrupt aagalam; kill panna munnaadi confirm pannunga.")
    if "permission_denied" in families:
        safe_steps.extend([
            "Check whether the path or command needs admin permission." if not tamil else "Path/command-ku admin permission venuma nu paarunga.",
            "Check whether the file is open or locked by another program." if not tamil else "File vera program-la open/lock aagudha nu paarunga.",
        ])
        risky_steps.append("Changing permissions or running as admin should be confirmed first." if not tamil else "Permission change/admin run panna munnaadi confirm pannunga.")
    if "file_not_found" in families:
        safe_steps.extend([
            "Compare the referenced path with the current working directory." if not tamil else "Referenced path-ai current working directory-oda compare pannunga.",
            "Check spelling, extension, and whether the file was generated yet." if not tamil else "Spelling, extension, file generate aachaa nu check pannunga.",
        ])
    if "npm_node" in families:
        safe_steps.extend([
            "Read the first npm error line and the script name that failed." if not tamil else "First npm error line and failed script name-ai paarunga.",
            "Check package.json and lockfile state before changing dependencies." if not tamil else "Dependencies change panna munnaadi package.json/lockfile state paarunga.",
        ])
        risky_steps.append("Installing or deleting node_modules changes project state; confirm first." if not tamil else "node_modules install/delete project state-ai change pannum; confirm pannunga.")
    if "git" in families:
        safe_steps.extend([
            "Read the exact git error and current branch state." if not tamil else "Exact git error and current branch state-ai paarunga.",
            "Avoid force push or reset unless explicitly approved." if not tamil else "Force push/reset explicit approval illama panna koodadhu.",
        ])
        risky_steps.append("Reset, checkout, rebase conflict resolution, and force operations need explicit confirmation." if not tamil else "Reset/checkout/rebase conflict/force operations-ku explicit confirmation venum.")
    if not safe_steps:
        safe_steps.extend([
            "Copy the first complete error line and the line immediately above it." if not tamil else "First complete error line and adhukku mela irukkra line-ai note pannunga.",
            "Identify which app produced the error before changing anything." if not tamil else "Edhu app error kuduthuchu nu first identify pannunga.",
            "Ask me to inspect the error again after you reveal more lines." if not tamil else "More lines visible pannitu again inspect panna sollunga.",
        ])
    return {"safe_steps": safe_steps, "risky_steps": risky_steps}


def build_debug_report(language: str = "auto") -> dict[str, Any]:
    resolved = _resolve_language(language, "idha debug pannu" if str(language).lower() in {"ta", "tamil"} else "")
    try:
        screen_payload = summarize_screen_context(language=resolved)
    except Exception as error:
        screen_payload = {"ok": False, "warning": True, "summary": _compact_text(error), "error_detection": {"lines": []}}
    try:
        window_payload = summarize_active_window(language=resolved)
    except Exception:
        window_payload = {"ok": False, "warning": True}
    error_text = _extract_error_text(screen_payload) if screen_payload.get("ok") else ""
    if not error_text:
        summary = "Visible-a clear error text illa." if resolved == "ta" else "I do not see a clear visible error right now."
        return {
            "ok": False,
            "language": resolved,
            "summary": summary,
            "error_text": "",
            "error_families": [],
            "likely_causes": ["More readable error text is needed." if resolved != "ta" else "Readable error text innum venum."],
            "safe_steps": ["Make the full error visible, then ask me to debug this again." if resolved != "ta" else "Full error visible pannitu again debug panna sollunga."],
            "risky_steps": [],
            "no_command_executed": True,
            "timestamp": _utc_now(),
        }
    steps = suggest_safe_debug_steps(error_text, window_payload=window_payload, language=resolved)
    return {
        "ok": True,
        "language": resolved,
        "summary": summarize_error_text(error_text, language=resolved),
        "error_text": error_text,
        "error_families": _detect_families(error_text),
        "likely_causes": infer_likely_causes(error_text, window_payload=window_payload, language=resolved),
        "safe_steps": steps["safe_steps"],
        "risky_steps": steps["risky_steps"],
        "active_window": window_payload.get("active_window") if isinstance(window_payload, dict) else None,
        "no_command_executed": True,
        "timestamp": _utc_now(),
    }


def format_debug_report(report: dict[str, Any], language: str = "auto") -> str:
    resolved = _resolve_language(language or report.get("language", "auto"))
    summary = _compact_text(report.get("summary"))
    causes = report.get("likely_causes") or []
    steps = report.get("safe_steps") or []
    risky = report.get("risky_steps") or []
    if resolved == "ta":
        parts = [summary or "Clear error text theriyala."]
        if causes:
            parts.append("Likely cause: " + " | ".join(causes[:3]))
        if steps:
            parts.append("Safe steps: " + " | ".join(f"{index + 1}. {step}" for index, step in enumerate(steps[:4])))
        if risky:
            parts.append("Risky steps confirm panna vendum: " + " | ".join(risky[:2]))
        parts.append("Naan command run pannala, files edit pannala.")
        return " ".join(parts)
    parts = [summary or "I do not see clear error text right now."]
    if causes:
        parts.append("Likely cause: " + " | ".join(causes[:3]))
    if steps:
        parts.append("Safe steps: " + " | ".join(f"{index + 1}. {step}" for index, step in enumerate(steps[:4])))
    if risky:
        parts.append("Needs confirmation before doing: " + " | ".join(risky[:2]))
    parts.append("I did not run commands or edit files.")
    return " ".join(parts)
