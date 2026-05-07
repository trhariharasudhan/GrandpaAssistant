from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
from typing import Any

from utils.paths import backend_path


KNOWLEDGE_DIR = backend_path("data", "knowledge")
SCIENCE_PATH = os.path.join(KNOWLEDGE_DIR, "basic_science.json")
MATH_PATH = os.path.join(KNOWLEDGE_DIR, "basic_math.json")
THIRUKKURAL_PATH = os.path.join(KNOWLEDGE_DIR, "thirukkural_sample.json")
REVIEW_QUEUE_PATH = os.path.join(KNOWLEDGE_DIR, "review_queue.jsonl")
FALLBACK_REPLY_EN = "I do not have that in my offline knowledge pack yet."
FALLBACK_REPLY_TA = "அது இன்னும் என் உள்ளூர் அறிவுத் தொகுப்பில் இல்லை."
MAX_REVIEW_QUEUE_ITEMS = 500
MAX_REVIEW_QUESTION_CHARS = 220
PRIVATE_PATTERNS = (
    r"\b(password|passcode|pin|otp|token|api[_ -]?key|secret|credential|authorization|bearer)\b",
    r"\b\d{12,19}\b",
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    r"\b(?:\+?\d[\d\s().-]{8,}\d)\b",
)
SIMPLE_FACT_PREFIXES = (
    "what is",
    "what are",
    "who is",
    "who was",
    "when is",
    "when was",
    "where is",
    "where was",
    "tell me",
    "explain",
    "define",
    "meaning of",
    "formula of",
    "what's",
)


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


def _save_json_list(path: str, items: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(items, file, indent=2, ensure_ascii=False)


def _utc_now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _queue_id(normalized_question: str) -> str:
    return hashlib.sha256(normalized_question.encode("utf-8")).hexdigest()[:16]


def _private_looking_text(text: str) -> bool:
    candidate = str(text or "")
    if len(candidate) > MAX_REVIEW_QUESTION_CHARS:
        return True
    return any(re.search(pattern, candidate, flags=re.IGNORECASE) for pattern in PRIVATE_PATTERNS)


def _looks_like_simple_factual_question(question: str) -> bool:
    normalized = _normalize(question)
    if not normalized or len(question) > MAX_REVIEW_QUESTION_CHARS:
        return False
    if _private_looking_text(question):
        return False
    if _looks_tamil(question):
        return "?" in question or len(normalized.split()) <= 16
    if normalized.endswith("?"):
        return True
    return any(normalized.startswith(prefix) for prefix in SIMPLE_FACT_PREFIXES)


def _read_review_queue() -> list[dict[str, Any]]:
    items = []
    try:
        with open(REVIEW_QUEUE_PATH, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    items.append(payload)
    except FileNotFoundError:
        return []
    except Exception:
        return []
    return items[-MAX_REVIEW_QUEUE_ITEMS:]


def _write_review_queue(items: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(REVIEW_QUEUE_PATH), exist_ok=True)
    limited = items[-MAX_REVIEW_QUEUE_ITEMS:]
    with open(REVIEW_QUEUE_PATH, "w", encoding="utf-8") as file:
        for item in limited:
            file.write(json.dumps(item, ensure_ascii=False) + "\n")


def record_knowledge_miss(question: str, *, language: str | None = None) -> dict[str, Any] | None:
    clean_question = _compact_text(question)
    normalized = _normalize(clean_question)
    if not clean_question or not normalized or not _looks_like_simple_factual_question(clean_question):
        return None

    detected_language = language or ("ta" if _looks_tamil(clean_question) else "en")
    items = _read_review_queue()
    existing = next((item for item in items if item.get("normalized_question") == normalized), None)
    if existing:
        return existing

    record = {
        "id": _queue_id(normalized),
        "question": clean_question,
        "normalized_question": normalized,
        "detected_language": detected_language,
        "timestamp": _utc_now(),
        "source": "local_knowledge_miss",
    }
    items.append(record)
    _write_review_queue(items)
    return record


def list_knowledge_review_queue(limit: int = 20) -> list[dict[str, Any]]:
    try:
        resolved_limit = max(1, min(100, int(limit)))
    except Exception:
        resolved_limit = 20
    items = _read_review_queue()
    return list(reversed(items[-resolved_limit:]))


def clear_review_queue_item(item_id: str) -> bool:
    clean_id = _compact_text(item_id)
    if not clean_id:
        return False
    items = _read_review_queue()
    remaining = [item for item in items if item.get("id") != clean_id]
    if len(remaining) == len(items):
        return False
    _write_review_queue(remaining)
    return True


def add_local_knowledge_entry(category, question_patterns, answer_en, answer_ta=None) -> dict[str, Any]:
    clean_category = _compact_text(category).lower()
    if clean_category not in {"science", "math"}:
        raise ValueError("Category must be science or math.")
    if isinstance(question_patterns, str):
        patterns = [_compact_text(item) for item in question_patterns.split("|") if _compact_text(item)]
    else:
        patterns = [_compact_text(item) for item in (question_patterns or []) if _compact_text(item)]
    clean_answer_en = _compact_text(answer_en)
    clean_answer_ta = _compact_text(answer_ta)
    if not patterns or not clean_answer_en:
        raise ValueError("Question patterns and English answer are required.")
    if any(_private_looking_text(value) for value in [*patterns, clean_answer_en, clean_answer_ta]):
        raise ValueError("Knowledge entries must not contain private-looking secrets or credentials.")

    path = SCIENCE_PATH if clean_category == "science" else MATH_PATH
    items = _load_json_list(path)
    normalized_patterns = {_normalize(pattern) for pattern in patterns}
    for item in items:
        existing_patterns = {_normalize(pattern) for pattern in item.get("patterns", [])}
        if normalized_patterns & existing_patterns:
            raise ValueError("A matching knowledge pattern already exists.")
    entry_id = "custom_" + _queue_id("|".join(sorted(normalized_patterns)))
    entry = {
        "id": entry_id,
        "patterns": patterns,
        "answer_en": clean_answer_en,
    }
    if clean_answer_ta:
        entry["answer_ta"] = clean_answer_ta
    items.append(entry)
    _save_json_list(path, items)
    return entry


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

    result = {
        "confident": False,
        "answer": FALLBACK_REPLY_TA if tamil else FALLBACK_REPLY_EN,
        "source": "local_knowledge",
        "category": "fallback",
        "language": "ta" if tamil else "en",
        "question": question,
    }
    queued = record_knowledge_miss(question, language=result["language"])
    if queued:
        result["queued_for_review"] = True
        result["review_id"] = queued.get("id")
    return result


def answer_if_confident(prompt: str) -> str:
    result = lookup_local_knowledge(prompt)
    return result["answer"] if result.get("confident") else ""
