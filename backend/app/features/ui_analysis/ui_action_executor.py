from __future__ import annotations

from typing import Any

try:
    import pyautogui  # type: ignore
except Exception:
    pyautogui = None

try:
    from .action_planner import DANGEROUS_LABELS, MIN_CONFIDENCE
    from .ui_models import compact_text
except ImportError:
    from action_planner import DANGEROUS_LABELS, MIN_CONFIDENCE
    from ui_models import compact_text


ALLOWED_KEYS = {"enter", "tab", "escape", "backspace"}
SENSITIVE_WORDS = {"password", "pin", "otp", "token", "secret", "credential"}


def _response(ok: bool, action: str, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"ok": bool(ok), "action": action, "message": message, "data": data or {}}


def _bbox_center(bbox: Any) -> tuple[int, int] | None:
    try:
        x, y, width, height = [int(value or 0) for value in list(bbox)[:4]]
    except Exception:
        return None
    if width <= 0 or height <= 0:
        return None
    return x + width // 2, y + height // 2


def _is_dangerous_label(text: str) -> bool:
    lowered = compact_text(text).lower()
    return any(word in lowered for word in DANGEROUS_LABELS)


def execute_ui_action(action_payload: dict[str, Any]) -> dict[str, Any]:
    """Execute one explicitly confirmed UI action.

    This never runs shell commands and only supports small pyautogui primitives.
    """
    action = compact_text(action_payload.get("action")).lower()
    target = compact_text(action_payload.get("target"))
    confidence = float(action_payload.get("confidence") or 0.0)
    if pyautogui is None:
        return _response(False, action or "unknown", "UI action execution is not available because pyautogui is missing.")
    if action_payload.get("blocked") or _is_dangerous_label(target):
        return _response(False, action or "unknown", "That UI action is blocked for safety.")
    if confidence < MIN_CONFIDENCE:
        return _response(False, action or "unknown", "That UI action confidence is too low to execute.")

    if action == "click":
        center = _bbox_center(action_payload.get("bbox") or action_payload.get("element", {}).get("bbox"))
        if center is None:
            return _response(False, action, "I do not have safe coordinates for that click.")
        pyautogui.click(center[0], center[1])
        return _response(True, action, f"Clicked {target}.", {"x": center[0], "y": center[1]})

    if action == "type":
        text = str(action_payload.get("text") or "")
        if not text:
            return _response(False, action, "No text was provided to type.")
        if _is_dangerous_label(target) or any(word in target.lower() for word in SENSITIVE_WORDS):
            return _response(False, action, "I will not type sensitive values into that field.")
        pyautogui.write(text, interval=0.01)
        return _response(True, action, f"Typed text into {target}.", {"characters": len(text)})

    if action == "press_key":
        key = compact_text(action_payload.get("key")).lower()
        if key not in ALLOWED_KEYS:
            return _response(False, action, "That key is not allowlisted for UI automation.")
        pyautogui.press(key)
        return _response(True, action, f"Pressed {key}.", {"key": key})

    return _response(False, action or "unknown", "Unsupported UI action.")
