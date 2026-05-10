from __future__ import annotations

import datetime
import os
from typing import Any

try:
    import numpy as np  # type: ignore
except Exception:
    np = None

try:
    import pyautogui  # type: ignore
except Exception:
    pyautogui = None

try:
    from utils.paths import runtime_path
except ImportError:
    from backend.app.shared.utils.paths import runtime_path


SCREENSHOT_DIR = runtime_path("screenshots")


def _utc_now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _safe_warning(message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "warning": True,
        "message": "Screen capture is not available right now.",
        "detail": str(message or "").strip(),
        "image_path": "",
        "shape": [],
        "timestamp": _utc_now(),
    }


def capture_current_screen(*, all_screens: bool = True, save: bool = True) -> dict[str, Any]:
    """Capture the current desktop screen locally.

    Returns metadata plus a numpy array when numpy is available. API callers should
    strip the array before serializing the payload.
    """
    if pyautogui is None:
        return _safe_warning("pyautogui is not installed.")
    try:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        screenshot_kwargs = {"allScreens": True} if all_screens else {}
        try:
            screenshot = pyautogui.screenshot(**screenshot_kwargs)
        except TypeError:
            screenshot = pyautogui.screenshot()
        image_path = ""
        if save:
            filename = f"ui_capture_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
            image_path = os.path.join(SCREENSHOT_DIR, filename)
            screenshot.save(image_path)
        image_array = np.array(screenshot) if np is not None else None
        size = getattr(screenshot, "size", None)
        shape = list(getattr(image_array, "shape", []) or [])
        return {
            "ok": True,
            "warning": False,
            "image_path": image_path,
            "image_array": image_array,
            "width": int(size[0]) if isinstance(size, tuple) and len(size) == 2 else None,
            "height": int(size[1]) if isinstance(size, tuple) and len(size) == 2 else None,
            "shape": shape,
            "multi_monitor_attempted": bool(all_screens),
            "timestamp": _utc_now(),
        }
    except Exception as error:
        return _safe_warning(str(error))


def serializable_capture_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in (payload or {}).items() if key != "image_array"}
