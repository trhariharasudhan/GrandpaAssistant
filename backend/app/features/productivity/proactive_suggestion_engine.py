import datetime
import json
import os
import sqlite3
import threading
import time
from collections import Counter
from contextlib import suppress

from shared.utils.config import get_setting
from shared.utils.paths import backend_data_dir, backend_data_path
import voice.speak as voice_speak_module

DATA_DIR = backend_data_dir()
DB_PATH = backend_data_path("assistant.db")
CHAT_STATE_PATH = backend_data_path("chat_state.json")
TASKS_PATH = backend_data_path("tasks.json")
SUGGESTION_POLL_SECONDS = 300

_background_thread = None
_background_stop = threading.Event()


def _connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_tables():
    connection = _connect()
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS proactive_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                suggestion_text TEXT NOT NULL,
                suggestion_kind TEXT NOT NULL,
                score REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def _flatten_memory(memory, parent_key=""):
    flattened = {}
    if not isinstance(memory, dict):
        return flattened
    for key, value in memory.items():
        path = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            flattened.update(_flatten_memory(value, path))
        else:
            flattened[path] = value
    return flattened


def _load_memory_map():
    connection = _connect()
    try:
        rows = connection.execute(
            "SELECT path, value_json FROM memory_entries ORDER BY path"
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        connection.close()

    memory = {}
    for row in rows:
        with suppress(Exception):
            memory[row["path"]] = json.loads(row["value_json"])
    return memory


def _read_nested(memory_map, path, default=None):
    return memory_map.get(path, default)


def _normalize_text(value):
    return " ".join(str(value or "").split()).strip()


def _tokenize(text):
    parts = []
    for raw in _normalize_text(text).lower().split():
        cleaned = "".join(char for char in raw if char.isalnum())
        if cleaned:
            parts.append(cleaned)
    return parts


def _load_recent_chats(limit=30):
    state = _load_json(CHAT_STATE_PATH, {})
    sessions = state.get("sessions") or {}
    ordered_ids = state.get("session_order") or list(sessions.keys())
    messages = []
    for session_id in ordered_ids[:6]:
        session = sessions.get(session_id) or {}
        for item in session.get("messages") or []:
            if item.get("role") != "user":
                continue
            content = _normalize_text(item.get("content"))
            if not content:
                continue
            messages.append(
                {
                    "content": content,
                    "created_at": item.get("created_at") or session.get("updated_at") or "",
                }
            )
    messages.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return messages[:limit]


def _load_task_data():
    data = _load_json(TASKS_PATH, {"tasks": [], "reminders": []})
    return {
        "tasks": data.get("tasks") or [],
        "reminders": data.get("reminders") or [],
    }


def _parse_datetime(value):
    text = _normalize_text(value)
    if not text:
        return None
    candidates = [
        text.replace("Z", "+00:00"),
        text,
    ]
    for candidate in candidates:
        with suppress(Exception):
            return datetime.datetime.fromisoformat(candidate)
    formats = [
        "%d %b %I:%M %p",
        "%d %B %I:%M %p",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ]
    for fmt in formats:
        with suppress(Exception):
            parsed = datetime.datetime.strptime(text, fmt)
            return parsed.replace(year=datetime.datetime.now().year)
    return None


def _recent_command_frequency(limit=150):
    connection = _connect()
    try:
        rows = connection.execute(
            """
            SELECT command_text, created_at
            FROM command_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        connection.close()
    return rows


def _infer_habits(user_id):
    del user_id
    memory_map = _load_memory_map()
    commands = _recent_command_frequency()
    chats = _load_recent_chats()

    command_counter = Counter()
    hour_counter = Counter()
    for row in commands:
        command = _normalize_text(row["command_text"]).lower()
        if not command:
            continue
        command_counter[command] += 1
        parsed = _parse_datetime(row["created_at"])
        if parsed:
            hour_counter[parsed.hour] += 1

    chat_counter = Counter()
    for item in chats:
        tokens = _tokenize(item["content"])
        for token in tokens:
            chat_counter[token] += 1

    return {
        "memory": memory_map,
        "top_commands": command_counter.most_common(12),
        "top_chat_terms": chat_counter.most_common(20),
        "top_hours": hour_counter.most_common(6),
        "recent_chats": chats,
    }


def _suggest_from_time(now, habits):
    suggestions = []
    hour = now.hour
    top_hours = {value for value, _count in habits["top_hours"][:3]}
    if hour in top_hours:
        top_commands = [command for command, _count in habits["top_commands"][:5]]
        if any(command.startswith("open vs code") or "vscode" in command or "code" in command for command in top_commands):
            suggestions.append(("habit", "Open VS Code? You usually code at this time.", 0.96))
        if any("weather" in command for command in top_commands):
            suggestions.append(("habit", "Check weather? You usually ask for it around this time.", 0.64))
        if any("dashboard" in command or "daily brief" in command for command in top_commands):
            suggestions.append(("habit", "Open your dashboard? You normally review your status now.", 0.74))

    if 5 <= hour < 11:
        suggestions.append(("time", "Good morning. Want me to show your day plan and pending work?", 0.58))
    elif 11 <= hour < 17:
        suggestions.append(("time", "This is a good work block. Want me to open your current priority?", 0.52))
    elif 17 <= hour < 22:
        suggestions.append(("time", "Evening review time. Want me to summarize unfinished tasks?", 0.55))
    else:
        suggestions.append(("time", "Late hour detected. Want a quick low-effort wrap-up suggestion?", 0.48))
    return suggestions


def _suggest_from_memory(habits):
    memory = habits["memory"]
    suggestions = []

    preferred_editor = _read_nested(memory, "personal.favorites.favorite_code_editor") or _read_nested(
        memory, "personal.favorites.favorite_browser"
    )
    best_time = _read_nested(memory, "personal.routine.best_productive_time")
    current_focus = _read_nested(memory, "professional.learning_path.current_focus", [])
    goal = _read_nested(memory, "professional.goal_timeline.one_year_goal")
    preferred_name = _read_nested(memory, "personal.assistant.preferred_name_for_user") or _read_nested(
        memory, "personal.identity.name"
    )

    if preferred_editor:
        suggestions.append(("memory", f"Open {preferred_editor}? You often use it for focused work.", 0.66))
    if best_time:
        suggestions.append(("memory", f"This matches your productive routine around {best_time}. Want to start a focus block?", 0.67))
    if isinstance(current_focus, list) and current_focus:
        suggestions.append(("memory", f"Continue with {current_focus[0]}? That is one of your saved focus areas.", 0.77))
    elif _normalize_text(current_focus):
        suggestions.append(("memory", f"Continue with {current_focus}? That is one of your saved focus areas.", 0.77))
    if goal:
        name_prefix = f"{preferred_name}, " if preferred_name else ""
        suggestions.append(("memory", f"{name_prefix}one good step now is something that moves you toward: {goal}.", 0.62))
    return suggestions


def _suggest_from_tasks(now):
    data = _load_task_data()
    suggestions = []

    pending_tasks = [task for task in data["tasks"] if not task.get("completed")]
    reminders = data["reminders"]

    if pending_tasks:
        first_task = _normalize_text(pending_tasks[0].get("title")) or "your top task"
        suggestions.append(("tasks", f"You have {len(pending_tasks)} pending tasks. Start with {first_task}?", 0.93))

    due_reminders = []
    for reminder in reminders:
        parsed = (
            _parse_datetime(reminder.get("due_date"))
            or _parse_datetime(reminder.get("when"))
            or _parse_datetime(reminder.get("datetime"))
        )
        if parsed and parsed <= now + datetime.timedelta(hours=2):
            due_reminders.append(reminder)

    if due_reminders:
        title = _normalize_text(due_reminders[0].get("title")) or "a saved reminder"
        suggestions.append(("reminders", f"You have a reminder coming up soon: {title}. Want me to show it?", 0.95))
    elif reminders:
        suggestions.append(("reminders", f"You have {len(reminders)} reminders saved. Want a quick reminder review?", 0.68))

    return suggestions


def _suggest_from_recent_chats(habits):
    suggestions = []
    joined_terms = {term for term, _count in habits["top_chat_terms"]}
    recent_text = " ".join(item["content"].lower() for item in habits["recent_chats"][:8])

    if {"resume", "job", "interview"} & joined_terms:
        suggestions.append(("chat", "Want to continue your resume or job-prep work? You asked about it recently.", 0.82))
    if {"study", "learn", "course"} & joined_terms:
        suggestions.append(("chat", "Want to continue studying? You were discussing learning tasks recently.", 0.78))
    if {"chrome", "browser", "search"} & joined_terms:
        suggestions.append(("chat", "Open Chrome and continue where you left off?", 0.63))
    if "weather" in recent_text:
        suggestions.append(("chat", "You checked weather recently. Want a fresh update?", 0.51))
    return suggestions


def _dedupe_suggestions(items, limit=6):
    ranked = {}
    for kind, text, score in items:
        normalized = _normalize_text(text)
        if not normalized:
            continue
        current = ranked.get(normalized)
        if not current or score > current[2]:
            ranked[normalized] = (kind, normalized, score)
    ordered = sorted(ranked.values(), key=lambda item: (-item[2], item[1]))
    return ordered[:limit]


def _store_suggestions(user_id, suggestions):
    _ensure_tables()
    connection = _connect()
    try:
        connection.execute("DELETE FROM proactive_suggestions WHERE user_id = ?", (user_id,))
        now = datetime.datetime.utcnow().isoformat() + "Z"
        connection.executemany(
            """
            INSERT INTO proactive_suggestions (user_id, suggestion_text, suggestion_kind, score, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(user_id, text, kind, float(score), now) for kind, text, score in suggestions],
        )
        connection.commit()
    finally:
        connection.close()


def get_latest_proactive_suggestions(user_id, limit=6):
    _ensure_tables()
    connection = _connect()
    try:
        rows = connection.execute(
            """
            SELECT suggestion_text, suggestion_kind, score, created_at
            FROM proactive_suggestions
            WHERE user_id = ?
            ORDER BY score DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    finally:
        connection.close()
    return [
        {
            "text": row["suggestion_text"],
            "kind": row["suggestion_kind"],
            "score": float(row["score"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def generate_proactive_suggestions(user_id):
    now = datetime.datetime.now()
    habits = _infer_habits(user_id)
    suggestions = []
    suggestions.extend(_suggest_from_time(now, habits))
    suggestions.extend(_suggest_from_memory(habits))
    suggestions.extend(_suggest_from_tasks(now))
    suggestions.extend(_suggest_from_recent_chats(habits))
    final_suggestions = _dedupe_suggestions(suggestions)
    _store_suggestions(user_id, final_suggestions)
    return [
        {
            "text": text,
            "kind": kind,
            "score": float(score),
        }
        for kind, text, score in final_suggestions
    ]


_last_spoken_suggestion = None

def _background_worker(user_id):
    global _last_spoken_suggestion
    while not _background_stop.wait(SUGGESTION_POLL_SECONDS):
        with suppress(Exception):
            suggestions = generate_proactive_suggestions(user_id)
            if not suggestions:
                continue

            top_suggestion = suggestions[0]
            if top_suggestion["score"] > 0.85 and top_suggestion["text"] != _last_spoken_suggestion:
                # High confidence suggestion, check if focus mode is off
                focus_mode = get_setting("assistant.focus_mode_enabled", False)
                if not focus_mode:
                    _last_spoken_suggestion = top_suggestion["text"]
                    voice_speak_module.speak(top_suggestion["text"])


def start_proactive_suggestion_worker(user_id="default"):
    global _background_thread
    if _background_thread and _background_thread.is_alive():
        return _background_thread
    _background_stop.clear()
    _ensure_tables()
    with suppress(Exception):
        generate_proactive_suggestions(user_id)
    _background_thread = threading.Thread(
        target=_background_worker,
        args=(user_id,),
        daemon=True,
        name="proactive-suggestion-worker",
    )
    _background_thread.start()
    return _background_thread


def stop_proactive_suggestion_worker():
    _background_stop.set()


def register_proactive_suggestion_engine(app, user_id="default"):
    @app.on_event("startup")
    def _startup():
        start_proactive_suggestion_worker(user_id=user_id)

    @app.on_event("shutdown")
    def _shutdown():
        stop_proactive_suggestion_worker()

