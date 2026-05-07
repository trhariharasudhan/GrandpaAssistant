from __future__ import annotations

import datetime
import json
import os
import re
from typing import Any

from utils.paths import backend_path


KNOWLEDGE_DIR = backend_path("data", "knowledge")
SCIENCE_PATH = os.path.join(KNOWLEDGE_DIR, "basic_science.json")
MATH_PATH = os.path.join(KNOWLEDGE_DIR, "basic_math.json")
THIRUKKURAL_PATH = os.path.join(KNOWLEDGE_DIR, "thirukkural_sample.json")
FALLBACK_REPLY_EN = "I do not have that in my offline knowledge pack yet."
FALLBACK_REPLY_TA = "அது இன்னும் என் உள்ளூர் அறிவுத் தொகுப்பில் இல்லை."


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize(value: Any) -> str:
    text = _compact_text(value).lower()
    text = re.sub(r"user question:\s*", " ", text)
    text = re.sub(r"[^a-z0-9\u0b80-\u0bff\s]+", " ", text)
    return _compact_text(text)


def _looks_tamil(text: str) -> bool:
    return any("\u0b80" <= char <= "\u0bff" for char in str(text or ""))


def _extract_question(prompt: str) -> str:
    text = str(prompt or "").strip()
    matches = re.findall(r"User question:\s*(.+)", text, flags=re.IGNORECASE)
    if matches:
        return _compact_text(matches[-1])
    return _compact_text(text)


def _load_json_list(path: str) -> list[dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


def _answer_for_language(item: dict[str, Any], tamil: bool) -> str:
    if tamil:
        return _compact_text(item.get("answer_ta")) or _compact_text(item.get("answer_en"))
    return _compact_text(item.get("answer_en")) or _compact_text(item.get("answer_ta"))


def _matches_pattern(normalized_query: str, pattern: str) -> bool:
    normalized_pattern = _normalize(pattern)
    if not normalized_pattern:
        return False
    if normalized_pattern in normalized_query:
        return True
    pattern_words = normalized_pattern.split()
    query_words = set(normalized_query.split())
    if len(pattern_words) >= 2 and all(word in query_words for word in pattern_words):
        return True
    return False


def _lookup_structured_fact(query: str, tamil: bool) -> dict[str, Any] | None:
    normalized = _normalize(query)
    for category, path in (("science", SCIENCE_PATH), ("math", MATH_PATH)):
        for item in _load_json_list(path):
            patterns = item.get("patterns") or []
            if any(_matches_pattern(normalized, str(pattern)) for pattern in patterns):
                answer = _answer_for_language(item, tamil)
                if answer:
                    return {
                        "confident": True,
                        "answer": answer,
                        "source": "local_knowledge",
                        "category": category,
                        "id": item.get("id", ""),
                    }
    return None


def _time_or_date_answer(query: str, tamil: bool) -> dict[str, Any] | None:
    normalized = _normalize(query)
    time_terms = ("time now", "what is time", "current time", "tell me time", "நேரம்", "மணி")
    date_terms = ("date today", "what is the date", "current date", "today date", "தேதி", "இன்று")
    if not any(term in normalized for term in time_terms + date_terms):
        return None

    now = datetime.datetime.now()
    if tamil:
        answer = f"இப்போது நேரம் {now.strftime('%I:%M %p')}. இன்று {now.strftime('%A, %d %B %Y')}."
    elif any(term in normalized for term in date_terms) and not any(term in normalized for term in time_terms):
        answer = now.strftime("Today is %A, %d %B %Y.")
    else:
        answer = now.strftime("It is %I:%M %p on %A, %d %B %Y.")
    return {
        "confident": True,
        "answer": answer,
        "source": "local_knowledge",
        "category": "time_date",
    }


def _thirukkural_answer(query: str, tamil: bool) -> dict[str, Any] | None:
    normalized = _normalize(query)
    if not any(term in normalized for term in ("thirukkural", "thirukural", "kural", "திருக்குறள்", "குறள்")):
        return None
    items = _load_json_list(THIRUKKURAL_PATH)
    if not items:
        return None
    match = re.search(r"\b(\d{1,4})\b", normalized)
    selected = None
    if match:
        number = int(match.group(1))
        selected = next((item for item in items if int(item.get("number", 0) or 0) == number), None)
    selected = selected or items[0]
    kural = _compact_text(selected.get("kural_ta"))
    meaning = _compact_text(selected.get("meaning_ta" if tamil else "meaning_en"))
    if tamil:
        answer = f"திருக்குறள் {selected.get('number')}: {kural} பொருள்: {meaning}"
    else:
        answer = f"Thirukkural {selected.get('number')}: {kural} Meaning: {meaning}"
    return {
        "confident": True,
        "answer": answer,
        "source": "local_knowledge",
        "category": "thirukkural",
        "id": str(selected.get("number", "")),
    }


def lookup_local_knowledge(prompt: str) -> dict[str, Any]:
    question = _extract_question(prompt)
    tamil = _looks_tamil(question)
    if not question:
        return {
            "confident": False,
            "answer": FALLBACK_REPLY_TA if tamil else FALLBACK_REPLY_EN,
            "source": "local_knowledge",
            "category": "fallback",
        }

    for resolver in (_time_or_date_answer, _thirukkural_answer, _lookup_structured_fact):
        result = resolver(question, tamil)
        if result and _normalize(result.get("answer")) != _normalize(question):
            result["language"] = "ta" if tamil else "en"
            result["question"] = question
            return result

    return {
        "confident": False,
        "answer": FALLBACK_REPLY_TA if tamil else FALLBACK_REPLY_EN,
        "source": "local_knowledge",
        "category": "fallback",
        "language": "ta" if tamil else "en",
        "question": question,
    }


def answer_if_confident(prompt: str) -> str:
    result = lookup_local_knowledge(prompt)
    return result["answer"] if result.get("confident") else ""
