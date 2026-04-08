import os
import re

from claude_client import is_claude_configured
from offline_multi_model import get_ollama_status
from utils.config import get_setting


VALID_AI_MODES = {"auto", "offline", "online"}

COMPLEX_HINTS = (
    "analyze",
    "architecture",
    "compare",
    "design",
    "explain in detail",
    "step by step",
    "why does",
    "how does",
    "tradeoff",
    "refactor",
    "debug",
    "traceback",
    "exception",
    "implement",
    "strategy",
    "multi-step",
)

RULE_PREFIXES = (
    "add task",
    "create task",
    "set reminder",
    "add reminder",
    "add note",
    "create note",
    "open ",
    "launch ",
    "start ",
    "close ",
    "shutdown",
    "restart",
    "lock ",
    "turn on ",
    "turn off ",
    "enable ",
    "disable ",
    "increase volume",
    "decrease volume",
    "set brightness",
    "wifi ",
    "bluetooth ",
    "today agenda",
    "plan my day",
    "show overdue",
)

RULE_PATTERNS = (
    re.compile(r"\b(add|create|set|show|list|delete|remove)\b.*\b(task|tasks|reminder|reminders|note|notes|event|events)\b", re.IGNORECASE),
    re.compile(r"\b(open|launch|close|start|stop|minimize|maximize|switch)\b.*\b(app|browser|settings|window|camera|microphone)\b", re.IGNORECASE),
    re.compile(r"\b(turn on|turn off|enable|disable)\b.*\b(wifi|bluetooth|focus assist|airplane mode|volume|brightness|device|iot)\b", re.IGNORECASE),
)


def _configured_ai_mode() -> str:
    value = str(
        os.getenv(
            "AI_MODE",
            get_setting("assistant.ai_mode", get_setting("AI_MODE", "auto")),
        )
    ).strip().lower()
    return value if value in VALID_AI_MODES else "auto"


def _looks_like_rule_request(user_input: str) -> bool:
    lowered = str(user_input or "").strip().lower()
    if not lowered:
        return False
    if any(lowered.startswith(prefix) for prefix in RULE_PREFIXES):
        return True
    return any(pattern.search(lowered) for pattern in RULE_PATTERNS)


def _is_complex_request(user_input: str) -> bool:
    cleaned = " ".join(str(user_input or "").split())
    lowered = cleaned.lower()
    if not lowered:
        return False
    if any(token in lowered for token in COMPLEX_HINTS):
        return True
    if cleaned.count("\n") >= 2 or cleaned.count("?") >= 2:
        return True
    words = cleaned.split()
    if len(words) >= 28:
        return True
    if ":" in cleaned and len(words) >= 18:
        return True
    return False


def _ollama_available() -> bool:
    status = get_ollama_status()
    return bool(status.get("ok"))


def route_request(user_input: str) -> dict[str, str]:
    cleaned = str(user_input or "").strip()
    if not cleaned:
        return {"mode": "fallback", "model": "rule", "reason": "empty"}

    if _looks_like_rule_request(cleaned):
        return {"mode": "fallback", "model": "rule", "reason": "system-task"}

    configured_mode = _configured_ai_mode()
    claude_ready = is_claude_configured()

    if configured_mode == "online":
        if claude_ready:
            return {"mode": "online", "model": "claude", "reason": "forced-online"}
        if _ollama_available():
            return {"mode": "offline", "model": "llama3", "reason": "forced-online-fallback-offline"}
        return {"mode": "fallback", "model": "rule", "reason": "no-provider"}

    if configured_mode == "offline":
        if _ollama_available():
            return {"mode": "offline", "model": "llama3", "reason": "forced-offline"}
        if claude_ready:
            return {"mode": "online", "model": "claude", "reason": "forced-offline-fallback-online"}
        return {"mode": "fallback", "model": "rule", "reason": "no-provider"}

    if _is_complex_request(cleaned):
        if claude_ready:
            return {"mode": "online", "model": "claude", "reason": "complex"}
        if _ollama_available():
            return {"mode": "offline", "model": "llama3", "reason": "complex-fallback-offline"}
        return {"mode": "fallback", "model": "rule", "reason": "no-provider"}

    if _ollama_available():
        return {"mode": "offline", "model": "llama3", "reason": "simple"}
    if claude_ready:
        return {"mode": "online", "model": "claude", "reason": "simple-fallback-online"}
    return {"mode": "fallback", "model": "rule", "reason": "no-provider"}
