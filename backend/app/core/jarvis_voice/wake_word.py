from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def normalize_phrase(value: Any) -> str:
    text = _compact_text(value).lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class WakeWordEngine:
    def __init__(self, wake_words: list[str] | None = None, *, threshold: float = 0.86) -> None:
        words = wake_words or ["hey grandpa"]
        self.wake_words = [normalize_phrase(word) for word in words if normalize_phrase(word)] or ["hey grandpa"]
        self.threshold = max(0.5, min(float(threshold), 1.0))

    def detect(self, transcript: str) -> bool:
        return bool(self.extract_command(transcript)["wake_detected"])

    def extract_command(self, transcript: str) -> dict[str, Any]:
        normalized = normalize_phrase(transcript)
        if not normalized:
            return {"wake_detected": False, "wake_word": "", "command": "", "confidence": 0.0}
        for wake in sorted(self.wake_words, key=len, reverse=True):
            if normalized == wake:
                return {"wake_detected": True, "wake_word": wake, "command": "", "confidence": 1.0}
            if normalized.startswith(wake + " "):
                return {
                    "wake_detected": True,
                    "wake_word": wake,
                    "command": _compact_text(transcript)[len(wake) :].strip(" ,.!?"),
                    "confidence": 1.0,
                }
            prefix = " ".join(normalized.split()[: len(wake.split())])
            confidence = SequenceMatcher(None, prefix, wake).ratio()
            if confidence >= self.threshold:
                remainder = " ".join(normalized.split()[len(wake.split()) :])
                return {"wake_detected": True, "wake_word": wake, "command": remainder, "confidence": round(confidence, 3)}
        return {"wake_detected": False, "wake_word": "", "command": "", "confidence": 0.0}
