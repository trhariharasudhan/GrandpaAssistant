from __future__ import annotations

from typing import Any

from .capture import compact_text


class SafeActionExecutor:
    def execute(self, plan: dict[str, Any], *, approved: bool = False) -> dict[str, Any]:
        if plan.get("dangerous"):
            return {"ok": False, "executed": False, "blocked": True, "message": "Blocked dangerous visual desktop action."}
        if plan.get("requires_confirmation") and not approved:
            return {"ok": False, "executed": False, "requires_confirmation": True, "message": "Confirmation required before clicking this UI element.", "plan": self._safe_plan(plan)}
        if plan.get("action") == "read":
            return {"ok": True, "executed": False, "message": "Screen content was read and summarized.", "plan": self._safe_plan(plan)}
        if plan.get("action") == "click":
            element = plan.get("matched_element") if isinstance(plan.get("matched_element"), dict) else {}
            if not element:
                return {"ok": False, "executed": False, "message": "I could not confidently identify the UI element to click.", "plan": self._safe_plan(plan)}
            return {"ok": True, "executed": False, "message": f"Planned click on {compact_text(element.get('label'))}. Real UI clicking is approval-gated and adapter-driven.", "plan": self._safe_plan(plan)}
        return {"ok": True, "executed": False, "message": "No desktop action was needed.", "plan": self._safe_plan(plan)}

    def _safe_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        return {
            "action": compact_text(plan.get("action")),
            "target": compact_text(plan.get("target")),
            "confidence": float(plan.get("confidence") or 0.0),
            "requires_confirmation": bool(plan.get("requires_confirmation")),
            "dangerous": bool(plan.get("dangerous")),
        }
