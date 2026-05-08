from __future__ import annotations

import re
import webbrowser
from typing import Any


EMERGENCY_NUMBERS = {"100", "101", "102", "108", "112", "911", "999"}


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _strip_call_words(value: str) -> str:
    cleaned = _compact_text(value).lower()
    cleaned = re.sub(r"\b(?:please|kindly|now|phone|number)\b", " ", cleaned)
    cleaned = re.sub(r"\b(?:call|cll|dial|pannu|ku|to)\b", " ", cleaned)
    return _compact_text(cleaned)


def normalize_phone_number(value):
    raw = str(value or "")
    leading_plus = raw.strip().startswith("+")
    digits = re.sub(r"\D+", "", raw)
    if not digits:
        return ""
    if len(digits) < 7 or len(digits) > 15:
        return ""
    return f"+{digits}" if leading_plus else digits


def _is_emergency_number(number: str) -> bool:
    digits = re.sub(r"\D+", "", str(number or ""))
    return digits in EMERGENCY_NUMBERS


def detect_call_intent(command):
    normalized = _compact_text(command).lower()
    if not normalized:
        return {"is_call": False, "target_text": "", "reason": "empty"}

    patterns = [
        r"^(?:call|dial|cll)\s+(.+)$",
        r"^(?:call|dial|cll)\s+pannu\s+(.+)$",
        r"^(.+?)\s+ku\s+(?:call|cll|phone)\s+pannu$",
        r"^(.+?)\s+(?:call|cll)\s+pannu$",
    ]
    for pattern in patterns:
        match = re.match(pattern, normalized)
        if match:
            target = _strip_call_words(match.group(1))
            return {"is_call": True, "target_text": target, "reason": "matched"}

    if normalized in {"call", "dial", "cll pannu", "call pannu", "phone pannu"}:
        return {"is_call": True, "target_text": "", "reason": "missing_target"}

    return {"is_call": False, "target_text": "", "reason": "not_call"}


def _resolve_contact_phone(name_or_number: str) -> dict[str, Any]:
    try:
        from contact_manager import find_contact

        local = find_contact(name_or_number)
        if local.get("ok") and local.get("contact"):
            contact = local["contact"]
            return {
                "ok": True,
                "type": "local_contact",
                "display_name": contact.get("name") or _compact_text(name_or_number),
                "phone_number": normalize_phone_number(contact.get("phone")),
                "message": f"Found local contact {contact.get('name')}.",
            }
        if local.get("status") == "ambiguous":
            return {"ok": False, "status": "ambiguous", "message": local.get("message", "I found multiple matching local contacts.")}
    except Exception:
        pass

    try:
        from brain.memory_engine import get_named_contact_field

        value, reply = get_named_contact_field(name_or_number, "phone")
        if value:
            return {
                "ok": True,
                "type": "contact",
                "display_name": _compact_text(name_or_number),
                "phone_number": normalize_phone_number(value),
                "message": _compact_text(reply),
            }
        reply_text = _compact_text(reply)
        if "found multiple" in reply_text.lower():
            return {"ok": False, "status": "ambiguous", "message": reply_text}
        return {"ok": False, "status": "not_found", "message": reply_text or f"I could not find a saved contact matching {name_or_number}. Add the contact or provide a phone number."}
    except Exception as error:
        return {
            "ok": False,
            "status": "provider_unavailable",
            "message": f"Contact lookup is unavailable: {error}",
        }


def resolve_call_target(name_or_number):
    target = _strip_call_words(name_or_number)
    if not target:
        return {
            "ok": False,
            "status": "missing_target",
            "message": "Who should I call? Say call followed by a contact name or phone number.",
        }

    if _is_emergency_number(target):
        return {
            "ok": False,
            "status": "emergency_blocked",
            "message": "I cannot automatically call emergency numbers. Please dial emergency services manually.",
        }

    number = normalize_phone_number(target)
    if number:
        if _is_emergency_number(number):
            return {
                "ok": False,
                "status": "emergency_blocked",
                "message": "I cannot automatically call emergency numbers. Please dial emergency services manually.",
            }
        return {
            "ok": True,
            "type": "number",
            "display_name": "that number",
            "phone_number": number,
            "message": "Phone number recognized.",
        }

    resolved = _resolve_contact_phone(target)
    if resolved.get("ok") and _is_emergency_number(resolved.get("phone_number", "")):
        return {
            "ok": False,
            "status": "emergency_blocked",
            "message": "I cannot automatically call emergency numbers. Please dial emergency services manually.",
        }
    return resolved


def call_capability_status():
    return {
        "ok": True,
        "provider": "tel_uri",
        "implemented": True,
        "safety": "Clear non-emergency call intents open the local tel: handler directly. Missing or ambiguous targets ask for clarification.",
        "setup_instruction": "Configure Windows Phone Link or another default tel: handler if calls do not open.",
    }


def initiate_call(target, language="auto"):
    resolved = target if isinstance(target, dict) else resolve_call_target(target)
    if not resolved.get("ok"):
        return {
            "ok": False,
            "called": False,
            "status": resolved.get("status", "unavailable"),
            "message": resolved.get("message") or "I could not resolve who to call.",
        }

    number = resolved.get("phone_number", "")
    if not number:
        return {
            "ok": False,
            "called": False,
            "status": "missing_number",
            "message": "I found the target, but no phone number is available.",
        }
    if _is_emergency_number(number):
        return {
            "ok": False,
            "called": False,
            "status": "emergency_blocked",
            "message": "I cannot automatically call emergency numbers. Please dial emergency services manually.",
        }

    url = f"tel:{number}"
    try:
        opened = bool(webbrowser.open(url, new=0))
    except Exception:
        opened = False
    if not opened:
        return {
            "ok": False,
            "called": False,
            "status": "provider_unavailable",
            "target": resolved.get("display_name", "that number"),
            "message": "Phone Link or default tel: handler is not configured. Set up Windows Phone Link or a default phone app for tel: links.",
        }

    return {
        "ok": True,
        "called": True,
        "status": "started",
        "target": resolved.get("display_name", "that number"),
        "phone_number": number,
        "provider": "tel_uri",
        "message": f"Starting call flow for {resolved.get('display_name', 'that number')} using the Windows tel: handler.",
    }
