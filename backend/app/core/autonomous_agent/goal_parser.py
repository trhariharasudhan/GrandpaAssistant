from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from .action_schema import compact_text


BLOCKED_PATTERNS = {
    "delete_or_remove_files": r"\b(delete|remove|erase|wipe)\b.*\b(file|files|folder|folders|directory|directories|drive|disk|project)\b",
    "format_or_wipe": r"\b(format|factory reset|wipe drive|erase drive)\b",
    "message_or_send": r"\b(send|message|email|mail|whatsapp|sms|dm)\b",
    "payment_or_purchase": r"\b(pay|payment|transfer money|buy|purchase|order|checkout)\b",
    "account_or_security_change": r"\b(change|reset|update|disable|enable)\b.*\b(password|account|security|pin|permission|admin)\b",
    "power_action": r"\b(shutdown|shut down|restart|reboot|sign out|logout)\b",
    "safety_bypass": r"\b(ignore safety|bypass|override permission|disable confirmation)\b",
}


def _extract_url(text: str) -> str:
    match = re.search(r"https?://[^\s]+", text, flags=re.IGNORECASE)
    if match:
        return match.group(0).rstrip(".,)")
    domain = re.search(r"\b(?:open|visit|go to)\s+([a-z0-9.-]+\.[a-z]{2,})(?:\b|/)", text, flags=re.IGNORECASE)
    if not domain:
        return ""
    url = "https://" + domain.group(1).rstrip(".,)")
    parsed = urlparse(url)
    return url if parsed.netloc else ""


def _extract_app(text: str) -> str:
    normalized = text.lower()
    known = {
        "notepad": "notepad",
        "calculator": "calculator",
        "calc": "calc",
        "paint": "paint",
        "mspaint": "mspaint",
        "explorer": "explorer",
    }
    for token, app in known.items():
        if re.search(rf"\b{re.escape(token)}\b", normalized):
            return app
    match = re.search(r"\b(?:open|launch|start)\s+([a-z0-9_. -]+)", normalized)
    return compact_text(match.group(1), 80) if match else ""


def _extract_directory(text: str) -> str:
    match = re.search(r"\b(?:list|show|inspect)\b.*?\b(?:folder|directory)\s+(.+)$", text, flags=re.IGNORECASE)
    return compact_text(match.group(1), 500) if match else ""


def parse_goal(goal: str) -> dict[str, Any]:
    text = compact_text(goal, 2000)
    normalized = text.lower()
    blocked = [
        {"code": code, "reason": f"Goal matches blocked autonomous action category: {code}."}
        for code, pattern in BLOCKED_PATTERNS.items()
        if re.search(pattern, normalized)
    ]
    if blocked:
        return {"goal": text, "intent": "blocked", "slots": {}, "blocked_reasons": blocked}
    if any(term in normalized for term in ("system status", "status", "readiness", "health")):
        return {"goal": text, "intent": "read_safe_system_status", "slots": {}, "blocked_reasons": []}
    if "screenshot" in normalized or "screen shot" in normalized:
        return {"goal": text, "intent": "take_screenshot", "slots": {}, "blocked_reasons": []}
    if "remind" in normalized or "reminder" in normalized:
        return {"goal": text, "intent": "create_reminder", "slots": {"reminder_text": text, "time_text": text}, "blocked_reasons": []}
    url = _extract_url(text)
    if url:
        return {"goal": text, "intent": "open_url", "slots": {"url": url}, "blocked_reasons": []}
    if re.search(r"\b(open|launch|start)\b", normalized):
        app = _extract_app(text)
        return {"goal": text, "intent": "open_application", "slots": {"app": app}, "blocked_reasons": []}
    directory = _extract_directory(text)
    if directory:
        return {"goal": text, "intent": "list_safe_directory_metadata", "slots": {"path": directory}, "blocked_reasons": []}
    return {"goal": text, "intent": "clarify", "slots": {}, "blocked_reasons": []}
