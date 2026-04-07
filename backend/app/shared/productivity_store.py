import datetime
import json
import os
import sqlite3
from typing import Any, Callable

from brain.database import DB_PATH, initialize_database


ScopeLoader = Callable[[], dict[str, Any]]


def _utc_now_text() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    initialize_database()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_productivity_store() -> None:
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assistant_state_kv (
                scope TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_user_preferences (
                user_id INTEGER PRIMARY KEY,
                settings_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES app_users(id)
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_assistant_state_kv_updated_at ON assistant_state_kv(updated_at)"
        )
        connection.commit()
    finally:
        connection.close()


def _normalize_payload(payload: Any, default_factory: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    default_payload = default_factory()
    if not isinstance(payload, dict):
        return default_payload
    merged = dict(default_payload)
    merged.update(payload)
    return merged


def _payload_has_content(payload: dict[str, Any], default_factory: Callable[[], dict[str, Any]]) -> bool:
    default_payload = default_factory()
    for key, default_value in default_payload.items():
        current_value = payload.get(key)
        if isinstance(default_value, list):
            if current_value:
                return True
            continue
        if isinstance(default_value, dict):
            if current_value and current_value != default_value:
                return True
            continue
        if current_value not in (None, "", default_value):
            return True
    return False


def _read_scope(scope: str) -> dict[str, Any] | None:
    initialize_productivity_store()
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT payload_json FROM assistant_state_kv WHERE scope = ?",
            (scope,),
        ).fetchone()
    finally:
        connection.close()

    if not row:
        return None

    try:
        payload = json.loads(row["payload_json"] or "{}")
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _write_scope(scope: str, payload: dict[str, Any]) -> None:
    initialize_productivity_store()
    connection = _connect()
    try:
        connection.execute(
            """
            INSERT INTO assistant_state_kv (scope, payload_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(scope) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            (scope, json.dumps(payload, ensure_ascii=False), _utc_now_text()),
        )
        connection.commit()
    finally:
        connection.close()


def load_scope_payload(
    scope: str,
    *,
    default_factory: Callable[[], dict[str, Any]],
    legacy_loader: ScopeLoader | None = None,
) -> dict[str, Any]:
    payload = _read_scope(scope)
    if payload is not None:
        return _normalize_payload(payload, default_factory)

    if legacy_loader is not None:
        try:
            legacy_payload = _normalize_payload(legacy_loader(), default_factory)
        except Exception:
            legacy_payload = default_factory()
        if _payload_has_content(legacy_payload, default_factory):
            _write_scope(scope, legacy_payload)
        return legacy_payload

    payload = default_factory()
    _write_scope(scope, payload)
    return payload


def save_scope_payload(scope: str, payload: dict[str, Any], *, default_factory: Callable[[], dict[str, Any]]) -> None:
    normalized = _normalize_payload(payload, default_factory)
    _write_scope(scope, normalized)


def load_task_payload(*, default_factory: Callable[[], dict[str, Any]], legacy_loader: ScopeLoader | None = None) -> dict[str, Any]:
    return load_scope_payload("productivity.tasks", default_factory=default_factory, legacy_loader=legacy_loader)


def save_task_payload(payload: dict[str, Any], *, default_factory: Callable[[], dict[str, Any]]) -> None:
    save_scope_payload("productivity.tasks", payload, default_factory=default_factory)


def load_notes_payload(*, default_factory: Callable[[], dict[str, Any]], legacy_loader: ScopeLoader | None = None) -> dict[str, Any]:
    return load_scope_payload("productivity.notes", default_factory=default_factory, legacy_loader=legacy_loader)


def save_notes_payload(payload: dict[str, Any], *, default_factory: Callable[[], dict[str, Any]]) -> None:
    save_scope_payload("productivity.notes", payload, default_factory=default_factory)


def load_event_payload(*, default_factory: Callable[[], dict[str, Any]], legacy_loader: ScopeLoader | None = None) -> dict[str, Any]:
    return load_scope_payload("productivity.events", default_factory=default_factory, legacy_loader=legacy_loader)


def save_event_payload(payload: dict[str, Any], *, default_factory: Callable[[], dict[str, Any]]) -> None:
    save_scope_payload("productivity.events", payload, default_factory=default_factory)


def load_chat_state_payload(*, default_factory: Callable[[], dict[str, Any]], legacy_loader: ScopeLoader | None = None) -> dict[str, Any]:
    return load_scope_payload("assistant.chat_state", default_factory=default_factory, legacy_loader=legacy_loader)


def save_chat_state_payload(payload: dict[str, Any], *, default_factory: Callable[[], dict[str, Any]]) -> None:
    save_scope_payload("assistant.chat_state", payload, default_factory=default_factory)


def get_user_preferences(user_id: int) -> dict[str, Any]:
    initialize_productivity_store()
    connection = _connect()
    try:
        row = connection.execute(
            "SELECT settings_json FROM app_user_preferences WHERE user_id = ?",
            (int(user_id),),
        ).fetchone()
    finally:
        connection.close()

    if not row:
        return {}

    try:
        payload = json.loads(row["settings_json"] or "{}")
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def update_user_preferences(user_id: int, preferences: dict[str, Any]) -> dict[str, Any]:
    normalized = preferences if isinstance(preferences, dict) else {}
    initialize_productivity_store()
    connection = _connect()
    try:
        connection.execute(
            """
            INSERT INTO app_user_preferences (user_id, settings_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                settings_json = excluded.settings_json,
                updated_at = excluded.updated_at
            """,
            (int(user_id), json.dumps(normalized, ensure_ascii=False), _utc_now_text()),
        )
        connection.commit()
    finally:
        connection.close()
    return get_user_preferences(int(user_id))
