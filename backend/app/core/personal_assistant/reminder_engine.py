from __future__ import annotations

import datetime
import re
import uuid
from typing import Any, Callable

try:
    from shared.productivity_store import load_task_payload, save_task_payload
except ImportError:  # pragma: no cover
    from productivity_store import load_task_payload, save_task_payload

from .context import compact_text
from .notifications import deliver_reminder_notification


ReminderPayloadLoader = Callable[..., dict[str, Any]]
ReminderPayloadSaver = Callable[..., None]
Notifier = Callable[[dict[str, Any]], dict[str, Any]]

REMINDER_STATUSES = {"pending", "due", "done", "cancelled"}


def default_task_payload() -> dict[str, list[dict[str, Any]]]:
    return {"tasks": [], "reminders": []}


def utc_now_text(now: datetime.datetime | None = None) -> str:
    moment = now or datetime.datetime.utcnow()
    return moment.replace(microsecond=0).isoformat() + "Z"


def local_now(now: datetime.datetime | None = None) -> datetime.datetime:
    return (now or datetime.datetime.now()).replace(second=0, microsecond=0)


def parse_due_datetime(time_text: str, *, now: datetime.datetime | None = None) -> datetime.datetime | None:
    normalized = compact_text(time_text).lower()
    if not normalized:
        return None
    base_now = local_now(now)
    if "naalai" in normalized or "tomorrow" in normalized:
        base = base_now.date() + datetime.timedelta(days=1)
    elif "today" in normalized or "indru" in normalized:
        base = base_now.date()
    else:
        base = base_now.date()
    if "morning" in normalized:
        clock = datetime.time(hour=9, minute=0)
    elif "afternoon" in normalized:
        clock = datetime.time(hour=13, minute=0)
    elif "evening" in normalized or "night" in normalized:
        clock = datetime.time(hour=18, minute=0)
    else:
        clock = datetime.time(hour=9, minute=0)
    relative = re.search(r"\bin\s+(\d+)\s+(minute|minutes|hour|hours|day|days|week|weeks)\b", normalized)
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2)
        if "minute" in unit:
            return base_now + datetime.timedelta(minutes=amount)
        if "hour" in unit:
            return base_now + datetime.timedelta(hours=amount)
        if "week" in unit:
            return base_now + datetime.timedelta(days=amount * 7)
        return base_now + datetime.timedelta(days=amount)
    explicit = re.search(r"\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", normalized)
    if explicit:
        hour = int(explicit.group(1))
        minute = int(explicit.group(2) or 0)
        meridiem = explicit.group(3)
        if hour == 12:
            hour = 0
        if meridiem == "pm":
            hour += 12
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            clock = datetime.time(hour=hour, minute=minute)
    return datetime.datetime.combine(base, clock)


def parse_reminder_datetime(value: Any) -> datetime.datetime | None:
    text = compact_text(value)
    if not text:
        return None
    try:
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def due_label(due_at: datetime.datetime | None) -> str:
    if due_at is None:
        return ""
    return due_at.strftime("%I:%M %p").lstrip("0")


def normalize_reminder_record(details: dict[str, Any], *, now: datetime.datetime | None = None) -> dict[str, Any]:
    created = local_now(now)
    reminder_text = compact_text(details.get("reminder_text") or details.get("title") or details.get("topic"))
    title = reminder_text or "Untitled reminder"
    time_text = compact_text(details.get("time_text") or details.get("due_at") or details.get("due_datetime"))
    due_at = parse_due_datetime(time_text, now=created) if time_text else parse_reminder_datetime(details.get("due_datetime") or details.get("due_at"))
    due_iso = due_at.isoformat(timespec="minutes") if due_at else None
    created_text = compact_text(details.get("created_at")) or created.isoformat(timespec="seconds")
    record = {
        "id": compact_text(details.get("id")) or uuid.uuid4().hex[:12],
        "title": title,
        "topic": compact_text(details.get("topic")) or title,
        "due_date": due_at.date().isoformat() if due_at else None,
        "due_at": due_iso,
        "due_datetime": due_iso,
        "due_label": due_label(due_at),
        "reminder_offset": compact_text(details.get("reminder_offset")),
        "status": compact_text(details.get("status")).lower() if compact_text(details.get("status")).lower() in REMINDER_STATUSES else "pending",
        "source_conversation_summary": compact_text(details.get("source_conversation_summary")) or "Reminder created from context-aware assistant flow.",
        "recurrence": details.get("recurrence") or None,
        "created_at": created_text,
        "updated_at": compact_text(details.get("updated_at")) or created_text,
        "notified_at": compact_text(details.get("notified_at")),
        "completed_at": compact_text(details.get("completed_at")),
        "cancelled_at": compact_text(details.get("cancelled_at")),
    }
    return record


def _load_payload(load_payload: ReminderPayloadLoader | None = None) -> dict[str, Any]:
    loader = load_payload or load_task_payload
    try:
        payload = loader(default_factory=default_task_payload)
    except TypeError:
        payload = loader()
    if not isinstance(payload, dict):
        payload = default_task_payload()
    payload.setdefault("tasks", [])
    reminders = payload.setdefault("reminders", [])
    if not isinstance(reminders, list):
        payload["reminders"] = []
    return payload


def _save_payload(payload: dict[str, Any], save_payload: ReminderPayloadSaver | None = None) -> None:
    saver = save_payload or save_task_payload
    try:
        saver(payload, default_factory=default_task_payload)
    except TypeError:
        saver(payload)


def create_reminder(
    details: dict[str, Any],
    *,
    now: datetime.datetime | None = None,
    load_payload: ReminderPayloadLoader | None = None,
    save_payload: ReminderPayloadSaver | None = None,
) -> dict[str, Any]:
    payload = _load_payload(load_payload)
    record = normalize_reminder_record(details or {}, now=now)
    payload.setdefault("reminders", []).append(record)
    _save_payload(payload, save_payload)
    if record.get("due_at"):
        due_at = parse_reminder_datetime(record.get("due_at"))
        friendly_due = due_at.strftime("%I:%M %p on %d %B %Y").lstrip("0") if due_at else compact_text(record.get("due_at"))
        message = f"Reminder saved. I'll remind you at {friendly_due}. Reminder added for {record['due_at']}: {record['title']}"
    else:
        message = f"Reminder saved. Reminder added: {record['title']}"
    return {"ok": True, "message": message, "reminder": record}


def list_reminders(
    *,
    status: str = "pending",
    load_payload: ReminderPayloadLoader | None = None,
) -> dict[str, Any]:
    payload = _load_payload(load_payload)
    wanted = compact_text(status).lower()
    reminders = []
    for reminder in payload.get("reminders") or []:
        if not isinstance(reminder, dict):
            continue
        current = compact_text(reminder.get("status")).lower() or "pending"
        if wanted in {"", "all"} or current == wanted:
            reminders.append(reminder)
    reminders.sort(key=lambda item: (compact_text(item.get("due_at")) or "9999", compact_text(item.get("title"))))
    if not reminders:
        label = wanted or "pending"
        return {"ok": True, "message": f"You have no {label} reminders.", "reminders": []}
    parts = []
    for item in reminders[:6]:
        title = compact_text(item.get("title")) or "Untitled reminder"
        due = compact_text(item.get("due_label")) or compact_text(item.get("due_at")) or "no time"
        parts.append(f"{title} at {due}")
    return {"ok": True, "message": "Pending reminders: " + "; ".join(parts) + ".", "reminders": reminders}


def _query_tokens(query: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", compact_text(query).lower()) if token not in {"my", "the", "this", "that", "reminder", "meeting"}]


def find_matching_reminders(
    query: str,
    *,
    statuses: tuple[str, ...] = ("pending", "due"),
    load_payload: ReminderPayloadLoader | None = None,
) -> list[dict[str, Any]]:
    payload = _load_payload(load_payload)
    tokens = _query_tokens(query)
    matches = []
    for reminder in payload.get("reminders") or []:
        if not isinstance(reminder, dict):
            continue
        status = compact_text(reminder.get("status")).lower() or "pending"
        if status not in statuses:
            continue
        if not tokens:
            matches.append(reminder)
            continue
        haystack = " ".join(
            compact_text(reminder.get(key)).lower()
            for key in ("id", "title", "topic", "source_conversation_summary", "due_at")
        )
        if all(token in haystack for token in tokens):
            matches.append(reminder)
    matches.sort(key=lambda item: (compact_text(item.get("due_at")) or "9999", compact_text(item.get("title"))))
    return matches


def _save_status_change(
    query: str,
    *,
    new_status: str,
    timestamp_key: str,
    now: datetime.datetime | None = None,
    load_payload: ReminderPayloadLoader | None = None,
    save_payload: ReminderPayloadSaver | None = None,
) -> dict[str, Any]:
    payload = _load_payload(load_payload)
    matches = find_matching_reminders(query, load_payload=lambda default_factory=None: payload)
    if not matches:
        return {"ok": False, "needs_disambiguation": False, "message": "I could not find a matching pending reminder.", "matches": []}
    if len(matches) > 1:
        options = [compact_text(item.get("title")) or compact_text(item.get("id")) for item in matches[:5]]
        return {
            "ok": False,
            "needs_disambiguation": True,
            "message": "I found multiple matching reminders. Which one should I update? " + "; ".join(options),
            "matches": matches,
        }
    target_id = compact_text(matches[0].get("id"))
    changed = None
    stamp = local_now(now).isoformat(timespec="seconds")
    for reminder in payload.get("reminders") or []:
        if isinstance(reminder, dict) and compact_text(reminder.get("id")) == target_id:
            reminder["status"] = new_status
            reminder[timestamp_key] = stamp
            reminder["updated_at"] = stamp
            changed = reminder
            break
    _save_payload(payload, save_payload)
    title = compact_text((changed or {}).get("title")) or "that reminder"
    verb = "marked done" if new_status == "done" else "cancelled"
    return {"ok": True, "needs_disambiguation": False, "message": f"Reminder {verb}: {title}.", "reminder": changed}


def complete_reminder(
    query: str,
    *,
    now: datetime.datetime | None = None,
    load_payload: ReminderPayloadLoader | None = None,
    save_payload: ReminderPayloadSaver | None = None,
) -> dict[str, Any]:
    return _save_status_change(query, new_status="done", timestamp_key="completed_at", now=now, load_payload=load_payload, save_payload=save_payload)


def cancel_reminder(
    query: str,
    *,
    now: datetime.datetime | None = None,
    load_payload: ReminderPayloadLoader | None = None,
    save_payload: ReminderPayloadSaver | None = None,
) -> dict[str, Any]:
    return _save_status_change(query, new_status="cancelled", timestamp_key="cancelled_at", now=now, load_payload=load_payload, save_payload=save_payload)


def check_due_reminders(
    *,
    now: datetime.datetime | None = None,
    notifier: Notifier | None = None,
    load_payload: ReminderPayloadLoader | None = None,
    save_payload: ReminderPayloadSaver | None = None,
) -> dict[str, Any]:
    moment = local_now(now)
    payload = _load_payload(load_payload)
    notifications = []
    due_records = []
    changed = False
    for reminder in payload.get("reminders") or []:
        if not isinstance(reminder, dict):
            continue
        status = compact_text(reminder.get("status")).lower() or "pending"
        due_at = parse_reminder_datetime(reminder.get("due_datetime") or reminder.get("due_at"))
        if due_at is None or due_at > moment:
            continue
        if status == "pending":
            reminder["status"] = "due"
            reminder["updated_at"] = moment.isoformat(timespec="seconds")
            status = "due"
            changed = True
        if status == "due":
            due_records.append(reminder)
            if not compact_text(reminder.get("notified_at")):
                delivery = (notifier or deliver_reminder_notification)(reminder)
                reminder["notified_at"] = moment.isoformat(timespec="seconds")
                reminder["updated_at"] = moment.isoformat(timespec="seconds")
                notifications.append({"reminder": reminder, "delivery": delivery})
                changed = True
    if changed:
        _save_payload(payload, save_payload)
    if notifications:
        titles = "; ".join(compact_text(item["reminder"].get("title")) for item in notifications[:5])
        message = "Due reminder notification sent: " + titles + "."
    elif due_records:
        message = "There are due reminders, but they were already notified."
    else:
        message = "No reminders are due right now."
    return {
        "ok": True,
        "message": message,
        "due_reminders": due_records,
        "notifications": notifications,
        "notification_count": len(notifications),
    }
