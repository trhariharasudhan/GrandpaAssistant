from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from .notifications import NotificationListener, SUPPORTED_PLATFORMS, compact_text
from .smart_reply import SmartReplyEngine
from .storage import MessageMemory


RISKY_MESSAGE_TERMS = {"payment", "password", "otp", "pin", "confidential", "secret", "resign", "fire", "bank"}


@dataclass(frozen=True)
class ChatPlatformAdapter:
    platform: str
    available: bool = False
    supports_voice: bool = False
    supports_media: bool = False
    missing_adapter: str = "real_chat_app_adapter"


class ChatIntegrationManager:
    """Local-first chat integration coordinator with approval-gated sends."""

    def __init__(
        self,
        *,
        memory: MessageMemory | None = None,
        smart_reply: SmartReplyEngine | None = None,
        notification_listener: NotificationListener | None = None,
        approval_mode: bool | None = None,
    ) -> None:
        self.memory = memory or MessageMemory()
        self.smart_reply = smart_reply or SmartReplyEngine()
        self.notification_listener = notification_listener or NotificationListener()
        self.approval_mode = bool(os.getenv("GRANDPA_CHAT_APPROVAL_MODE", "1").lower() in {"1", "true", "yes", "on"}) if approval_mode is None else approval_mode
        self.adapters = {
            "whatsapp": ChatPlatformAdapter("whatsapp", available=False, supports_voice=True, supports_media=True, missing_adapter="whatsapp_web_playwright_adapter"),
            "telegram": ChatPlatformAdapter("telegram", available=False, supports_voice=True, supports_media=True, missing_adapter="telegram_client_adapter"),
            "discord": ChatPlatformAdapter("discord", available=False, supports_voice=True, supports_media=True, missing_adapter="discord_client_adapter"),
            "slack": ChatPlatformAdapter("slack", available=False, supports_voice=False, supports_media=True, missing_adapter="slack_client_adapter"),
        }

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "approval_mode": self.approval_mode,
            "supported_platforms": sorted(SUPPORTED_PLATFORMS),
            "adapters": {name: adapter.__dict__ for name, adapter in self.adapters.items()},
            "memory": self.memory.status(),
        }

    def ingest_notification(self, title: str, body: str, *, platform: str = "") -> dict[str, Any]:
        message = self.notification_listener.parse_notification(title, body, platform=platform)
        self.memory.remember_message(message)
        self.memory.add_contact(message["platform"], message["contact"])
        return {"ok": True, "message": message}

    def read_messages(self, *, platform: str = "", contact: str = "", unread_only: bool = False, limit: int = 20) -> dict[str, Any]:
        payload = self.memory.load()
        app = compact_text(platform).lower()
        person = compact_text(contact).lower()
        messages = []
        for message in payload.get("messages", []):
            if app and app != compact_text(message.get("platform")).lower():
                continue
            if person and person not in f"{message.get('contact', '')} {message.get('thread', '')}".lower():
                continue
            if unread_only and not message.get("unread"):
                continue
            messages.append(message)
        return {"ok": True, "messages": messages[-max(1, min(limit, 100)):], "message_count": len(messages)}

    def search_contacts(self, query: str, *, platform: str = "") -> dict[str, Any]:
        return {"ok": True, "contacts": self.memory.search_contacts(query, platform), "query": compact_text(query)}

    def suggest_replies(self, *, platform: str = "", contact: str = "", tone: str = "warm") -> dict[str, Any]:
        messages = self.read_messages(platform=platform, contact=contact, limit=10).get("messages", [])
        return self.smart_reply.suggest_replies(messages, tone=tone)

    def summarize_unread(self, *, platform: str = "") -> dict[str, Any]:
        messages = self.read_messages(platform=platform, unread_only=True, limit=50).get("messages", [])
        return self.smart_reply.summarize(messages)

    def send_message(self, *, platform: str, contact: str, text: str, approved: bool = False, media_path: str = "", voice: bool = False) -> dict[str, Any]:
        app = compact_text(platform).lower()
        adapter = self.adapters.get(app)
        if adapter is None:
            return {"ok": False, "requires_approval": False, "message": f"I understood the message intent, but {platform} is not a supported chat platform.", "missing_adapter": "unsupported_platform"}
        safe_text = compact_text(text, 4000)
        risky = any(term in safe_text.lower() for term in RISKY_MESSAGE_TERMS)
        if self.approval_mode and not approved:
            return {
                "ok": False,
                "requires_approval": True,
                "risk_level": "high_confirmation" if risky else "medium_confirmation",
                "message": f"Approval required before sending a {adapter.platform} message to {compact_text(contact)}.",
                "draft": {"platform": adapter.platform, "contact": compact_text(contact), "text": safe_text, "media_path": compact_text(media_path), "voice": bool(voice)},
            }
        if not adapter.available:
            return {
                "ok": False,
                "requires_approval": False,
                "message": f"I understood you want to send a message on {adapter.platform}, but the {adapter.missing_adapter} is not connected yet.",
                "missing_adapter": adapter.missing_adapter,
            }
        outgoing = {"platform": adapter.platform, "contact": contact, "thread": contact, "direction": "outgoing", "text": safe_text, "media_type": "voice" if voice else ("media" if media_path else ""), "timestamp": time.time(), "unread": False}
        self.memory.remember_message(outgoing)
        return {"ok": True, "message": f"Sent message to {compact_text(contact)} on {adapter.platform}.", "delivery": outgoing}

    def mute_thread(self, *, platform: str, thread: str, approved: bool = False) -> dict[str, Any]:
        if self.approval_mode and not approved:
            return {"ok": False, "requires_approval": True, "message": f"Approval required before muting {compact_text(thread)}."}
        payload = self.memory.load()
        muted = payload.setdefault("muted_threads", [])
        item = {"platform": compact_text(platform).lower(), "thread": compact_text(thread)}
        if item not in muted:
            muted.append(item)
        self.memory.save(payload)
        return {"ok": True, "message": f"Muted {compact_text(thread)} locally.", "muted": item}


_GLOBAL_MANAGER: ChatIntegrationManager | None = None


def get_chat_integration_manager() -> ChatIntegrationManager:
    global _GLOBAL_MANAGER
    if _GLOBAL_MANAGER is None:
        _GLOBAL_MANAGER = ChatIntegrationManager()
    return _GLOBAL_MANAGER
