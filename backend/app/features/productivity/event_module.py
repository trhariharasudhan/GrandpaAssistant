import datetime
import json
import os
import re

from productivity_store import load_event_payload, save_event_payload
from productivity.calendar_module import extract_specific_date, get_relative_base
from utils.paths import backend_data_path


DATA_FILE = backend_data_path("events.json")


def _default_data():
    return {"events": []}


def _load_legacy_data():
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


def _load_data():
    try:
        return load_event_payload(default_factory=_default_data, legacy_loader=_load_legacy_data)
    except Exception:
        return _load_legacy_data()


def _save_legacy_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def _save_data(data):
    try:
        save_event_payload(data, default_factory=_default_data)
    except Exception:
        _save_legacy_data(data)


def get_event_data():
    return _load_data()


def _clean_text(value):
    return re.sub(r"\s+", " ", value).strip(" ,.-")


def _extract_event_date(command):
    date_obj = get_relative_base(command) or extract_specific_date(command)
    if not date_obj:
        return None

    if isinstance(date_obj, datetime.datetime):
        date_obj = date_obj.date()

    return date_obj.isoformat()


def _extract_relative_event_datetime(command):
    match = re.search(
        r"\bin\s+(\d+)\s*(minute|minutes|hour|hours|day|days|week|weeks)\b",
        command,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).lower()
    now = datetime.datetime.now()

    if "minute" in unit:
        return now + datetime.timedelta(minutes=amount)
    if "hour" in unit:
        return now + datetime.timedelta(hours=amount)
    if "week" in unit:
        return now + datetime.timedelta(days=amount * 7)
    return now + datetime.timedelta(days=amount)


def _extract_event_time(command):
    match = re.search(
        r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
        command,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = (match.group(3) or "").lower()

    if meridiem:
        if hour == 12:
            hour = 0
        if meridiem == "pm":
            hour += 12

    if hour > 23 or minute > 59:
        return None

    return f"{hour:02d}:{minute:02d}"


def _extract_event_datetime(command):
    relative_value = _extract_relative_event_datetime(command)
    if relative_value is not None:
        return relative_value.replace(second=0, microsecond=0)

    date_value = get_relative_base(command) or extract_specific_date(command)
    time_value = _extract_event_time(command)

    if isinstance(date_value, datetime.datetime):
        date_value = date_value.date()

    if date_value is None and time_value is None:
        return None

    if time_value is not None:
        hour, minute = map(int, time_value.split(":"))
        time_obj = datetime.time(hour=hour, minute=minute)
    else:
        time_obj = datetime.time(hour=9, minute=0)

    if date_value is None:
        date_value = datetime.date.today()

    return datetime.datetime.combine(date_value, time_obj)


def _remove_date_phrases(text):
    patterns = [
        r"\b(today|tomorrow|yesterday|next week|last week|next month|last month|next year|last year)\b",
        r"\bin\s+\d+\s*(minute|minutes|hour|hours|day|days|week|weeks)\b",
        r"\bon\s+\d{1,2}\s+[a-zA-Z]+\s+\d{4}\b",
        r"\b\d{1,2}\s+[a-zA-Z]+\s+\d{4}\b",
        r"\bon\s+\d{1,2}\s+\d{1,2}\s+\d{4}\b",
        r"\b\d{1,2}\s+\d{1,2}\s+\d{4}\b",
    ]

    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(
        r"\bat\s+\d{1,2}(?::\d{2})?\s*(am|pm)?\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )

    return _clean_text(cleaned)


def _extract_recurrence(command):
    normalized = (command or "").lower()
    if "every day" in normalized or "daily" in normalized:
        return "daily"

    weekday_match = re.search(
        r"\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        normalized,
    )
    if weekday_match:
        return f"weekly:{weekday_match.group(1)}"

    if "every week" in normalized or "weekly" in normalized:
        return "weekly"

    if "every month" in normalized or "monthly" in normalized:
        return "monthly"

    return None


def _strip_recurrence_phrases(text):
    cleaned = re.sub(
        r"\bevery\s+(day|week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\b(daily|weekly|monthly)\b", " ", cleaned, flags=re.IGNORECASE)
    return _clean_text(cleaned)


def _format_recurrence(recurrence):
    if not recurrence:
        return ""
    if recurrence == "daily":
        return " (recurs daily)"
    if recurrence == "weekly":
        return " (recurs weekly)"
    if recurrence == "monthly":
        return " (recurs monthly)"
    if recurrence.startswith("weekly:"):
        return f" (recurs every {recurrence.split(':', 1)[1]})"
    return f" ({recurrence})"


def _format_date(date_str):
    if not date_str:
        return "No date"

    try:
        return datetime.date.fromisoformat(date_str).strftime("%d %B %Y")
    except ValueError:
        return date_str


def _format_time(time_str):
    if not time_str:
        return "No time"

    try:
        return datetime.datetime.strptime(time_str, "%H:%M").strftime("%I:%M %p")
    except ValueError:
        return time_str


def _sort_key(event):
    date_value = event.get("date") or "9999-12-31"
    time_value = event.get("time") or "23:59"
    return (date_value, time_value)


def _format_event_line(index, event):
    title = event.get("title", "Untitled event")
    date_text = _format_date(event.get("date"))
    time_text = event.get("time")
    if time_text:
        return f"{index}. {title} - {date_text} at {_format_time(time_text)}{_format_recurrence(event.get('recurrence'))}"
    return f"{index}. {title} - {date_text}{_format_recurrence(event.get('recurrence'))}"


def _find_conflicting_event(events, date_value, time_value):
    if not date_value or not time_value:
        return None

    try:
        new_dt = datetime.datetime.combine(
            datetime.date.fromisoformat(date_value),
            datetime.datetime.strptime(time_value, "%H:%M").time(),
        )
    except Exception:
        return None

    for event in events:
        if event.get("date") != date_value or not event.get("time"):
            continue
        try:
            existing_dt = datetime.datetime.combine(
                datetime.date.fromisoformat(event.get("date")),
                datetime.datetime.strptime(event.get("time"), "%H:%M").time(),
            )
        except Exception:
            continue
        if abs((existing_dt - new_dt).total_seconds()) <= 3600:
            return event
    return None


def add_event(command):
    recurrence = _extract_recurrence(command)
    event_datetime = _extract_event_datetime(command)
    date_value = event_datetime.date().isoformat() if event_datetime else _extract_event_date(command)
    time_value = event_datetime.strftime("%H:%M") if event_datetime else _extract_event_time(command)
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

    title = _strip_recurrence_phrases(_remove_date_phrases(title))
    if not title:
        return "Tell me what event you want to add."

    data = _load_data()
    conflict = _find_conflicting_event(data["events"], date_value, time_value)
    data["events"].append(
        {
            "title": title,
            "date": date_value,
            "time": time_value,
            "recurrence": recurrence,
            "created_at": datetime.datetime.now().isoformat(),
        }
    )
    _save_data(data)

    conflict_note = ""
    if conflict:
        conflict_time = f" at {_format_time(conflict.get('time'))}" if conflict.get("time") else ""
        conflict_note = f" Possible conflict with {conflict.get('title', 'another event')} on {_format_date(conflict.get('date'))}{conflict_time}."

    if date_value and time_value:
        prefix = "Recurring event added" if recurrence else "Event added"
        return f"{prefix}{_format_recurrence(recurrence)} for {_format_date(date_value)} at {_format_time(time_value)}: {title}.{conflict_note}".strip()
    if date_value:
        prefix = "Recurring event added" if recurrence else "Event added"
        return f"{prefix}{_format_recurrence(recurrence)} for {_format_date(date_value)}: {title}.{conflict_note}".strip()
    return f"Event added: {title}.{conflict_note}".strip()


def list_events():
    data = _load_data()
    events = data["events"]

    if not events:
        return "You do not have any saved events right now."

    events = sorted(events, key=_sort_key)
    lines = []
    for index, event in enumerate(events[:10], start=1):
        lines.append(_format_event_line(index, event))

    return "Your events are: " + " | ".join(lines)


def today_events():
    today = datetime.date.today().isoformat()
    data = _load_data()
    events = [event for event in data["events"] if event.get("date") == today]

    if not events:
        return "You do not have any events for today."

    events = sorted(events, key=_sort_key)
    lines = []
    for event in events[:10]:
        title = event.get("title", "Untitled event")
        if event.get("time"):
            lines.append(f"{title} at {_format_time(event.get('time'))}{_format_recurrence(event.get('recurrence'))}")
        else:
            lines.append(f"{title}{_format_recurrence(event.get('recurrence'))}")

    return "Today's events are: " + " | ".join(lines)


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
            upcoming.append(event)

    if not upcoming:
        return "You do not have any upcoming events right now."

    upcoming.sort(key=_sort_key)
    lines = []
    for event in upcoming[:5]:
        date = datetime.date.fromisoformat(event.get("date"))
        time_value = event.get("time") or "23:59"
        title = event.get("title", "Untitled event")
        if time_value and time_value != "23:59":
            lines.append(f"{title} on {date.strftime('%d %B %Y')} at {_format_time(time_value)}{_format_recurrence(event.get('recurrence'))}")
        else:
            lines.append(f"{title} on {date.strftime('%d %B %Y')}{_format_recurrence(event.get('recurrence'))}")
    return "Upcoming events: " + " | ".join(lines)


def _get_latest_created_event(events):
    if not events:
        return None

    return max(events, key=lambda event: event.get("created_at", ""))


def latest_event():
    data = _load_data()
    event = _get_latest_created_event(data["events"])

    if not event:
        return "You do not have any saved events right now."

    title = event.get("title", "Untitled event")
    date_text = _format_date(event.get("date"))
    time_value = event.get("time")
    if time_value:
        return f"Your latest event is {title} on {date_text} at {_format_time(time_value)}{_format_recurrence(event.get('recurrence'))}."
    return f"Your latest event is {title} on {date_text}{_format_recurrence(event.get('recurrence'))}."


def delete_event(command):
    raw = command.replace("delete event", "", 1).strip()
    if not raw.isdigit():
        return "Tell me the event number to delete."

    index = int(raw) - 1
    data = _load_data()
    events = sorted(data["events"], key=_sort_key)

    if index < 0 or index >= len(events):
        return "That event number does not exist."

    removed = events.pop(index)
    data["events"] = events
    _save_data(data)
    return f"Deleted event: {removed.get('title', 'Untitled event')}"


def delete_latest_event():
    data = _load_data()
    event = _get_latest_created_event(data["events"])

    if not event:
        return "You do not have any saved events to delete."

    data["events"].remove(event)
    _save_data(data)
    return f"Deleted latest event: {event.get('title', 'Untitled event')}"


def _match_event_by_title(events, title_text):
    query = _clean_text(title_text).lower()
    if not query:
        return None

    candidates = []
    for event in events:
        title = _clean_text(event.get("title", "")).lower()
        if not title:
            continue

        score = 0
        if title == query:
            score = 100
        elif title.startswith(query):
            score = 90
        elif query in title:
            score = 80
        else:
            query_words = [word for word in query.split() if word]
            overlap = sum(1 for word in query_words if word in title)
            if overlap:
                score = overlap * 10

        if score:
            candidates.append((score, event))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1].get("created_at", "")), reverse=True)
    return candidates[0][1]


def delete_event_by_title(command):
    match = re.match(
        r"^(?:delete|remove)\s+event\s+(?:about|titled)\s+(.+)$",
        command,
    )
    if not match:
        return "Tell me which event title you want to delete."

    title_text = _clean_text(match.group(1))
    if not title_text:
        return "Tell me which event title you want to delete."

    data = _load_data()
    event = _match_event_by_title(data["events"], title_text)
    if not event:
        return f"I could not find an event matching '{title_text}'."

    data["events"].remove(event)
    _save_data(data)
    return f"Deleted event: {event.get('title', 'Untitled event')}"


def rename_event(command):
    match = re.match(
        r"^(?:rename|update|change)\s+event\s+(?:about|titled)\s+(.+?)\s+to\s+(.+)$",
        command,
    )
    if not match:
        return "Tell me which event you want to rename and the new title."

    current_title = _clean_text(match.group(1))
    new_title = _clean_text(match.group(2))
    if not current_title or not new_title:
        return "I need both the current event title and the new title."

    data = _load_data()
    event = _match_event_by_title(data["events"], current_title)
    if not event:
        return f"I could not find an event matching '{current_title}'."

    event["title"] = new_title
    _save_data(data)
    return f"Event renamed to: {new_title}"


def reschedule_event(command):
    match = re.match(
        r"^(?:reschedule|update|change)\s+event\s+(?:about|titled)\s+(.+?)\s+to\s+(.+)$",
        command,
    )
    if not match:
        return "Tell me which event you want to reschedule and the new time."

    title_text = _clean_text(match.group(1))
    schedule_text = _clean_text(match.group(2))
    if not title_text or not schedule_text:
        return "I need the event title and the new schedule."

    data = _load_data()
    event = _match_event_by_title(data["events"], title_text)
    if not event:
        return f"I could not find an event matching '{title_text}'."

    event_datetime = _extract_event_datetime(schedule_text)
    date_value = event_datetime.date().isoformat() if event_datetime else _extract_event_date(schedule_text)
    time_value = event_datetime.strftime("%H:%M") if event_datetime else _extract_event_time(schedule_text)

    if date_value is None and time_value is None:
        return "Tell me the new date or time for that event."

    event["date"] = date_value
    event["time"] = time_value
    _save_data(data)

    if date_value and time_value:
        return f"Event rescheduled to {_format_date(date_value)} at {_format_time(time_value)}."
    return f"Event rescheduled to {_format_date(date_value)}."


def clear_all_events():
    data = _load_data()
    events = data["events"]

    if not events:
        return "You do not have any events to clear."

    count = len(events)
    data["events"] = []
    _save_data(data)
    return f"Cleared all events: {count} event(s)."


def clear_today_events():
    today = datetime.date.today().isoformat()
    data = _load_data()
    events = data["events"]
    today_events_list = [event for event in events if event.get("date") == today]

    if not today_events_list:
        return "You do not have any events for today to clear."

    data["events"] = [event for event in events if event.get("date") != today]
    _save_data(data)
    return f"Cleared today's events: {len(today_events_list)} event(s)."


def clear_past_events():
    today = datetime.date.today()
    data = _load_data()
    events = data["events"]
    past_events = []

    for event in events:
        try:
            event_date = datetime.date.fromisoformat(event.get("date"))
        except Exception:
            continue

        if event_date < today:
            past_events.append(event)

    if not past_events:
        return "You do not have any past events to clear."

    data["events"] = [event for event in events if event not in past_events]
    _save_data(data)
    return f"Cleared past events: {len(past_events)} event(s)."


def get_due_event_titles(days_ahead=1):
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=days_ahead)
    due_events = {"today": [], "upcoming": []}

    for event in _load_data().get("events", []):
        try:
            event_date = datetime.date.fromisoformat(event.get("date"))
        except Exception:
            continue

        title = event.get("title", "Untitled event")
        if event_date == today:
            if event.get("time"):
                due_events["today"].append(f"{title} at {_format_time(event.get('time'))}")
            else:
                due_events["today"].append(title)
        elif today < event_date <= end_date:
            if event.get("time"):
                due_events["upcoming"].append(
                    f"{title} on {event_date.strftime('%d %B %Y')} at {_format_time(event.get('time'))}"
                )
            else:
                due_events["upcoming"].append(f"{title} on {event_date.strftime('%d %B %Y')}")

    return due_events
