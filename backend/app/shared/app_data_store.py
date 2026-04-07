import datetime
import json
import os
import sqlite3
from typing import Any

from brain.database import DB_PATH, initialize_database


def _utc_now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    initialize_database()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _json_dumps(payload: dict[str, Any] | None) -> str:
    return json.dumps(payload or {}, ensure_ascii=False)


def initialize_app_data_store() -> None:
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                device_name TEXT NOT NULL DEFAULT '',
                user_agent TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                revoked_at TEXT,
                FOREIGN KEY (user_id) REFERENCES app_users(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assistant_chat_archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id INTEGER,
                source TEXT NOT NULL DEFAULT 'web',
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                emotion TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES app_users(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assistant_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                category TEXT NOT NULL,
                action TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES app_users(id)
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_app_sessions_token_hash ON app_sessions(token_hash)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_app_sessions_user_id ON app_sessions(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_assistant_chat_archive_session_id ON assistant_chat_archive(session_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_assistant_chat_archive_user_id ON assistant_chat_archive(user_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_assistant_audit_log_created_at ON assistant_audit_log(created_at)"
        )
        connection.commit()
    finally:
        connection.close()


def count_users() -> int:
    initialize_app_data_store()
    connection = _connect()
    try:
        row = connection.execute("SELECT COUNT(*) AS count FROM app_users").fetchone()
        return int(row["count"] or 0)
    finally:
        connection.close()


def get_user_by_username(username: str) -> sqlite3.Row | None:
    initialize_app_data_store()
    connection = _connect()
    try:
        return connection.execute(
            "SELECT * FROM app_users WHERE lower(username) = lower(?)",
            (username,),
        ).fetchone()
    finally:
        connection.close()


def get_user_by_id(user_id: int) -> sqlite3.Row | None:
    initialize_app_data_store()
    connection = _connect()
    try:
        return connection.execute(
            "SELECT * FROM app_users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        connection.close()


def list_users(limit: int = 100) -> list[dict[str, Any]]:
    initialize_app_data_store()
    connection = _connect()
    try:
        rows = connection.execute(
            """
            SELECT id, username, display_name, role, is_active, created_at, updated_at, last_login_at
            FROM app_users
            ORDER BY id ASC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def create_user(
    username: str,
    display_name: str,
    password_hash: str,
    password_salt: str,
    role: str = "user",
) -> dict[str, Any]:
    initialize_app_data_store()
    now = _utc_now()
    connection = _connect()
    try:
        cursor = connection.execute(
            """
            INSERT INTO app_users (username, display_name, password_hash, password_salt, role, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (username, display_name, password_hash, password_salt, role, now, now),
        )
        connection.commit()
        user_id = int(cursor.lastrowid)
    finally:
        connection.close()
    user = get_user_by_id(user_id)
    return dict(user) if user else {}


def update_user_last_login(user_id: int) -> None:
    initialize_app_data_store()
    now = _utc_now()
    connection = _connect()
    try:
        connection.execute(
            """
            UPDATE app_users
            SET last_login_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, now, user_id),
        )
        connection.commit()
    finally:
        connection.close()


def update_user_profile(
    user_id: int,
    *,
    display_name: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> dict[str, Any] | None:
    initialize_app_data_store()
    assignments = []
    params: list[Any] = []

    if display_name is not None:
        assignments.append("display_name = ?")
        params.append(str(display_name or "").strip())
    if role is not None:
        assignments.append("role = ?")
        params.append(str(role or "").strip())
    if is_active is not None:
        assignments.append("is_active = ?")
        params.append(1 if is_active else 0)

    if not assignments:
        row = get_user_by_id(int(user_id))
        return dict(row) if row else None

    assignments.append("updated_at = ?")
    params.append(_utc_now())
    params.append(int(user_id))

    connection = _connect()
    try:
        connection.execute(
            f"""
            UPDATE app_users
            SET {", ".join(assignments)}
            WHERE id = ?
            """,
            tuple(params),
        )
        connection.commit()
    finally:
        connection.close()

    row = get_user_by_id(int(user_id))
    return dict(row) if row else None


def create_session(
    user_id: int,
    token_hash: str,
    expires_at: str,
    *,
    device_name: str = "",
    user_agent: str = "",
) -> dict[str, Any]:
    initialize_app_data_store()
    now = _utc_now()
    connection = _connect()
    try:
        cursor = connection.execute(
            """
            INSERT INTO app_sessions (user_id, token_hash, device_name, user_agent, created_at, expires_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, token_hash, device_name, user_agent, now, expires_at, now),
        )
        connection.commit()
        session_id = int(cursor.lastrowid)
        row = connection.execute(
            "SELECT * FROM app_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    finally:
        connection.close()
    return dict(row) if row else {}


def get_session_by_token_hash(token_hash: str) -> dict[str, Any] | None:
    initialize_app_data_store()
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT * FROM app_sessions WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
    finally:
        connection.close()
    return dict(row) if row else None


def touch_session(token_hash: str) -> None:
    initialize_app_data_store()
    connection = _connect()
    try:
        connection.execute(
            "UPDATE app_sessions SET last_seen_at = ? WHERE token_hash = ?",
            (_utc_now(), token_hash),
        )
        connection.commit()
    finally:
        connection.close()


def revoke_session(token_hash: str) -> None:
    initialize_app_data_store()
    connection = _connect()
    try:
        connection.execute(
            "UPDATE app_sessions SET revoked_at = ? WHERE token_hash = ?",
            (_utc_now(), token_hash),
        )
        connection.commit()
    finally:
        connection.close()


def upsert_chat_session(session_id: str, *, title: str = "New chat", user_id: int | None = None, source: str = "web") -> None:
    initialize_app_data_store()
    now = _utc_now()
    connection = _connect()
    try:
        row = connection.execute(
            """
            SELECT id
            FROM assistant_chat_archive
            WHERE session_id = ?
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()
        if row:
            return
        connection.execute(
            """
            INSERT INTO assistant_chat_archive (session_id, user_id, source, role, content, emotion, metadata_json, created_at)
            VALUES (?, ?, ?, 'system', ?, '', ?, ?)
            """,
            (
                session_id,
                user_id,
                source,
                "",
                _json_dumps({"title": title, "event": "session_created"}),
                now,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def append_chat_message(
    session_id: str,
    role: str,
    content: str,
    *,
    user_id: int | None = None,
    source: str = "web",
    emotion: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    initialize_app_data_store()
    connection = _connect()
    try:
        connection.execute(
            """
            INSERT INTO assistant_chat_archive (session_id, user_id, source, role, content, emotion, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                user_id,
                source,
                role,
                content,
                emotion,
                _json_dumps(metadata),
                _utc_now(),
            ),
        )
        connection.commit()
    finally:
        connection.close()


def list_chat_archive(*, session_id: str | None = None, user_id: int | None = None, limit: int = 120) -> list[dict[str, Any]]:
    initialize_app_data_store()
    conditions = ["role != 'system'"]
    params: list[Any] = []
    if session_id:
        conditions.append("session_id = ?")
        params.append(session_id)
    if user_id is not None:
        conditions.append("user_id = ?")
        params.append(user_id)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    connection = _connect()
    try:
        rows = connection.execute(
            f"""
            SELECT id, session_id, user_id, source, role, content, emotion, metadata_json, created_at
            FROM assistant_chat_archive
            {where_clause}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(1, int(limit))),
        ).fetchall()
    finally:
        connection.close()
    items = []
    for row in rows:
        item = dict(row)
        try:
            item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
        except Exception:
            item["metadata"] = {}
        items.append(item)
    return items


def log_audit_event(
    category: str,
    action: str,
    *,
    user_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    initialize_app_data_store()
    connection = _connect()
    try:
        connection.execute(
            """
            INSERT INTO assistant_audit_log (user_id, category, action, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, category, action, _json_dumps(payload), _utc_now()),
        )
        connection.commit()
    finally:
        connection.close()


def get_audit_log(*, user_id: int | None = None, category: str | None = None, limit: int = 120) -> list[dict[str, Any]]:
    initialize_app_data_store()
    conditions = []
    params: list[Any] = []
    if user_id is not None:
        conditions.append("user_id = ?")
        params.append(user_id)
    if category:
        conditions.append("category = ?")
        params.append(category)
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    connection = _connect()
    try:
        rows = connection.execute(
            f"""
            SELECT id, user_id, category, action, payload_json, created_at
            FROM assistant_audit_log
            {where_clause}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, max(1, int(limit))),
        ).fetchall()
    finally:
        connection.close()

    items = []
    for row in rows:
        item = dict(row)
        try:
            item["payload"] = json.loads(item.pop("payload_json") or "{}")
        except Exception:
            item["payload"] = {}
        items.append(item)
    return items
