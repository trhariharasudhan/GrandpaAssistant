from __future__ import annotations

import copy
import datetime
import json
import os


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "backend", "data")
MOOD_MEMORY_PATH = os.path.join(DATA_DIR, "mood_memory.json")
MAX_MOOD_HISTORY = 160

DEFAULT_MOOD_MEMORY = {
    "last_mood": "neutral",
    "last_compound": 0.0,
    "last_updated_at": "",
    "history": [],
}


def _utc_now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _preview_text(text: str | None, limit: int = 120) -> str:
    compact = " ".join(str(text or "").split()).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _normalize_history_entry(item):
    if isinstance(item, str):
        return {
            "emotion": item.strip().lower() or "neutral",
            "compound": 0.0,
            "source": "legacy",
            "timestamp": "",
            "text_preview": "",
        }
    if not isinstance(item, dict):
        return None
    emotion = " ".join(str(item.get("emotion", "neutral")).split()).strip().lower() or "neutral"
    return {
        "emotion": emotion,
        "compound": round(float(item.get("compound", 0.0) or 0.0), 4),
        "source": " ".join(str(item.get("source", "unknown")).split()).strip() or "unknown",
        "timestamp": " ".join(str(item.get("timestamp", "")).split()).strip(),
        "text_preview": _preview_text(item.get("text_preview", "")),
    }


def _normalized_payload(data) -> dict:
    if not isinstance(data, dict):
        data = {}
    history = []
    for item in data.get("history", []):
        normalized = _normalize_history_entry(item)
        if normalized is not None:
            history.append(normalized)
    history = history[-MAX_MOOD_HISTORY:]
    last_mood = " ".join(str(data.get("last_mood", "neutral")).split()).strip().lower() or "neutral"
    return {
        "last_mood": last_mood,
        "last_compound": round(float(data.get("last_compound", 0.0) or 0.0), 4),
        "last_updated_at": " ".join(str(data.get("last_updated_at", "")).split()).strip(),
        "history": history,
    }


def _write_payload(payload: dict) -> None:
    _ensure_data_dir()
    with open(MOOD_MEMORY_PATH, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def ensure_mood_memory_file() -> None:
    _ensure_data_dir()
    if not os.path.exists(MOOD_MEMORY_PATH):
        _write_payload(copy.deepcopy(DEFAULT_MOOD_MEMORY))


def load_mood_memory() -> dict:
    ensure_mood_memory_file()
    try:
        with open(MOOD_MEMORY_PATH, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:
        payload = copy.deepcopy(DEFAULT_MOOD_MEMORY)
        _write_payload(payload)
        return payload

    normalized = _normalized_payload(payload)
    if normalized != payload:
        _write_payload(normalized)
    return normalized


def save_mood_memory(payload: dict) -> dict:
    normalized = _normalized_payload(payload)
    _write_payload(normalized)
    return normalized


def _counts(history: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in history:
        emotion = item.get("emotion", "neutral")
        counts[emotion] = counts.get(emotion, 0) + 1
    return counts


def _streak(history: list[dict], last_mood: str) -> int:
    if not history or not last_mood:
        return 0
    streak = 0
    for item in reversed(history):
        if item.get("emotion") != last_mood:
            break
        streak += 1
    return streak


def mood_status_payload(limit: int = 8) -> dict:
    payload = load_mood_memory()
    history = payload.get("history", [])
    recent_entries = history[-max(1, limit):]
    previous_mood = history[-2]["emotion"] if len(history) >= 2 else payload.get("last_mood", "neutral")
    previous_distinct = payload.get("last_mood", "neutral")
    for item in reversed(history[:-1]):
        if item.get("emotion") != payload.get("last_mood"):
            previous_distinct = item.get("emotion", "neutral")
            break
    return {
        "last_mood": payload.get("last_mood", "neutral"),
        "previous_mood": previous_mood,
        "previous_distinct_mood": previous_distinct,
        "last_compound": payload.get("last_compound", 0.0),
        "last_updated_at": payload.get("last_updated_at", ""),
        "history_count": len(history),
        "recent_moods": [item.get("emotion", "neutral") for item in recent_entries],
        "recent_history": recent_entries,
        "counts": _counts(history),
        "streak": _streak(history, payload.get("last_mood", "neutral")),
    }


def record_mood(emotion: str, *, compound: float = 0.0, text: str = "", source: str = "chat") -> dict:
    payload = load_mood_memory()
    history = list(payload.get("history", []))
    entry = {
        "emotion": " ".join(str(emotion or "neutral").split()).strip().lower() or "neutral",
        "compound": round(float(compound or 0.0), 4),
        "source": " ".join(str(source or "chat").split()).strip() or "chat",
        "timestamp": _utc_now(),
        "text_preview": _preview_text(text),
    }
    history.append(entry)
    payload["history"] = history[-MAX_MOOD_HISTORY:]
    payload["last_mood"] = entry["emotion"]
    payload["last_compound"] = entry["compound"]
    payload["last_updated_at"] = entry["timestamp"]
    save_mood_memory(payload)
    snapshot = mood_status_payload()
    snapshot["current_event"] = entry
    return snapshot


def record_mood_from_analysis(text: str, analysis: dict, source: str = "chat") -> dict:
    return record_mood(
        analysis.get("emotion", "neutral"),
        compound=float(analysis.get("compound", 0.0) or 0.0),
        text=text,
        source=source,
    )


def build_mood_memory_context(snapshot: dict | None = None) -> str:
    snapshot = snapshot or mood_status_payload(limit=5)
    last_mood = snapshot.get("last_mood", "neutral")
    previous_mood = snapshot.get("previous_distinct_mood") or snapshot.get("previous_mood") or last_mood
    recent_moods = snapshot.get("recent_moods", [])[-4:]
    recent_pattern = ", ".join(recent_moods) if recent_moods else last_mood
    return (
        f"User previous mood: {previous_mood}.\n"
        f"Recent mood pattern: {recent_pattern}.\n"
        f"Current stored mood memory: {last_mood}."
    )


def reset_mood_memory() -> dict:
    payload = copy.deepcopy(DEFAULT_MOOD_MEMORY)
    save_mood_memory(payload)
    return mood_status_payload()
