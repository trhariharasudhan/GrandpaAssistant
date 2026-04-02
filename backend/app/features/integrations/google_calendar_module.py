import datetime
import json
import os
import re

from productivity.event_module import (
    _extract_event_date,
    _extract_event_datetime,
    _extract_event_time,
    _remove_date_phrases,
    _strip_recurrence_phrases,
)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(DATA_DIR, "google_calendar_token.json")
CACHE_PATH = os.path.join(DATA_DIR, "google_calendar_cache.json")
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _get_calendar_service():
    if not os.path.exists(CREDENTIALS_PATH):
        return None, (
            "I could not find credentials.json in the project folder. "
            "Keep it in the project root and try again."
        )

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except Exception:
        return None, (
            "Google Calendar libraries are not installed yet. "
            "Install the project requirements first."
        )

    _ensure_data_dir()
    creds = None

    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    return service, None


def _format_event(event):
    start = event.get("start", {})
    raw_dt = start.get("dateTime") or start.get("date")
    summary = event.get("summary") or "Untitled event"
    if not raw_dt:
        return summary

    try:
        if "T" in raw_dt:
            dt = datetime.datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
            return f"{summary} at {dt.strftime('%d %B %Y %I:%M %p')}"
        date_value = datetime.date.fromisoformat(raw_dt)
        return f"{summary} on {date_value.strftime('%d %B %Y')}"
    except Exception:
        return summary


def _save_cache(items):
    _ensure_data_dir()
    with open(CACHE_PATH, "w", encoding="utf-8") as file:
        json.dump(items, file, indent=4, ensure_ascii=False)


def _load_cache():
    if not os.path.exists(CACHE_PATH):
        return []
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _today_cached_events():
    today = datetime.date.today()
    lines = []
    for event in _load_cache():
        start = event.get("start", {})
        raw_dt = start.get("dateTime") or start.get("date")
        summary = event.get("summary") or "Untitled event"
        if not raw_dt:
            continue
        try:
            if "T" in raw_dt:
                dt = datetime.datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
                local_date = dt.date()
                if local_date != today:
                    continue
                lines.append(f"{summary} at {dt.strftime('%I:%M %p')}")
            else:
                date_value = datetime.date.fromisoformat(raw_dt)
                if date_value != today:
                    continue
                lines.append(summary)
        except Exception:
            continue
    return lines


def google_calendar_status():
    if not os.path.exists(CREDENTIALS_PATH):
        return "Google Calendar is not ready yet because credentials.json is missing."
    if os.path.exists(TOKEN_PATH):
        return "Google Calendar credentials are ready and an authorization token is saved."
    return "Google Calendar credentials are ready, but first-time authorization is still needed."


def sync_google_calendar(limit=10):
    service, error = _get_calendar_service()
    if error:
        return False, error

    now_utc = datetime.datetime.utcnow().isoformat() + "Z"
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now_utc,
            maxResults=limit,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    items = events_result.get("items", [])
    _save_cache(items)
    return True, f"Google Calendar synced. I cached {len(items)} upcoming events."


def today_google_calendar_summary_lines(limit=3):
    return _today_cached_events()[:limit]


def _upcoming_events(service, limit=20):
    now_utc = datetime.datetime.utcnow().isoformat() + "Z"
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now_utc,
            maxResults=limit,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events_result.get("items", [])


def _find_event_by_title(service, title_query):
    normalized_query = " ".join((title_query or "").lower().split())
    if not normalized_query:
        return None

    for event in _upcoming_events(service, limit=25):
        summary = " ".join((event.get("summary") or "").lower().split())
        if normalized_query in summary:
            return event
    return None


def _event_start_datetime(event):
    start = event.get("start", {})
    raw_dt = start.get("dateTime")
    if not raw_dt:
        return None
    try:
        return datetime.datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
    except Exception:
        return None


def _conflict_summary(service, target_start, skip_event_id=None):
    if not target_start:
        return None

    for event in _upcoming_events(service, limit=20):
        if skip_event_id and event.get("id") == skip_event_id:
            continue
        event_start = _event_start_datetime(event)
        if not event_start:
            continue
        delta_minutes = abs((event_start - target_start).total_seconds()) / 60
        if delta_minutes < 60:
            summary = event.get("summary") or "Untitled event"
            return f"Possible conflict with {summary}."
    return None


def list_google_calendar_event_titles(limit=8):
    service, error = _get_calendar_service()
    if error:
        return error

    items = _upcoming_events(service, limit=limit)
    if not items:
        return "You do not have any upcoming Google Calendar events right now."
    titles = [item.get("summary") or "Untitled event" for item in items]
    return "Upcoming Google Calendar titles: " + " | ".join(titles)


def upcoming_google_calendar_title_lines(limit=3):
    service, error = _get_calendar_service()
    if error:
        return []
    items = _upcoming_events(service, limit=limit)
    return [(item.get("summary") or "Untitled event") for item in items[:limit]]


def today_google_calendar_events():
    service, error = _get_calendar_service()
    if error:
        return error

    now = datetime.datetime.now()
    start = datetime.datetime.combine(now.date(), datetime.time.min).isoformat()
    end = datetime.datetime.combine(now.date(), datetime.time.max).isoformat()

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    items = events_result.get("items", [])
    if not items:
        return "You do not have any Google Calendar events for today."
    return "Today's Google Calendar events: " + " | ".join(_format_event(item) for item in items[:5])


def upcoming_google_calendar_events(limit=5):
    service, error = _get_calendar_service()
    if error:
        return error

    items = _upcoming_events(service, limit=limit)
    if not items:
        return "You do not have any upcoming Google Calendar events right now."
    return "Upcoming Google Calendar events: " + " | ".join(_format_event(item) for item in items[:limit])


def delete_latest_google_calendar_event():
    service, error = _get_calendar_service()
    if error:
        return error

    items = _upcoming_events(service, limit=1)
    if not items:
        return "There is no upcoming Google Calendar event to delete."

    event = items[0]
    event_id = event.get("id")
    title = event.get("summary") or "Untitled event"
    if not event_id:
        return "I could not identify the latest Google Calendar event."

    service.events().delete(calendarId="primary", eventId=event_id).execute()
    return f"Deleted latest Google Calendar event: {title}."


def rename_latest_google_calendar_event(command):
    service, error = _get_calendar_service()
    if error:
        return error

    match = re.match(
        r"^(?:rename|update)\s+latest google calendar event(?:\s+to)?\s+(.+)$",
        " ".join((command or "").strip().split()),
    )
    if not match:
        return "Use this format: rename latest Google Calendar event to team sync."

    new_title = match.group(1).strip(" .")
    if not new_title:
        return "Tell me the new Google Calendar event title."

    items = _upcoming_events(service, limit=1)
    if not items:
        return "There is no upcoming Google Calendar event to rename."

    event = items[0]
    event["summary"] = new_title
    service.events().update(calendarId="primary", eventId=event["id"], body=event).execute()
    return f"Renamed latest Google Calendar event to {new_title}."


def delete_google_calendar_event_by_title(command):
    service, error = _get_calendar_service()
    if error:
        return error

    match = re.match(
        r"^(?:delete|remove)\s+google calendar event(?:\s+(?:about|titled))?\s+(.+)$",
        " ".join((command or "").strip().split()),
    )
    if not match:
        return "Use this format: delete google calendar event team sync."

    title_query = match.group(1).strip(" .")
    event = _find_event_by_title(service, title_query)
    if not event:
        return f"I could not find an upcoming Google Calendar event matching {title_query}."

    title = event.get("summary") or "Untitled event"
    service.events().delete(calendarId="primary", eventId=event["id"]).execute()
    return f"Deleted Google Calendar event: {title}."


def rename_google_calendar_event_by_title(command):
    service, error = _get_calendar_service()
    if error:
        return error

    match = re.match(
        r"^(?:rename|update)\s+google calendar event\s+(.+?)\s+to\s+(.+)$",
        " ".join((command or "").strip().split()),
    )
    if not match:
        return "Use this format: rename google calendar event team sync to client sync."

    title_query = match.group(1).strip(" .")
    new_title = match.group(2).strip(" .")
    event = _find_event_by_title(service, title_query)
    if not event:
        return f"I could not find an upcoming Google Calendar event matching {title_query}."

    event["summary"] = new_title
    service.events().update(calendarId="primary", eventId=event["id"], body=event).execute()
    return f"Renamed Google Calendar event {title_query} to {new_title}."


def reschedule_latest_google_calendar_event(command):
    service, error = _get_calendar_service()
    if error:
        return error

    normalized = " ".join((command or "").strip().split())
    match = re.match(
        r"^(?:reschedule|move)\s+latest google calendar event(?:\s+to)?\s+(.+)$",
        normalized,
    )
    if not match:
        return "Use this format: reschedule latest Google Calendar event to tomorrow at 6 pm."

    target_phrase = match.group(1).strip()
    event_datetime = _extract_event_datetime(target_phrase)
    date_value = event_datetime.date().isoformat() if event_datetime else _extract_event_date(target_phrase)
    time_value = event_datetime.strftime("%H:%M") if event_datetime else _extract_event_time(target_phrase)

    if not date_value:
        return "Tell me the new date for the latest Google Calendar event."

    items = _upcoming_events(service, limit=1)
    if not items:
        return "There is no upcoming Google Calendar event to reschedule."

    event = items[0]
    if time_value:
        start_dt = datetime.datetime.combine(
            datetime.date.fromisoformat(date_value),
            datetime.datetime.strptime(time_value, "%H:%M").time(),
        )
        end_dt = start_dt + datetime.timedelta(hours=1)
        warning = _conflict_summary(service, start_dt, skip_event_id=event.get("id"))
        event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Calcutta"}
        event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Calcutta"}
        service.events().update(calendarId="primary", eventId=event["id"], body=event).execute()
        reply = f"Rescheduled latest Google Calendar event to {start_dt.strftime('%d %B %Y at %I:%M %p')}."
        if warning:
            reply += f" {warning}"
        return reply

    event["start"] = {"date": date_value}
    event["end"] = {"date": date_value}
    service.events().update(calendarId="primary", eventId=event["id"], body=event).execute()
    return f"Rescheduled latest Google Calendar event to {datetime.date.fromisoformat(date_value).strftime('%d %B %Y')}."


def reschedule_google_calendar_event_by_title(command):
    service, error = _get_calendar_service()
    if error:
        return error

    normalized = " ".join((command or "").strip().split())
    match = re.match(
        r"^(?:reschedule|move)\s+google calendar event\s+(.+?)\s+to\s+(.+)$",
        normalized,
    )
    if not match:
        return "Use this format: reschedule google calendar event team sync to tomorrow at 6 pm."

    title_query = match.group(1).strip(" .")
    target_phrase = match.group(2).strip()
    event = _find_event_by_title(service, title_query)
    if not event:
        return f"I could not find an upcoming Google Calendar event matching {title_query}."

    event_datetime = _extract_event_datetime(target_phrase)
    date_value = event_datetime.date().isoformat() if event_datetime else _extract_event_date(target_phrase)
    time_value = event_datetime.strftime("%H:%M") if event_datetime else _extract_event_time(target_phrase)
    if not date_value:
        return "Tell me the new date for that Google Calendar event."

    if time_value:
        start_dt = datetime.datetime.combine(
            datetime.date.fromisoformat(date_value),
            datetime.datetime.strptime(time_value, "%H:%M").time(),
        )
        end_dt = start_dt + datetime.timedelta(hours=1)
        warning = _conflict_summary(service, start_dt, skip_event_id=event.get("id"))
        event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Calcutta"}
        event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Calcutta"}
        service.events().update(calendarId="primary", eventId=event["id"], body=event).execute()
        reply = f"Rescheduled Google Calendar event {title_query} to {start_dt.strftime('%d %B %Y at %I:%M %p')}."
        if warning:
            reply += f" {warning}"
        return reply

    event["start"] = {"date": date_value}
    event["end"] = {"date": date_value}
    service.events().update(calendarId="primary", eventId=event["id"], body=event).execute()
    return f"Rescheduled Google Calendar event {title_query} to {datetime.date.fromisoformat(date_value).strftime('%d %B %Y')}."


def add_google_calendar_event(command):
    service, error = _get_calendar_service()
    if error:
        return error

    normalized = " ".join((command or "").strip().split())
    title = normalized
    for prefix in ["add google calendar event", "create google calendar event", "schedule google calendar event"]:
        if normalized.startswith(prefix):
            title = normalized.replace(prefix, "", 1)
            break

    title = _strip_recurrence_phrases(_remove_date_phrases(title)).strip(" ,.-")
    if not title:
        return "Tell me what Google Calendar event you want to add."

    event_datetime = _extract_event_datetime(normalized)
    date_value = event_datetime.date().isoformat() if event_datetime else _extract_event_date(normalized)
    time_value = event_datetime.strftime("%H:%M") if event_datetime else _extract_event_time(normalized)

    if date_value:
        if time_value:
            start_dt = datetime.datetime.combine(
                datetime.date.fromisoformat(date_value),
                datetime.datetime.strptime(time_value, "%H:%M").time(),
            )
            end_dt = start_dt + datetime.timedelta(hours=1)
            warning = _conflict_summary(service, start_dt)
            event_body = {
                "summary": title,
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Calcutta"},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Calcutta"},
            }
            service.events().insert(calendarId="primary", body=event_body).execute()
            reply = f"Google Calendar event added for {start_dt.strftime('%d %B %Y at %I:%M %p')}: {title}."
            if warning:
                reply += f" {warning}"
            return reply

        event_body = {
            "summary": title,
            "start": {"date": date_value},
            "end": {"date": date_value},
        }
        service.events().insert(calendarId="primary", body=event_body).execute()
        return f"Google Calendar event added for {datetime.date.fromisoformat(date_value).strftime('%d %B %Y')}: {title}."

    now = datetime.datetime.now().replace(second=0, microsecond=0)
    start_dt = now + datetime.timedelta(hours=1)
    end_dt = start_dt + datetime.timedelta(hours=1)
    event_body = {
        "summary": title,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Calcutta"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Calcutta"},
    }
    service.events().insert(calendarId="primary", body=event_body).execute()
    return f"Google Calendar event added for {start_dt.strftime('%d %B %Y at %I:%M %p')}: {title}."
