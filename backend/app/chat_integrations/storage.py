from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

try:
    from utils.paths import runtime_path
except Exception:  # pragma: no cover
    runtime_path = None


def _runtime_file() -> str:
    if runtime_path is not None:
        return runtime_path("chat_integrations", "message_memory.enc")
    return os.path.join("runtime", "chat_integrations", "message_memory.enc")


def _compact(value: Any, limit: int = 1000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _key_bytes() -> bytes:
    seed = os.getenv("GRANDPA_CHAT_STORAGE_KEY") or "grandpa-local-chat-memory"
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _xor_crypt(data: bytes) -> bytes:
    key = _key_bytes()
    return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data))


def _encrypt_json(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(_xor_crypt(raw)).decode("ascii")


def _decrypt_json(text: str) -> dict[str, Any]:
    raw = _xor_crypt(base64.urlsafe_b64decode(text.encode("ascii")))
    payload = json.loads(raw.decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


class MessageMemory:
    """Small encrypted-at-rest local store for safe chat metadata and message text."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or _runtime_file()

    def load(self) -> dict[str, Any]:
        try:
            if not os.path.exists(self.path):
                return self._empty()
            text = Path(self.path).read_text(encoding="utf-8").strip()
            if not text:
                return self._empty()
            payload = _decrypt_json(text)
            payload.setdefault("messages", [])
            payload.setdefault("contacts", [])
            payload.setdefault("muted_threads", [])
            payload.setdefault("created_at", time.time())
            payload["encrypted_at_rest"] = True
            return payload
        except Exception:
            return self._empty(error="memory_unreadable")

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        safe_payload = payload if isinstance(payload, dict) else self._empty()
        safe_payload["encrypted_at_rest"] = True
        safe_payload["updated_at"] = time.time()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        Path(tmp).write_text(_encrypt_json(safe_payload), encoding="utf-8")
        os.replace(tmp, self.path)
        return {"ok": True, "path": self.path, "encrypted_at_rest": True}

    def remember_message(self, message: dict[str, Any]) -> dict[str, Any]:
        payload = self.load()
        messages = payload.setdefault("messages", [])
        safe = {
            "platform": _compact(message.get("platform"), 40),
            "contact": _compact(message.get("contact"), 120),
            "thread": _compact(message.get("thread"), 120),
            "direction": _compact(message.get("direction"), 20) or "incoming",
            "text": _compact(message.get("text"), 4000),
            "media_type": _compact(message.get("media_type"), 40),
            "timestamp": float(message.get("timestamp") or time.time()),
            "unread": bool(message.get("unread", True)),
        }
        messages.append(safe)
        payload["messages"] = messages[-500:]
        return self.save(payload)

    def add_contact(self, platform: str, name: str, handle: str = "") -> None:
        payload = self.load()
        contacts = payload.setdefault("contacts", [])
        item = {"platform": _compact(platform, 40), "name": _compact(name, 120), "handle": _compact(handle, 120)}
        if item not in contacts:
            contacts.append(item)
            payload["contacts"] = contacts[-500:]
            self.save(payload)

    def search_contacts(self, query: str, platform: str = "") -> list[dict[str, Any]]:
        needle = _compact(query).lower()
        app = _compact(platform).lower()
        contacts = self.load().get("contacts", [])
        results = []
        for contact in contacts:
            haystack = f"{contact.get('name', '')} {contact.get('handle', '')}".lower()
            if needle and needle in haystack and (not app or app == str(contact.get("platform", "")).lower()):
                results.append(contact)
        return results[:10]

    def status(self) -> dict[str, Any]:
        payload = self.load()
        counts: dict[str, int] = {}
        for message in payload.get("messages", []):
            platform = _compact((message or {}).get("platform")) or "unknown"
            counts[platform] = counts.get(platform, 0) + 1
        return {
            "ok": True,
            "path": self.path,
            "encrypted_at_rest": True,
            "message_count": len(payload.get("messages", [])),
            "contact_count": len(payload.get("contacts", [])),
            "muted_thread_count": len(payload.get("muted_threads", [])),
            "message_count_by_platform": counts,
        }

    def _empty(self, *, error: str = "") -> dict[str, Any]:
        return {"messages": [], "contacts": [], "muted_threads": [], "encrypted_at_rest": True, "created_at": time.time(), "error": error}
