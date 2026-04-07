from __future__ import annotations

import re
from typing import Any


SAFE_SYSTEM_COMMANDS = {
    "verify my face",
    "verify my voice",
    "my voice status",
    "face security status",
    "security status",
    "security alerts",
    "security logs",
    "unlock assistant",
    "disable assistant lockdown",
}


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def classify_command(command: str) -> dict[str, Any]:
    normalized = _compact_text(command).lower()
    if not normalized:
        return {
            "level": "LOW",
            "category": "chat",
            "requires_confirmation": False,
            "requires_authentication": False,
            "requires_admin_mode": False,
            "reason": "Empty input.",
        }

    if normalized in SAFE_SYSTEM_COMMANDS or normalized.startswith(("security pin ", "set security pin to ")):
        return {
            "level": "LOW",
            "category": "security",
            "requires_confirmation": False,
            "requires_authentication": False,
            "requires_admin_mode": False,
            "reason": "Security verification command.",
        }

    high_risk_patterns = [
        r"\b(format|wipe|factory reset|erase)\b",
        r"\b(delete|remove)\b.*\b(file|files|folder|folders|directory|directories|drive|disk)\b",
        r"\b(delete|remove)\b.*\b(account|user|credential|credentials|security|pin|password)\b",
        r"\b(delete|remove|clear|reset)\b.*\b(memory|all memory|face profile|voice profile|voice sample)\b",
        r"\b(shutdown|shut down|restart|sign out|logout)\b",
        r"\b(lock system|disable assistant|turn off microphone|turn off camera)\b",
        r"\b(clear piper|clear my voice sample|reset piper)\b",
        r"\b(set|change|update)\b.*\b(pin|password|security|startup|interface mode|role|admin|permissions?)\b",
        r"\b(enable|disable|start|stop)\b.*\b(admin mode|security admin mode|autonomous mode)\b",
    ]
    for pattern in high_risk_patterns:
        if re.search(pattern, normalized):
            return {
                "level": "HIGH",
                "category": "system",
                "requires_confirmation": True,
                "requires_authentication": True,
                "requires_admin_mode": True if "admin" in normalized or "security" in normalized or normalized.startswith(("set ", "change ", "update ")) else False,
                "reason": "This command can change system state or security settings.",
            }

    medium_risk_patterns = [
        r"^(?:send|message|mail|email|whatsapp|call)\b",
        r"^(?:sync|refresh|merge|update|delete|remove|show|list)\b.*\bcontacts?\b",
        r"(?:\b(iot|smart home)\b|^(?:turn on|turn off|switch on|switch off)\b)",
        r"^(?:open|launch|close)\b",
        r"^(?:delete|remove|clear)\b.*\b(task|tasks|reminder|reminders|note|notes|event|events)\b",
    ]
    for pattern in medium_risk_patterns:
        if re.search(pattern, normalized):
            return {
                "level": "MEDIUM",
                "category": "sensitive-action",
                "requires_confirmation": True,
                "requires_authentication": False,
                "requires_admin_mode": False,
                "reason": "This command can affect messages, contacts, devices, or personal data.",
            }

    admin_only_patterns = [
        r"\b(set|change|update)\b.*\b(wake word|voice backend|tts backend|stt backend|language mode|developer mode|focus mode)\b",
        r"\b(enable|disable)\b.*\b(developer mode|focus mode|offline mode)\b",
        r"\b(reload plugins|enable plugin|disable plugin)\b",
    ]
    for pattern in admin_only_patterns:
        if re.search(pattern, normalized):
            return {
                "level": "HIGH",
                "category": "configuration",
                "requires_confirmation": True,
                "requires_authentication": True,
                "requires_admin_mode": True,
                "reason": "Configuration changes require security admin mode.",
            }

    return {
        "level": "LOW",
        "category": "general",
        "requires_confirmation": False,
        "requires_authentication": False,
        "requires_admin_mode": False,
        "reason": "General assistant command.",
    }
