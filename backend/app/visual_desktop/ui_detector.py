from __future__ import annotations

import re
from typing import Any

from .capture import compact_text


BUTTON_WORDS = {"login", "sign in", "ok", "cancel", "submit", "continue", "settings", "close", "yes", "no", "send"}


class UIElementDetector:
    def detect(self, *, capture: dict[str, Any] | None = None, ocr: dict[str, Any] | None = None) -> dict[str, Any]:
        elements: list[dict[str, Any]] = []
        lines = []
        if isinstance(ocr, dict):
            raw_lines = ocr.get("lines") if isinstance(ocr.get("lines"), list) else []
            lines = [compact_text(line) for line in raw_lines]
            if not lines and ocr.get("text"):
                lines = str(ocr.get("text")).splitlines()
        for index, line in enumerate(lines[:80]):
            normalized = compact_text(line).lower()
            if not normalized:
                continue
            role = "button" if any(word in normalized for word in BUTTON_WORDS) else ("input" if re.search(r"(search|email|password|type)", normalized) else "text")
            confidence = 0.78 if role == "button" else 0.55
            elements.append({"element_id": f"ocr-{index}", "role": role, "label": compact_text(line, 160), "confidence": confidence, "source": "ocr"})
        return {"ok": True, "elements": elements, "element_count": len(elements)}
