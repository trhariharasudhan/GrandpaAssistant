import datetime
import json
import os
import re


DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "notes.json",
)


def _default_data():
    return {"notes": []}


def _load_data():
    if not os.path.exists(DATA_FILE):
        return _default_data()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return _default_data()

    if "notes" not in data:
        data["notes"] = []

    return data


def _save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


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
