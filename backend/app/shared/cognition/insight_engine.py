from __future__ import annotations

import datetime
import os
import sqlite3
from collections import Counter

from cognition.learning_engine import learning_status_payload
from utils.mood_memory import mood_status_payload


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "backend", "data", "assistant.db")


def _compact_text(value) -> str:
    return " ".join(str(value or "").split()).strip()


def _connect():
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def _recent_command_rows(limit: int = 200) -> list:
    if not os.path.exists(DB_PATH):
        return []
    connection = _connect()
    try:
        return connection.execute(
            "SELECT command_text, created_at FROM command_history ORDER BY id DESC LIMIT ?",
            (max(1, int(limit)),),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        connection.close()


def _parse_iso(text: str):
    cleaned = _compact_text(text)
    if not cleaned:
        return None
    try:
        return datetime.datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except Exception:
        return None


def _hour_label(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "late night"


def generate_user_insights() -> dict:
    rows = _recent_command_rows()
    hour_counter = Counter()
    command_counter = Counter()
    for row in rows:
        command = _compact_text(row["command_text"]).lower()
        if command:
            command_counter[command] += 1
        created_at = _parse_iso(row["created_at"])
        if created_at is not None:
            hour_counter[created_at.hour] += 1

    learning = learning_status_payload()
    mood = mood_status_payload(limit=12)
    busy_hour = hour_counter.most_common(1)[0][0] if hour_counter else None
    busiest_window = _hour_label(busy_hour) if busy_hour is not None else "unknown"
    common_commands = [item[0] for item in command_counter.most_common(4)]
    mood_counts = mood.get("counts", {})
    dominant_mood = max(mood_counts.items(), key=lambda item: item[1])[0] if mood_counts else "neutral"
    learned_preferences = learning.get("user_preferences", {})
    behavior_learning = learning.get("behavior_learning", {})
    automation_suggestions = learning.get("automation_suggestions", [])

    productivity_patterns = []
    if busy_hour is not None:
        productivity_patterns.append(f"You tend to use the assistant most during the {busiest_window}.")
    if common_commands:
        productivity_patterns.append("Most frequent actions: " + ", ".join(common_commands[:3]) + ".")
    preferred_length = learned_preferences.get("response_length", "adaptive")
    if preferred_length == "short":
        productivity_patterns.append("You usually prefer quick, concise responses.")
    elif preferred_length == "detailed":
        productivity_patterns.append("You usually prefer fuller explanations when they are useful.")
    learned_window = behavior_learning.get("active_time_window", "unknown")
    if learned_window != "unknown" and learned_window != busiest_window:
        productivity_patterns.append(f"Conversation history also suggests you are often active during the {learned_window}.")
    if not productivity_patterns:
        productivity_patterns.append("There is not enough usage history yet to infer a strong productivity pattern.")

    mood_trends = []
    if mood.get("history_count", 0):
        mood_trends.append(
            f"Recent mood trend looks mostly {dominant_mood} with a streak of {mood.get('streak', 0)}."
        )
        if mood_counts.get("sad", 0) + mood_counts.get("angry", 0) > mood_counts.get("happy", 0):
            mood_trends.append("Recent mood has leaned heavier, so a lighter schedule could help.")
    else:
        mood_trends.append("Mood tracking has not collected enough history yet.")

    suggestions = []
    if busy_hour is not None:
        suggestions.append(f"Protect a focused block around your usual peak time in the {busiest_window}.")
    if dominant_mood in {"sad", "angry"}:
        suggestions.append("Try a shorter task list and one quick win before going deep.")
    if learning.get("success_rate", 0) < 50 and learning.get("feedback_count", 0) >= 3:
        suggestions.append("Use feedback more often so the assistant can adapt its response style faster.")
    for item in automation_suggestions[:2]:
        message = _compact_text(item.get("message"))
        if message:
            suggestions.append(message)
    if not suggestions:
        suggestions.append("Keep using planning and notes consistently so the assistant can personalize better.")

    return {
        "usage_count": len(rows),
        "busiest_hour": busy_hour,
        "busiest_window": busiest_window,
        "top_commands": common_commands,
        "dominant_mood": dominant_mood,
        "productivity_patterns": productivity_patterns,
        "mood_trends": mood_trends,
        "suggestions": suggestions,
        "summary": f"Insights ready from {len(rows)} command events and {mood.get('history_count', 0)} mood snapshots.",
    }
