import datetime
import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "assistant.db")
LEGACY_MEMORY_PATH = os.path.join(DATA_DIR, "memory.json")


def _connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = _connect()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_entries (
                path TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_text TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def _flatten_dict(data, parent_key="", sep="."):
    items = {}

    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.update(_flatten_dict(value, new_key, sep))
        else:
            items[new_key] = value

    return items


def migrate_legacy_memory():
    initialize_database()

    if not os.path.exists(LEGACY_MEMORY_PATH):
        return

    connection = _connect()
    try:
        cursor = connection.cursor()
        row = cursor.execute("SELECT COUNT(*) AS count FROM memory_entries").fetchone()
        if row["count"] > 0:
            return

        with open(LEGACY_MEMORY_PATH, "r", encoding="utf-8") as file:
            legacy_data = json.load(file)

        flattened = _flatten_dict(legacy_data)
        now = datetime.datetime.now().isoformat()

        for path, value in flattened.items():
            cursor.execute(
                """
                INSERT OR REPLACE INTO memory_entries (path, value_json, updated_at)
                VALUES (?, ?, ?)
                """,
                (path, json.dumps(value), now),
            )

        connection.commit()
    except Exception:
        return
    finally:
        connection.close()


def set_memory_value(path, value):
    initialize_database()
    migrate_legacy_memory()

    connection = _connect()
    try:
        connection.execute(
            """
            INSERT OR REPLACE INTO memory_entries (path, value_json, updated_at)
            VALUES (?, ?, ?)
            """,
            (path, json.dumps(value), datetime.datetime.now().isoformat()),
        )
        connection.commit()
    finally:
        connection.close()


def get_memory_value(path):
    initialize_database()
    migrate_legacy_memory()

    connection = _connect()
    try:
        row = connection.execute(
            "SELECT value_json FROM memory_entries WHERE path = ?", (path,)
        ).fetchone()
    finally:
        connection.close()

    if not row:
        return None

    return json.loads(row["value_json"])


def get_all_memory_entries():
    initialize_database()
    migrate_legacy_memory()

    connection = _connect()
    try:
        rows = connection.execute(
            "SELECT path, value_json FROM memory_entries ORDER BY path"
        ).fetchall()
    finally:
        connection.close()

    return {row["path"]: json.loads(row["value_json"]) for row in rows}


def log_command(command_text, source="unknown"):
    initialize_database()

    connection = _connect()
    try:
        connection.execute(
            """
            INSERT INTO command_history (command_text, source, created_at)
            VALUES (?, ?, ?)
            """,
            (command_text, source, datetime.datetime.now().isoformat()),
        )
        connection.commit()
    finally:
        connection.close()


def get_recent_commands(limit=6):
    initialize_database()

    connection = _connect()
    try:
        rows = connection.execute(
            """
            SELECT command_text
            FROM command_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit * 3,),
        ).fetchall()
    finally:
        connection.close()

    recent = []
    seen = set()
    for row in rows:
        command_text = (row["command_text"] or "").strip()
        if not command_text or command_text in seen:
            continue
        seen.add(command_text)
        recent.append(command_text)
        if len(recent) >= limit:
            break

    return recent


def get_command_frequency(limit=200):
    initialize_database()

    connection = _connect()
    try:
        rows = connection.execute(
            """
            SELECT command_text
            FROM command_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()

    frequency = {}
    for row in rows:
        command_text = (row["command_text"] or "").strip().lower()
        if not command_text:
            continue
        frequency[command_text] = frequency.get(command_text, 0) + 1

    return sorted(frequency.items(), key=lambda item: (-item[1], item[0]))
