from __future__ import annotations

from typing import Any

from .config import DANGEROUS_ACTION_KEYWORDS, SENSITIVE_FIELD_HINTS


def _compact_text(value: Any, limit: int = 1000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


class BrowserSafetyLayer:
    def classify(self, plan: dict[str, Any] | None) -> dict[str, Any]:
        payload = plan if isinstance(plan, dict) else {}
        text = " ".join(
            [
                _compact_text(payload.get("goal")),
                _compact_text(payload.get("intent")),
                _compact_text(payload.get("url")),
                " ".join(
                    " ".join(
                        [
                            _compact_text(step.get("action")),
                            _compact_text(step.get("selector")),
                            _compact_text(step.get("description")),
                            _compact_text(step.get("value")),
                        ]
                    )
                    for step in payload.get("steps", [])
                    if isinstance(step, dict)
                ),
            ]
        ).lower()
        field_names = " ".join(
            _compact_text(key).lower()
            for step in payload.get("steps", [])
            if isinstance(step, dict)
            for key in ((step.get("fields") or {}).keys() if isinstance(step.get("fields"), dict) else [])
        )
        sensitive_fields = sorted({hint for hint in SENSITIVE_FIELD_HINTS if hint in field_names})
        dangerous_matches = sorted({keyword for keyword in DANGEROUS_ACTION_KEYWORDS if keyword in text})
        requires_confirmation = bool(dangerous_matches or sensitive_fields or payload.get("requires_confirmation"))
        blocked = any(keyword in text for keyword in ("bypass captcha", "steal", "scrape private", "ignore robots"))
        risk_level = "blocked" if blocked else ("high_confirmation" if dangerous_matches else ("medium_confirmation" if requires_confirmation else "safe_local_action"))
        return {
            "allowed": not blocked,
            "blocked": blocked,
            "requires_confirmation": requires_confirmation,
            "risk_level": risk_level,
            "dangerous_matches": dangerous_matches,
            "sensitive_fields": sensitive_fields,
            "reason": "Confirmation required for browser actions that may submit, buy, book, order, apply, send, or use sensitive fields."
            if requires_confirmation
            else "Browser plan is within safe local action limits.",
        }

    def assert_safe(self, plan: dict[str, Any], *, confirmed: bool = False) -> dict[str, Any]:
        decision = self.classify(plan)
        if decision["blocked"]:
            return {"ok": False, "message": "Blocked unsafe browser automation request.", "safety": decision}
        if decision["requires_confirmation"] and not confirmed:
            return {"ok": False, "message": "Confirmation required before running this browser automation.", "safety": decision}
        return {"ok": True, "message": "Browser automation safety check passed.", "safety": decision}
