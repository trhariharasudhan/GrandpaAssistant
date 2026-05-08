from __future__ import annotations

import datetime
import json
import os
import re
from typing import Any

try:
    from utils.paths import backend_data_path
except Exception:
    backend_data_path = None


CONTACTS_PATH = (
    backend_data_path("contacts", "contacts.json")
    if backend_data_path
    else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "contacts", "contacts.json"))
)


def _utc_now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def normalize_contact_name(name):
    text = _compact_text(name).lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return _compact_text(text)


def validate_contact_phone(phone):
    raw = _compact_text(phone)
    leading_plus = raw.startswith("+")
    digits = re.sub(r"\D+", "", raw)
    if len(digits) < 7 or len(digits) > 15:
        return {"ok": False, "phone": "", "message": "Phone number must contain 7 to 15 digits."}
    return {"ok": True, "phone": f"+{digits}" if leading_plus else digits, "message": "Phone number is valid."}


def _ensure_dir() -> None:
    os.makedirs(os.path.dirname(CONTACTS_PATH), exist_ok=True)


def _load_contacts() -> list[dict[str, Any]]:
    if not os.path.exists(CONTACTS_PATH):
        return []
    try:
        with open(CONTACTS_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _save_contacts(contacts: list[dict[str, Any]]) -> None:
    _ensure_dir()
    with open(CONTACTS_PATH, "w", encoding="utf-8") as handle:
        json.dump(contacts, handle, ensure_ascii=True, indent=2, sort_keys=True)


def _redact_phone(phone: str) -> str:
    digits = re.sub(r"\D+", "", str(phone or ""))
    if not digits:
        return ""
    return "*" * max(0, len(digits) - 4) + digits[-4:]


def redact_contact_for_display(contact):
    contact = contact or {}
    return {
        "name": contact.get("name", ""),
        "phone": _redact_phone(contact.get("phone", "")),
        "labels": list(contact.get("labels") or [])[:10],
        "updated_at": contact.get("updated_at", ""),
    }


def add_contact(name, phone, labels=None):
    display_name = _compact_text(name)
    normalized = normalize_contact_name(display_name)
    if not normalized:
        return {"ok": False, "status": "invalid_name", "message": "Contact name is required."}
    phone_result = validate_contact_phone(phone)
    if not phone_result["ok"]:
        return {"ok": False, "status": "invalid_phone", "message": phone_result["message"]}
    contacts = _load_contacts()
    if any(item.get("normalized_name") == normalized for item in contacts):
        return {"ok": False, "status": "duplicate", "message": f"Contact {display_name} already exists."}
    now = _utc_now()
    contact = {
        "name": display_name,
        "normalized_name": normalized,
        "phone": phone_result["phone"],
        "labels": [str(item).strip() for item in (labels or []) if str(item).strip()][:10],
        "created_at": now,
        "updated_at": now,
    }
    contacts.append(contact)
    contacts.sort(key=lambda item: item.get("normalized_name", ""))
    _save_contacts(contacts)
    return {"ok": True, "status": "added", "contact": redact_contact_for_display(contact), "message": f"Added contact {display_name}."}


def find_contact(query):
    normalized = normalize_contact_name(query)
    if not normalized:
        return {"ok": False, "status": "missing_query", "matches": [], "message": "Contact name is required."}
    contacts = _load_contacts()
    exact = [item for item in contacts if item.get("normalized_name") == normalized]
    if len(exact) == 1:
        return {"ok": True, "status": "found", "contact": exact[0], "matches": exact, "message": f"Found {exact[0].get('name')}."}
    matches = [
        item for item in contacts
        if normalized in item.get("normalized_name", "") or item.get("normalized_name", "") in normalized
    ]
    if len(matches) == 1:
        return {"ok": True, "status": "found", "contact": matches[0], "matches": matches, "message": f"Found {matches[0].get('name')}."}
    if len(matches) > 1:
        names = ", ".join(item.get("name", "Unknown") for item in matches[:5])
        return {"ok": False, "status": "ambiguous", "matches": matches, "message": f"I found multiple local contacts for {query}: {names}. Say the exact name."}
    return {"ok": False, "status": "not_found", "matches": [], "message": f"I could not find local contact {query}. Add the contact or provide a phone number."}


def list_contacts(limit=50):
    try:
        limit_value = max(1, int(limit))
    except Exception:
        limit_value = 50
    return [redact_contact_for_display(item) for item in _load_contacts()[:limit_value]]


def delete_contact(name):
    normalized = normalize_contact_name(name)
    if not normalized:
        return {"ok": False, "status": "missing_name", "message": "Contact name is required."}
    contacts = _load_contacts()
    remaining = [item for item in contacts if item.get("normalized_name") != normalized]
    if len(remaining) == len(contacts):
        return {"ok": False, "status": "not_found", "message": f"I could not find local contact {name}."}
    _save_contacts(remaining)
    return {"ok": True, "status": "deleted", "message": f"Deleted local contact {name}."}
