from __future__ import annotations

import re
from typing import Any

from .models import DomainClassification, compact_text


BROWSER_HINTS = {
    "browser",
    "google",
    "search",
    "youtube",
    "website",
    "web",
    "linkedin",
    "swiggy",
    "zomato",
    "open site",
}
CHAT_HINTS = {
    "send message",
    "reply",
    "whatsapp",
    "telegram",
    "discord",
    "slack",
    "good morning",
    "family",
    "summarize unread",
    "mute group",
}
VISUAL_HINTS = {
    "screen",
    "screenshot",
    "what is on",
    "enna iruku",
    "paaru",
    "read this error",
    "click",
    "popup",
    "login button",
}
AGENT_HINTS = {
    "book",
    "ticket",
    "cab",
    "hungry",
    "order",
    "prepare",
    "meeting notes",
    "today's report",
    "multi step",
}
GENERAL_HINTS = {"hi", "hello", "hey", "thanks", "joke", "how are you"}


class IntentMapper:
    """Deterministic broad-domain mapper for local action systems."""

    def classify(self, command: str) -> DomainClassification:
        text = compact_text(command, 2000)
        normalized = text.lower()
        if not normalized:
            return DomainClassification(text, "general", 0.95, "Empty command; no local action requested.")

        scores = {
            "browser": self._score(normalized, BROWSER_HINTS),
            "chat": self._score(normalized, CHAT_HINTS),
            "visual_desktop": self._score(normalized, VISUAL_HINTS),
            "autonomous_agent": self._score(normalized, AGENT_HINTS),
            "general": self._score(normalized, GENERAL_HINTS),
        }
        if re.search(r"\b(send|reply)\b.+\b(to|family|group|riya|riyaa)\b", normalized):
            scores["chat"] += 0.45
        if re.search(r"\b(open|search|google)\b", normalized):
            scores["browser"] += 0.25
        if re.search(r"\b(book|order|prepare|plan)\b", normalized):
            scores["autonomous_agent"] += 0.25
        if "screen la" in normalized or "enna iruku" in normalized:
            scores["visual_desktop"] += 0.6

        domain = max(scores, key=scores.get)
        top_score = scores[domain]
        if top_score <= 0:
            domain = "general"
            top_score = 0.55
        confidence = min(0.98, max(0.45, top_score))
        reason = self._reason(domain, normalized)
        return DomainClassification(text, domain, confidence, reason, slots=self._slots(domain, text))

    def _score(self, normalized: str, hints: set[str]) -> float:
        score = 0.0
        for hint in hints:
            if hint in normalized:
                score += 0.28 if " " in hint else 0.18
        return score

    def _reason(self, domain: str, normalized: str) -> str:
        if domain == "browser":
            return "Command mentions browser, web search, website, or browser-owned task."
        if domain == "chat":
            return "Command asks to send, reply, summarize, mute, or search chat messages."
        if domain == "visual_desktop":
            return "Command refers to current screen, OCR, UI, popup, or visual desktop action."
        if domain == "autonomous_agent":
            return "Command implies a multi-step goal that needs planning and confirmation checkpoints."
        return "Command looks conversational or does not require a local action system."

    def _slots(self, domain: str, text: str) -> dict[str, Any]:
        normalized = text.lower()
        if domain == "chat":
            contact = ""
            match = re.search(r"\b(?:to|reply to)\s+([a-zA-Z0-9 _.-]+?)(?:\s+that\b|$)", text, flags=re.IGNORECASE)
            if match:
                contact = compact_text(match.group(1), 120)
            return {"contact": contact, "message_hint": compact_text(text, 300)}
        if domain == "browser":
            query = re.sub(r"^(open\s+browser\s+and\s+|browser\s+|google\s+|search\s+)", "", normalized).strip()
            return {"query": compact_text(query or text, 300)}
        if domain == "visual_desktop":
            return {"screen_request": compact_text(text, 300)}
        if domain == "autonomous_agent":
            return {"goal": compact_text(text, 500)}
        return {}
