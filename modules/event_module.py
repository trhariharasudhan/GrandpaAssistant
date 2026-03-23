import datetime
import json
import os
import re

from modules.calendar_module import extract_specific_date, get_relative_base


DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "events.json",
)


def _default_data():
    return {"events": []}


def _load_data():
    if not os.path.exists(DATA_FILE):
        return _default_data()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return _default_data()

    if "events" not in data:
        data["events"] = []

    return data


def _save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def _clean_text(value):
    return re.sub(r"\s+", " ", value).strip(" ,.-")


def _extract_event_date(command):
    date_obj = get_relative_base(command) or extract_specific_date(command)
    if not date_obj:
        return None

    if isinstance(date_obj, datetime.datetime):
        date_obj = date_obj.date()

    return date_obj.isoformat()


def _remove_date_phrases(text):
    patterns = [
        r"\b(today|tomorrow|yesterday|next week|last week|next month|last month|next year|last year)\b",
        r"\bon\s+\d{1,2}\s+[a-zA-Z]+\s+\d{4}\b",
        r"\b\d{1,2}\s+[a-zA-Z]+\s+\d{4}\b",
        r"\bon\s+\d{1,2}\s+\d{1,2}\s+\d{4}\b",
        r"\b\d{1,2}\s+\d{1,2}\s+\d{4}\b",
    ]

    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    return _clean_text(cleaned)


def _format_date(date_str):
    if not date_str:
        return "No date"

    try:
        return datetime.date.fromisoformat(date_str).strftime("%d %B %Y")
    except ValueError:
        return date_str


def add_event(command):
    date_value = _extract_event_date(command)
    title = command

    prefixes = [
        "add event",
        "create event",
        "schedule event",
    ]

    for prefix in prefixes:
        if command.startswith(prefix):
            title = command.replace(prefix, "", 1)
            break

    title = _remove_date_phrases(title)
    if not title:
        return "Tell me what event you want to add."

    data = _load_data()
    data["events"].append(
        {
            "title": title,
            "date": date_value,
            "created_at": datetime.datetime.now().isoformat(),
        }
    )
    _save_data(data)

    if date_value:
        return f"Event added for {_format_date(date_value)}: {title}"
    return f"Event added: {title}"


def list_events():
    data = _load_data()
    events = data["events"]

    if not events:
        return "You do not have any saved events right now."

    events = sorted(events, key=lambda item: item.get("date") or "9999-12-31")
    lines = []
    for index, event in enumerate(events[:10], start=1):
        lines.append(f"{index}. {event.get('title', 'Untitled event')} - {_format_date(event.get('date'))}")

    return "Your events are: " + " | ".join(lines)


def today_events():
    today = datetime.date.today().isoformat()
    data = _load_data()
    events = [event.get("title", "Untitled event") for event in data["events"] if event.get("date") == today]

    if not events:
        return "You do not have any events for today."

    return "Today's events are: " + " | ".join(events)


def upcoming_events():
    today = datetime.date.today()
    data = _load_data()
    upcoming = []

    for event in data["events"]:
        try:
            event_date = datetime.date.fromisoformat(event.get("date"))
        except Exception:
            continue
        if event_date >= today:
            upcoming.append((event_date, event.get("title", "Untitled event")))

    if not upcoming:
        return "You do not have any upcoming events right now."

    upcoming.sort(key=lambda item: item[0])
    lines = [f"{title} on {date.strftime('%d %B %Y')}" for date, title in upcoming[:5]]
    return "Upcoming events: " + " | ".join(lines)


def delete_event(command):
    raw = command.replace("delete event", "", 1).strip()
    if not raw.isdigit():
        return "Tell me the event number to delete."

    index = int(raw) - 1
    data = _load_data()
    events = sorted(data["events"], key=lambda item: item.get("date") or "9999-12-31")

    if index < 0 or index >= len(events):
        return "That event number does not exist."

    removed = events.pop(index)
    data["events"] = events
    _save_data(data)
    return f"Deleted event: {removed.get('title', 'Untitled event')}"
