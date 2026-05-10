from __future__ import annotations

import re
from typing import Any

try:
    import pytesseract  # type: ignore
except Exception:
    pytesseract = None

try:
    from PIL import Image  # type: ignore
except Exception:
    Image = None

try:
    from .screen_capture import capture_current_screen
    from .ui_models import UIElement, compact_text
except ImportError:
    from screen_capture import capture_current_screen
    from ui_models import UIElement, compact_text


BUTTON_WORDS = {
    "ok",
    "cancel",
    "submit",
    "save",
    "send",
    "next",
    "back",
    "continue",
    "login",
    "sign in",
    "open",
    "close",
}
TEXT_FIELD_WORDS = {"search", "username", "password", "email", "name", "type", "enter"}
MENU_WORDS = {"file", "edit", "view", "help", "menu", "settings", "tools"}
DIALOG_WORDS = {"dialog", "confirm", "are you sure", "warning", "error", "alert"}
BROWSER_WORDS = {"http", "https", "www.", ".com", "chrome", "edge", "firefox", "browser"}


def _element_type_for_label(label: str) -> str:
    lowered = label.lower()
    if any(word in lowered for word in DIALOG_WORDS):
        return "dialog"
    if any(word in lowered for word in TEXT_FIELD_WORDS):
        return "text_field"
    if any(word in lowered for word in MENU_WORDS):
        return "menu"
    if any(word in lowered for word in BROWSER_WORDS):
        return "browser_region"
    if lowered in BUTTON_WORDS or any(word == lowered for word in BUTTON_WORDS):
        return "button"
    if re.fullmatch(r"[A-Z][A-Za-z0-9 ]{1,24}", label):
        return "button"
    return "text"


def _ocr_elements_from_image(image_path: str) -> tuple[list[dict[str, Any]], str]:
    if not image_path or pytesseract is None or Image is None:
        return [], ""
    image = Image.open(image_path)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    elements: list[dict[str, Any]] = []
    lines: list[str] = []
    count = len(data.get("text", []))
    for index in range(count):
        label = compact_text(data["text"][index])
        if not label:
            continue
        try:
            confidence = max(0.0, float(data.get("conf", ["0"])[index]) / 100.0)
        except Exception:
            confidence = 0.0
        if confidence < 0.25:
            continue
        bbox = [
            int(data.get("left", [0])[index] or 0),
            int(data.get("top", [0])[index] or 0),
            int(data.get("width", [0])[index] or 0),
            int(data.get("height", [0])[index] or 0),
        ]
        lines.append(label)
        elements.append(
            UIElement(
                type=_element_type_for_label(label),
                label=label,
                bbox=bbox,
                confidence=round(confidence, 2),
                source="ocr",
            ).to_dict()
        )
    return elements, "\n".join(lines)


def _heuristic_elements_from_text(text: str) -> list[dict[str, Any]]:
    elements = []
    for index, raw in enumerate(str(text or "").splitlines()):
        label = compact_text(raw)
        if not label:
            continue
        elements.append(
            UIElement(
                type=_element_type_for_label(label),
                label=label,
                bbox=[0, index * 24, max(80, min(420, len(label) * 9)), 24],
                confidence=0.55,
                source="text_heuristic",
            ).to_dict()
        )
    return elements


def detect_ui_elements(image_path: str | None = None, image_array: Any = None, text: str | None = None) -> dict[str, Any]:
    capture_payload = None
    if not image_path and image_array is None and text is None:
        capture_payload = capture_current_screen()
        image_path = capture_payload.get("image_path")
        image_array = capture_payload.get("image_array")

    elements, ocr_text = _ocr_elements_from_image(image_path or "")
    if not elements and text:
        elements = _heuristic_elements_from_text(text)
        ocr_text = text

    return {
        "ok": True,
        "warning": False,
        "image_path": image_path or "",
        "ocr_available": bool(pytesseract is not None and Image is not None),
        "integration_hooks": {
            "existing_vision_helpers": "vision.screen_reader OCR helpers can provide text input for this detector.",
            "n8n_route": "POST /api/ui/analyze",
        },
        "text": ocr_text,
        "elements": elements,
        "element_count": len(elements),
        "capture": {key: value for key, value in (capture_payload or {}).items() if key != "image_array"},
    }
