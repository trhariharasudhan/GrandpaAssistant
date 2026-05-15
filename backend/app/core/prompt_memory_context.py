from __future__ import annotations

from typing import Any


MAX_MEMORY_CONTEXT_CHARS = 2000
SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "credential", "otp", "pin"}
MEMORY_CONTEXT_HEADER = "Memory context hints (not guaranteed facts):"


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _is_sensitive_key(value: Any) -> bool:
    lowered = _compact_text(value).lower().replace("-", "_")
    return any(key in lowered for key in SENSITIVE_KEYS)


def _safe_line(value: Any) -> str:
    text = _compact_text(value)
    if not text or _is_sensitive_key(text):
        return ""
    return text


def _flatten_memory(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_safe_line(part) for part in value.splitlines()]
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if _is_sensitive_key(key):
                continue
            if isinstance(item, (dict, list, tuple, set)):
                nested = _flatten_memory(item)
                if nested:
                    lines.append(f"{_compact_text(key)}: {'; '.join(nested)}")
                continue
            item_text = _safe_line(item)
            key_text = _safe_line(key)
            if key_text and item_text:
                lines.append(f"{key_text}: {item_text}")
        return lines
    if isinstance(value, (list, tuple, set)):
        lines = []
        for item in value:
            lines.extend(_flatten_memory(item))
        return lines
    return [_safe_line(value)]


def normalize_memory_context(memory_context: Any) -> str:
    """Return a safe, concise prompt memory context string.

    Obvious sensitive keys or lines are excluded. Malformed values return an
    empty string instead of raising.
    """
    try:
        lines = [line for line in _flatten_memory(memory_context) if line]
        if not lines:
            return ""
        body = "\n".join(f"- {line}" for line in lines)
        result = f"{MEMORY_CONTEXT_HEADER}\n{body}"
        if len(result) > MAX_MEMORY_CONTEXT_CHARS:
            return result[:MAX_MEMORY_CONTEXT_CHARS].rstrip() + "\n- [truncated]"
        return result
    except Exception:
        return ""


def should_include_memory_context(memory_context: Any) -> bool:
    return bool(normalize_memory_context(memory_context))


def build_safe_memory_context(memory_context: Any = None) -> str:
    return normalize_memory_context(memory_context)
