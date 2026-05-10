from __future__ import annotations

import re


TAMIL_UNICODE_RE = re.compile(r"[\u0B80-\u0BFF]")
TANGLISH_WORDS = {
    "da",
    "dei",
    "machan",
    "macha",
    "enna",
    "epdi",
    "eppadi",
    "seri",
    "sari",
    "venum",
    "pannu",
    "panradhu",
    "puriyudhu",
    "iruku",
    "illa",
    "romba",
    "konjam",
    "nan",
    "naan",
    "unga",
    "nalla",
}


def detect_language_style(text: str) -> str:
    cleaned = str(text or "").strip().lower()
    if not cleaned:
        return "english"
    if TAMIL_UNICODE_RE.search(cleaned):
        return "tamil"
    words = set(re.findall(r"[a-zA-Z]+", cleaned))
    if words.intersection(TANGLISH_WORDS):
        return "tanglish"
    return "english"


def language_instruction(style: str) -> str:
    if style == "tamil":
        return "Reply in natural Tamil when possible, with simple wording."
    if style == "tanglish":
        return "Reply in natural Tanglish. Casual phrases like 'seri da', 'super da', and 'puriyudhu da' are okay when they fit."
    return "Reply in natural English."
