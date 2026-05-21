from __future__ import annotations

from typing import Any

from .capture import compact_text


class ActionPlanner:
    def plan(self, request: str, *, visual_context: dict[str, Any] | None = None) -> dict[str, Any]:
        text = compact_text(request, 1000)
        normalized = text.lower()
        elements = ((visual_context or {}).get("elements") or {}).get("elements", [])
        target = ""
        action = "describe"
        if "click" in normalized:
            action = "click"
            target = normalized.split("click", 1)[1].strip(" .") or "target"
        elif "close popup" in normalized or "close this" in normalized:
            action = "click"
            target = "close"
        elif "open settings" in normalized:
            action = "click"
            target = "settings"
        elif "read" in normalized or "error" in normalized:
            action = "read"
        match = None
        if target:
            for element in elements:
                if target in compact_text(element.get("label")).lower():
                    match = element
                    break
        confidence = float((match or {}).get("confidence") or (0.5 if action == "read" else 0.0))
        requires_confirmation = action == "click" and confidence < 0.85
        return {
            "ok": True,
            "request": text,
            "action": action,
            "target": target,
            "matched_element": match,
            "confidence": confidence,
            "requires_confirmation": requires_confirmation,
            "dangerous": any(word in normalized for word in ("buy", "pay", "delete", "send", "submit")),
        }
