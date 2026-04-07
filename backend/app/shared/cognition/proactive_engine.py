from __future__ import annotations

import datetime

from cognition.insight_engine import generate_user_insights
from cognition.state import load_section, update_section, utc_now
from utils.config import get_setting
from utils.mood_memory import mood_status_payload


def _compact_text(value) -> str:
    return " ".join(str(value or "").split()).strip()


def _parse_timestamp(value: str):
    text = _compact_text(value)
    if not text:
        return None
    try:
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None


def _last_user_timestamp(runtime_payload: dict) -> datetime.datetime | None:
    recent = list((runtime_payload.get("conversation") or {}).get("recent_messages") or [])
    for item in reversed(recent):
        if item.get("role") == "user":
            parsed = _parse_timestamp(item.get("timestamp", ""))
            if parsed is not None:
                return parsed
    return None


def _idle_message(context: str, mood: str) -> str:
    if context == "work":
        return "You have been inactive for a while. Want me to reopen your next priority or recap your plan?"
    if mood in {"sad", "angry"}:
        return "You have been quiet for a bit. Want a gentle reset, a smaller next step, or just a quick check-in?"
    return "You have been inactive for a while. Want a quick suggestion, a break reminder, or your next step?"


def proactive_conversation_status(runtime_payload: dict | None = None) -> dict:
    runtime = runtime_payload or {}
    now = datetime.datetime.now(datetime.timezone.utc)
    last_user = _last_user_timestamp(runtime)
    idle_seconds = int((now - last_user).total_seconds()) if last_user is not None else 0
    idle_threshold = int(get_setting("assistant.proactive_idle_seconds", 900) or 900)
    focus_mode = bool(get_setting("assistant.focus_mode_enabled", False))
    mood = mood_status_payload(limit=4)
    current_context = _compact_text((runtime.get("runtime") or {}).get("current_context")).lower() or "casual"
    section = load_section("proactive", {})
    suggestion = ""
    if idle_seconds >= idle_threshold and not focus_mode:
        suggestion = _idle_message(current_context, mood.get("last_mood", "neutral"))
    return {
        "idle_seconds": idle_seconds,
        "idle_threshold": idle_threshold,
        "idle_detected": idle_seconds >= idle_threshold,
        "focus_mode": focus_mode,
        "suggestion": suggestion,
        "last_idle_nudge_at": _compact_text(section.get("last_idle_nudge_at")),
        "summary": suggestion or "No proactive conversation prompt is needed right now.",
    }


def maybe_generate_idle_nudge(runtime_payload: dict | None = None) -> dict | None:
    status = proactive_conversation_status(runtime_payload)
    if not status.get("idle_detected") or not status.get("suggestion"):
        return None

    section = load_section("proactive", {})
    last_nudge = _parse_timestamp(section.get("last_idle_nudge_at", ""))
    cooldown = int(get_setting("assistant.proactive_idle_cooldown_seconds", 1800) or 1800)
    now = datetime.datetime.now(datetime.timezone.utc)
    if last_nudge is not None and (now - last_nudge).total_seconds() < cooldown:
        return None

    def updater(current):
        data = current if isinstance(current, dict) else {}
        history = list(data.get("suggestions") or [])
        history.append({"created_at": utc_now(), "text": status["suggestion"]})
        data["suggestions"] = history[-20:]
        data["last_idle_nudge_at"] = utc_now()
        data["last_idle_nudge_text"] = status["suggestion"]
        return data

    update_section("proactive", updater)
    payload = dict(status)
    payload["insights"] = generate_user_insights().get("suggestions", [])[:2]
    return payload
