from __future__ import annotations

from typing import Any

from .capture import compact_text


class OCRService:
    def extract_text(self, capture: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            from shared import screen_awareness
        except Exception:
            try:
                import screen_awareness  # type: ignore
            except Exception as error:
                return {"ok": False, "text": "", "lines": [], "message": "OCR adapter unavailable.", "error": compact_text(error)}
        try:
            payload = screen_awareness.summarize_screen_context(language="auto")
            lines = payload.get("lines") if isinstance(payload.get("lines"), list) else []
            text = "\n".join(compact_text(line, 500) for line in lines[:80]) or compact_text(payload.get("summary"), 3000)
            return {"ok": bool(payload.get("ok", True)), "text": text, "lines": lines[:80], "summary": compact_text(payload.get("summary"), 1000)}
        except Exception as error:
            return {"ok": False, "text": "", "lines": [], "message": "OCR extraction failed.", "error": compact_text(error)}
