from __future__ import annotations

import re
import time
from typing import Any


SUPPORTED_PLATFORMS = {"whatsapp", "telegram", "discord", "slack"}


def compact_text(value: Any, limit: int = 1000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


class NotificationListener:
    """Parser-only notification foundation; it does not subscribe to OS notifications yet."""

    def parse_notification(self, title: str, body: str, *, platform: str = "") -> dict[str, Any]:
        raw_platform = compact_text(platform).lower()
        text = f"{title} {body}".lower()
        if not raw_platform:
            for candidate in SUPPORTED_PLATFORMS:
                if candidate in text:
                    raw_platform = candidate
                    break
        contact = compact_text(title)
        message = compact_text(body, 2000)
        match = re.match(r"([^:]+):\s*(.+)", message)
        if match:
            contact = compact_text(match.group(1))
            message = compact_text(match.group(2), 2000)
        return {
            "ok": True,
            "platform": raw_platform or "unknown",
            "contact": contact,
            "thread": contact,
            "text": message,
            "timestamp": time.time(),
            "unread": True,
        }
