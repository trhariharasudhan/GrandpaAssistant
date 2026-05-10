from __future__ import annotations

from contextlib import closing
import datetime as _dt
from pathlib import Path
import re
import sqlite3
from typing import Any

from backend.app.config.grandpa_config import resolve_path


SECRET_RE = re.compile(r"(api[_-]?key|token|password|secret|credential)\s*[:=]", re.IGNORECASE)


def utc_now() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def estimate_tokens(text: str) -> int:
    return max(1, int(len(str(text or "").split()) * 1.3)) if text else 0


class ChatMemory:
    def __init__(self, db_path: str | Path):
        self.db_path = resolve_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self):
        return sqlite3.connect(self.db_path)

    def init_db(self) -> None:
        with closing(self.connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    provider TEXT,
                    model TEXT,
                    token_estimate INTEGER DEFAULT 0
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS app_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id, id)")
            connection.commit()

    def ensure_session(self, session_id: str) -> None:
        now = utc_now()
        with closing(self.connect()) as connection:
            connection.execute(
                """
                INSERT INTO chat_sessions(session_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET updated_at = excluded.updated_at
                """,
                (session_id, "Terminal chat", now, now),
            )
            connection.commit()

    def add_message(self, session_id: str, role: str, message: str, provider: str = "", model: str = "") -> None:
        self.ensure_session(session_id)
        text = compact_text(message)
        with closing(self.connect()) as connection:
            connection.execute(
                """
                INSERT INTO chat_messages(session_id, role, message, timestamp, provider, model, token_estimate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, role, text, utc_now(), provider, model, estimate_tokens(text)),
            )
            connection.commit()

    def recent_messages(self, session_id: str, limit_turns: int = 10) -> list[dict[str, Any]]:
        limit = max(1, int(limit_turns)) * 2
        with closing(self.connect()) as connection:
            rows = connection.execute(
                """
                SELECT role, message, timestamp, provider, model, token_estimate
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [
            {
                "role": role,
                "message": message,
                "timestamp": timestamp,
                "provider": provider or "",
                "model": model or "",
                "token_estimate": int(token_estimate or 0),
            }
            for role, message, timestamp, provider, model, token_estimate in reversed(rows)
        ]

    def clear_session(self, session_id: str) -> None:
        with closing(self.connect()) as connection:
            connection.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            connection.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
            connection.commit()

    def save_fact(self, fact: str) -> tuple[bool, str]:
        cleaned = compact_text(fact)
        if not cleaned:
            return False, "Tell me what to save, da."
        if SECRET_RE.search(cleaned):
            return False, "I did not save that because it looks like a secret."
        with closing(self.connect()) as connection:
            connection.execute("INSERT INTO user_memories(fact, created_at) VALUES (?, ?)", (cleaned, utc_now()))
            connection.commit()
        return True, "Saved da."

    def list_memories(self, limit: int = 20) -> list[dict[str, Any]]:
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT id, fact, created_at FROM user_memories ORDER BY id DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        return [{"id": row[0], "fact": row[1], "created_at": row[2]} for row in reversed(rows)]

    def forget(self, keyword: str) -> int:
        cleaned = compact_text(keyword)
        if not cleaned:
            return 0
        with closing(self.connect()) as connection:
            cursor = connection.execute("DELETE FROM user_memories WHERE fact LIKE ?", (f"%{cleaned}%",))
            connection.commit()
            return int(cursor.rowcount or 0)

    def add_event(self, event_type: str, message: str) -> None:
        with closing(self.connect()) as connection:
            connection.execute(
                "INSERT INTO app_events(event_type, message, timestamp) VALUES (?, ?, ?)",
                (compact_text(event_type), compact_text(message), utc_now()),
            )
            connection.commit()
