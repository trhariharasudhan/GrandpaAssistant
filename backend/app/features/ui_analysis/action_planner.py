from __future__ import annotations

import re
from typing import Any

try:
    from .ui_models import UIActionPlan, compact_text
except ImportError:
    from ui_models import UIActionPlan, compact_text


DANGEROUS_LABELS = {"delete", "format", "shutdown", "pay", "transfer"}
RISKY_LABELS = {"send", "submit", "confirm", "save", "close", "restart", "install", "uninstall"}
MIN_CONFIDENCE = 0.6


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", str(text or "").lower()) if len(token) > 1}


def _score_element(request: str, element: dict[str, Any]) -> float:
    request_tokens = _tokens(request)
    label = compact_text(element.get("label"))
    label_tokens = _tokens(label)
    if not request_tokens or not label_tokens:
        return 0.0
    overlap = len(request_tokens & label_tokens)
    score = overlap / max(1, len(label_tokens))
    lowered = request.lower()
    if label.lower() and label.lower() in lowered:
        score += 0.35
    if element.get("type") in {"button", "text_field", "menu"}:
        score += 0.1
    return min(0.99, round(score, 2))


def _action_for_request(request: str, element: dict[str, Any]) -> str:
    lowered = request.lower()
    if any(word in lowered for word in ("type", "enter", "fill")):
        return "type"
    if any(word in lowered for word in ("open", "select", "choose")) and element.get("type") == "menu":
        return "select"
    return "click"


def _risk_for_element(request: str, element: dict[str, Any]) -> tuple[bool, bool, str]:
    combined = f"{request} {element.get('label', '')}".lower()
    if any(word in combined for word in DANGEROUS_LABELS):
        return True, True, "Dangerous UI action is blocked."
    if any(word in combined for word in RISKY_LABELS):
        return False, True, "Confirmation required before this UI action."
    return False, False, ""


def build_action_plan(user_request: str, ui_elements: list[dict[str, Any]] | None) -> dict[str, Any]:
    request = compact_text(user_request)
    if not request:
        return {"ok": False, "plans": [], "message": "User request is required."}
    candidates = []
    for element in ui_elements or []:
        score = _score_element(request, element)
        if score <= 0:
            continue
        if score < 0.35:
            continue
        blocked, confirmation, reason = _risk_for_element(request, element)
        if score < MIN_CONFIDENCE and not blocked:
            confirmation = True
            reason = "Low-confidence UI action requires clarification or confirmation."
        candidates.append(
            UIActionPlan(
                action=_action_for_request(request, element),
                target=f"{compact_text(element.get('label'))} {element.get('type', 'element')}".strip(),
                confidence=score,
                requires_confirmation=confirmation,
                blocked=blocked,
                reason=reason,
                element=element,
            ).to_dict()
        )
    candidates.sort(key=lambda item: item.get("confidence", 0), reverse=True)
    return {
        "ok": True,
        "plans": candidates[:5],
        "message": "Action plan generated." if candidates else "No safe matching UI action found.",
        "safe_execution_rules": {
            "dangerous_labels_blocked": sorted(DANGEROUS_LABELS),
            "min_confidence": MIN_CONFIDENCE,
            "auto_execute": False,
        },
        "integration_hooks": {
            "local_action_executor": "Use /api/local-actions/execute only after a plan is safe and approved.",
            "n8n": "n8n workflows can call /api/ui/analyze and /api/ui/plan before requesting local actions.",
        },
    }
