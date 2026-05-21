from __future__ import annotations

from typing import Any


def compact_text(value: Any, limit: int = 1000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


class ScreenCaptureService:
    def capture(self, *, include_image: bool = False) -> dict[str, Any]:
        try:
            from app.features.ui_analysis.screen_capture import capture_current_screen, serializable_capture_payload
        except Exception:
            try:
                from backend.app.features.ui_analysis.screen_capture import capture_current_screen, serializable_capture_payload
            except Exception as error:
                return {"ok": False, "message": "Screen capture adapter unavailable.", "error": compact_text(error), "image_included": False}
        try:
            payload = serializable_capture_payload(capture_current_screen())
            if not include_image:
                payload.pop("image_base64", None)
                payload.pop("screenshot_base64", None)
            payload["image_included"] = bool(include_image)
            return payload
        except Exception as error:
            return {"ok": False, "message": "Screen capture failed.", "error": compact_text(error), "image_included": False}
