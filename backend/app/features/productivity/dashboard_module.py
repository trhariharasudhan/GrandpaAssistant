import datetime

from productivity.briefing_module import build_brief_details, build_due_reminder_alert
from productivity.event_module import get_event_data
from integrations.google_calendar_module import today_google_calendar_summary_lines
from productivity.profile_module import build_focus_suggestion
from system.system_module import get_battery_info
from productivity.task_module import get_task_data
from integrations.weather_module import get_weather_report
from utils.config import get_setting


def _parse_reminder_datetime(reminder):
    due_at = reminder.get("due_at")
    if due_at:
        try:
            return datetime.datetime.fromisoformat(due_at)
        except ValueError:
            pass

    due_date = reminder.get("due_date")
    if due_date:
        try:
            return datetime.datetime.combine(
                datetime.date.fromisoformat(due_date),
                datetime.time(hour=9, minute=0),
            )
        except ValueError:
            return None

    return None


def _format_reminder(reminder):
    due_datetime = _parse_reminder_datetime(reminder)
    title = reminder.get("title", "Untitled reminder")
    if due_datetime is None:
        return title
    return f"{title} at {due_datetime.strftime('%I:%M %p')}"


def _task_priority_rank(task):
    order = {"high": 0, "medium": 1, "normal": 2, "low": 3}
    return order.get(str(task.get("priority", "normal")).lower(), 2)


def _sort_pending_tasks(tasks):
    return sorted(
        tasks,
        key=lambda task: (
            _task_priority_rank(task),
            str(task.get("created_at") or "9999-12-31T23:59:59"),
            str(task.get("title") or ""),
        ),
    )


def _today_event_lines():
    today = datetime.date.today().isoformat()
    events = []

    for event in get_event_data().get("events", []):
        if event.get("date") != today:
            continue
        events.append(event)

    events.sort(key=lambda item: (item.get("time") or "23:59", item.get("title", "")))
    lines = []
    for event in events[:5]:
        title = event.get("title", "Untitled event")
        if event.get("time"):
            try:
                time_text = datetime.datetime.strptime(event["time"], "%H:%M").strftime("%I:%M %p")
            except ValueError:
                time_text = event["time"]
            lines.append(f"{title} at {time_text}")
        else:
            lines.append(title)
    return lines


def build_dashboard_report():
    parts = [build_brief_details()]

    battery_info = get_battery_info()
    if battery_info:
        parts.append(battery_info + ".")

    weather_info = get_weather_report("weather")
    if weather_info and "could not fetch weather" not in weather_info.lower():
        parts.append(weather_info)

    urgent_info = build_due_reminder_alert()
    if urgent_info and urgent_info != "No urgent reminders right now.":
        parts.append(urgent_info)

    data = get_task_data()
    pending_tasks = [task for task in data.get("tasks", []) if not task.get("completed")]
    reminders = data.get("reminders", [])

    if pending_tasks:
        top_tasks = ", ".join(task.get("title", "Untitled task") for task in pending_tasks[:3])
        parts.append(f"Top pending tasks: {top_tasks}.")

    if reminders:
        top_reminders = ", ".join(
            reminder.get("title", "Untitled reminder") for reminder in reminders[:3]
        )
        parts.append(f"Recent reminders: {top_reminders}.")

    return " ".join(part.strip() for part in parts if part)


def build_today_agenda():
    data = get_task_data()
    now = datetime.datetime.now()
    today = now.date()

    pending_tasks = _sort_pending_tasks(
        [task for task in data.get("tasks", []) if not task.get("completed")]
    )
    today_reminders = []
    overdue_reminders = []
    due_soon_reminders = []

    for reminder in data.get("reminders", []):
        due_datetime = _parse_reminder_datetime(reminder)
        if not due_datetime:
            continue
        if due_datetime < now:
            overdue_reminders.append((due_datetime, reminder))
        elif due_datetime <= now + datetime.timedelta(hours=2):
            due_soon_reminders.append((due_datetime, reminder))
        if due_datetime.date() == today:
            today_reminders.append((due_datetime, reminder))

    overdue_reminders.sort(key=lambda item: item[0])
    due_soon_reminders.sort(key=lambda item: item[0])
    today_reminders.sort(key=lambda item: item[0])
    event_lines = _today_event_lines()
    google_event_lines = today_google_calendar_summary_lines()

    parts = [f"Today agenda for {today.strftime('%d %B %Y')}:"]
    focus_mode_enabled = get_setting("assistant.focus_mode_enabled", False)
    focus_line = build_focus_suggestion()
    if focus_line:
        parts.append("Step 1: " + focus_line)

    if event_lines or google_event_lines:
        calendar_parts = []
        if event_lines:
            calendar_parts.append("Local: " + " | ".join(event_lines[:2]))
        if google_event_lines:
            calendar_parts.append("Google: " + " | ".join(google_event_lines[:2]))
        parts.append("Step 2: Calendar timeline - " + " || ".join(calendar_parts) + ".")
    else:
        parts.append("Step 2: Calendar timeline - no local or synced events today.")

    if overdue_reminders:
        reminder_lines = [_format_reminder(reminder) for _, reminder in overdue_reminders[:2]]
        parts.append("Step 3: Overdue reminders - " + " | ".join(reminder_lines) + ".")
    elif due_soon_reminders:
        reminder_lines = [_format_reminder(reminder) for _, reminder in due_soon_reminders[:2]]
        parts.append("Step 3: Due soon reminders - " + " | ".join(reminder_lines) + ".")
    elif today_reminders:
        reminder_lines = [_format_reminder(reminder) for _, reminder in today_reminders[:3]]
        parts.append("Step 3: Reminders for today - " + " | ".join(reminder_lines) + ".")
    else:
        parts.append("Step 3: Reminders - no reminders due today.")

    if pending_tasks:
        task_lines = [
            f"{task.get('title', 'Untitled task')} ({str(task.get('priority', 'normal')).lower()})"
            for task in pending_tasks[:3]
        ]
        parts.append("Step 4: Task queue - " + " | ".join(task_lines) + ".")
    else:
        parts.append("Step 4: Task queue - no pending tasks right now.")

    if focus_mode_enabled:
        parts.append("Focus mode is on, so proactive popups stay muted.")
    else:
        parts.append("Focus mode is off, so proactive suggestions can appear.")

    return " ".join(part.strip() for part in parts if part)


def build_daily_recap():
    data = get_task_data()
    now = datetime.datetime.now()
    today = now.date()

    completed_today = []
    pending_tasks = []
    carry_over_reminders = []

    for task in data.get("tasks", []):
        if task.get("completed"):
            completed_at = task.get("completed_at")
            try:
                completed_dt = datetime.datetime.fromisoformat(completed_at) if completed_at else None
            except ValueError:
                completed_dt = None
            if completed_dt and completed_dt.date() == today:
                completed_today.append(task.get("title", "Untitled task"))
        else:
            pending_tasks.append(task.get("title", "Untitled task"))

    for reminder in data.get("reminders", []):
        due_datetime = _parse_reminder_datetime(reminder)
        if due_datetime and due_datetime <= now:
            carry_over_reminders.append(reminder.get("title", "Untitled reminder"))

    event_lines = _today_event_lines()
    google_event_lines = today_google_calendar_summary_lines()

    parts = [f"Daily recap for {today.strftime('%d %B %Y')}:"] 
    if completed_today:
        parts.append("Completed: " + " | ".join(completed_today[:4]) + ".")
    else:
        parts.append("No tasks were marked completed today.")

    if pending_tasks:
        parts.append("Carry-over tasks: " + " | ".join(pending_tasks[:4]) + ".")

    if carry_over_reminders:
        parts.append("Open reminders: " + " | ".join(carry_over_reminders[:4]) + ".")

    if event_lines:
        parts.append("Today's event trail: " + " | ".join(event_lines[:4]) + ".")

    if google_event_lines:
        parts.append("Google Calendar trail: " + " | ".join(google_event_lines[:3]) + ".")

    focus_line = build_focus_suggestion()
    if focus_line:
        parts.append("Next step: " + focus_line)

    return " ".join(parts)
