from __future__ import annotations


def normalize_lines(items) -> list[str]:
    lines = []
    for item in items or []:
        if isinstance(item, dict):
            text = item.get("fact") or item.get("content") or item.get("message") or ""
        else:
            text = item
        cleaned = " ".join(str(text or "").split()).strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def render_bullets(items, *, empty: str = "- None.") -> str:
    lines = normalize_lines(items)
    if not lines:
        return empty
    return "\n".join(f"- {line}" for line in lines)


def render_history(items, *, role_key: str = "role", content_keys: tuple[str, ...] = ("content", "message"), empty: str = "- No recent context.") -> str:
    lines = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get(role_key) or "user").strip().title()
        text = ""
        for key in content_keys:
            text = str(item.get(key) or "").strip()
            if text:
                break
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines) if lines else empty
