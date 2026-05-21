from __future__ import annotations

from typing import Any

from .capture import compact_text


class VisualReasoningEngine:
    def summarize(self, *, active_window: dict[str, Any] | None = None, ocr: dict[str, Any] | None = None, elements: dict[str, Any] | None = None) -> dict[str, Any]:
        app = compact_text((active_window or {}).get("app_name") or (active_window or {}).get("process") or "unknown")
        title = compact_text((active_window or {}).get("title"), 240)
        text = compact_text((ocr or {}).get("summary") or (ocr or {}).get("text"), 1000)
        buttons = [item.get("label") for item in (elements or {}).get("elements", []) if item.get("role") == "button"][:8]
        summary = f"Active app: {app}."
        if title:
            summary += f" Window title: {title}."
        if text:
            summary += f" Visible text summary: {text}."
        if buttons:
            summary += " Possible buttons: " + ", ".join(compact_text(item, 80) for item in buttons) + "."
        return {"ok": True, "summary": summary, "active_app": app, "button_labels": buttons}
