from __future__ import annotations

from typing import Any


def _compact(value: Any, limit: int = 1200) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


class SmartReplyEngine:
    def suggest_replies(self, messages: list[dict[str, Any]], *, tone: str = "warm") -> dict[str, Any]:
        latest = _compact((messages[-1] if messages else {}).get("text", "")).lower()
        suggestions = ["Sure, I will check and get back to you.", "Thanks for the update.", "Sounds good."]
        if "?" in latest:
            suggestions = ["Yes, that works for me.", "Can you share a little more detail?", "I will confirm shortly."]
        if any(word in latest for word in ("urgent", "asap", "important")):
            suggestions = ["I saw this. I will respond as soon as possible.", "Understood, I will prioritize this.", "Thanks, I am checking now."]
        return {"ok": True, "tone": tone, "suggestions": suggestions[:3]}

    def summarize(self, messages: list[dict[str, Any]], *, limit: int = 20) -> dict[str, Any]:
        selected = [message for message in messages if isinstance(message, dict)][-limit:]
        contacts = sorted({str(item.get("contact") or item.get("thread") or "unknown") for item in selected})
        unread = [item for item in selected if item.get("unread")]
        topics = []
        for item in selected[:5]:
            text = _compact(item.get("text"), 140)
            if text:
                topics.append(text)
        summary = "No unread messages found." if not unread else f"{len(unread)} unread message(s) from {', '.join(contacts[:5])}."
        return {"ok": True, "summary": summary, "message_count": len(selected), "unread_count": len(unread), "contacts": contacts[:10], "topic_previews": topics}
