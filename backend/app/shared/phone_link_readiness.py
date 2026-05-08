from __future__ import annotations

import os
import re
from typing import Any


SETUP_MESSAGE = "Set up Windows Phone Link or choose a default app for tel: links."


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def safe_tel_uri_preview(number):
    digits = re.sub(r"\D+", "", str(number or ""))
    if not digits:
        return "tel:[number]"
    return "tel:" + ("*" * max(0, len(digits) - 4)) + digits[-4:]


def check_tel_handler_readiness():
    if os.name != "nt":
        return {
            "ok": False,
            "status": "warning",
            "tel_handler_configured": False,
            "message": SETUP_MESSAGE,
            "method": "non_windows",
        }
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"tel\shell\open\command") as key:
            command, _kind = winreg.QueryValueEx(key, None)
        configured = bool(_compact_text(command))
        return {
            "ok": configured,
            "status": "ok" if configured else "warning",
            "tel_handler_configured": configured,
            "message": "A default tel: handler appears to be configured." if configured else SETUP_MESSAGE,
            "method": "registry",
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "status": "warning",
            "tel_handler_configured": False,
            "message": SETUP_MESSAGE,
            "method": "registry_missing",
        }
    except Exception as error:
        return {
            "ok": False,
            "status": "warning",
            "tel_handler_configured": None,
            "message": f"Could not verify tel: handler readiness. {SETUP_MESSAGE}",
            "method": "registry_error",
            "detail": str(error),
        }


def summarize_phone_link_readiness(payload):
    payload = payload or {}
    if payload.get("tel_handler_configured"):
        return "Phone Link/default tel: handler looks configured."
    return payload.get("message") or SETUP_MESSAGE
