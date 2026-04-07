import datetime
import os
import re

from productivity_store import load_notes_payload, save_notes_payload
from security.encryption_utils import read_encrypted_json, remember_protected_target, write_encrypted_json


DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data",
    "notes.json",
)


def _default_data():
    return {"notes": []}


def _load_legacy_data():
    data = read_encrypted_json(DATA_FILE, _default_data())
    if not isinstance(data, dict):
        return _default_data()

    if "notes" not in data:
        data["notes"] = []

    return data


def _load_data():
    try:
        return load_notes_payload(default_factory=_default_data, legacy_loader=_load_legacy_data)
    except Exception:
        return _load_legacy_data()


def _save_legacy_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    write_encrypted_json(DATA_FILE, data, protect=True)
    remember_protected_target(DATA_FILE)


def _save_data(data):
    try:
        save_notes_payload(data, default_factory=_default_data)
    except Exception:
        _save_legacy_data(data)


def _clean_text(value):
    return re.sub(r"\s+", " ", value).strip(" ,.-")


def _parse_index(command, prefix):
    raw = command.replace(prefix, "", 1).strip()
    if not raw.isdigit():
        return None
    return int(raw) - 1


def add_note(command):
    note_text = command
    for prefix in ["take a note", "save this idea", "save note", "add note", "note this"]:
        if command.startswith(prefix):
            note_text = command.replace(prefix, "", 1)
            break

    note_text = _clean_text(note_text)
    if not note_text:
        return "Tell me what note you want to save."

    data = _load_data()
    data["notes"].append(
        {
            "content": note_text,
            "created_at": datetime.datetime.now().isoformat(),
        }
    )
    _save_data(data)
    return f"Note saved: {note_text}"


def list_notes():
    data = _load_data()
    notes = data["notes"]

    if not notes:
        return "You do not have any saved notes right now."

    lines = []
    for index, note in enumerate(notes, start=1):
        lines.append(f"{index}. {note.get('content', 'Untitled note')}")

    return "Your notes are: " + " | ".join(lines[:10])


def search_notes(command):
    query = command
    prefixes = [
        "search notes for",
        "find note about",
        "find note",
        "search notes",
    ]

    for prefix in prefixes:
        if command.startswith(prefix):
            query = command.replace(prefix, "", 1)
            break

    query = _clean_text(query).lower()
    if not query:
        return "Tell me what you want to search in your notes."

    data = _load_data()
    notes = data["notes"]
    matches = []

    for index, note in enumerate(notes, start=1):
        content = note.get("content", "")
        if query in content.lower():
            matches.append(f"{index}. {content}")

    if not matches:
        return f"I could not find any note related to {query}."

    return "Matching notes: " + " | ".join(matches[:5])


def latest_note():
    data = _load_data()
    notes = data["notes"]

    if not notes:
        return "You do not have any saved notes right now."

    note = notes[-1]
    return f"Your latest note is: {note.get('content', 'Untitled note')}"


def summarize_notes():
    data = _load_data()
    notes = data["notes"]

    if not notes:
        return "You do not have any saved notes right now."

    total = len(notes)
    latest_items = [note.get("content", "Untitled note") for note in notes[-3:]]
    return (
        f"You have {total} saved notes. "
        f"Recent notes are: {' | '.join(latest_items)}"
    )


def delete_note(command):
    index = _parse_index(command, "delete note")
    if index is None:
        return "Tell me the note number to delete."

    data = _load_data()
    notes = data["notes"]

    if index < 0 or index >= len(notes):
        return "That note number does not exist."

    removed = notes.pop(index)
    _save_data(data)
    return f"Deleted note: {removed.get('content', 'Untitled note')}"
