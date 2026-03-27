import datetime

from modules.briefing_module import build_brief_details, build_due_reminder_alert
from modules.event_module import get_event_data
from modules.profile_module import build_focus_suggestion
from modules.system_module import get_battery_info
from modules.task_module import get_task_data
from modules.weather_module import get_weather_report


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

    pending_tasks = [task for task in data.get("tasks", []) if not task.get("completed")]
    today_reminders = []

    for reminder in data.get("reminders", []):
        due_datetime = _parse_reminder_datetime(reminder)
        if due_datetime and due_datetime.date() == today:
            today_reminders.append((due_datetime, reminder))

    today_reminders.sort(key=lambda item: item[0])
    event_lines = _today_event_lines()

    parts = [f"Today agenda for {today.strftime('%d %B %Y')}:"]

    if event_lines:
        parts.append("Events: " + " | ".join(event_lines) + ".")

    if today_reminders:
        reminder_lines = [_format_reminder(reminder) for _, reminder in today_reminders[:5]]
        parts.append("Reminders: " + " | ".join(reminder_lines) + ".")

    if pending_tasks:
        task_lines = ", ".join(task.get("title", "Untitled task") for task in pending_tasks[:5])
        parts.append(f"Pending tasks: {task_lines}.")
    else:
        parts.append("You have no pending tasks right now.")

    focus_line = build_focus_suggestion()
    if focus_line:
        parts.append(f"Focus: {focus_line}")

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

    parts = [f"Daily recap for {today.strftime('%d %B %Y')}:"] 
    if completed_today:
        parts.append("Completed tasks: " + " | ".join(completed_today[:5]) + ".")
    else:
        parts.append("No tasks were marked completed today.")

    if pending_tasks:
        parts.append("Pending carry-over tasks: " + " | ".join(pending_tasks[:5]) + ".")

    if carry_over_reminders:
        parts.append("Open reminders to review: " + " | ".join(carry_over_reminders[:5]) + ".")

    if event_lines:
        parts.append("Today's event trail: " + " | ".join(event_lines[:4]) + ".")

    focus_line = build_focus_suggestion()
    if focus_line:
        parts.append("Next step: " + focus_line)

    return " ".join(parts)
