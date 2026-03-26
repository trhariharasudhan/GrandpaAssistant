import datetime

from modules.calendar_module import get_day, get_period, get_time
from modules.task_module import get_task_data


def _parse_date(date_str):
    if not date_str:
        return None

    try:
        return datetime.date.fromisoformat(date_str)
    except ValueError:
        return None


def _parse_datetime(date_str):
    if not date_str:
        return None

    try:
        return datetime.datetime.fromisoformat(date_str)
    except ValueError:
        return None


def _get_due_datetime(reminder):
    due_at = _parse_datetime(reminder.get("due_at"))
    if due_at is not None:
        return due_at

    due_date = _parse_date(reminder.get("due_date"))
    if due_date is not None:
        return datetime.datetime.combine(due_date, datetime.time(hour=9, minute=0))

    return None


def _format_due_for_brief(reminder):
    due_datetime = _get_due_datetime(reminder)
    if due_datetime is None:
        return "No date"
    return due_datetime.strftime("%d %B %I:%M %p")


def build_daily_brief():
    today = datetime.date.today()
    now = datetime.datetime.now()
    data = get_task_data()

    tasks = data.get("tasks", [])
    reminders = data.get("reminders", [])

    pending_tasks = [task for task in tasks if not task.get("completed")]
    due_today = []
    overdue = []
    upcoming = []

    for reminder in reminders:
        due_datetime = _get_due_datetime(reminder)
        if due_datetime is None:
            continue

        due_date = due_datetime.date()

        if due_datetime < now:
            overdue.append(reminder)
        elif due_date == today:
            due_today.append(reminder)
        elif due_date <= today + datetime.timedelta(days=3):
            upcoming.append(reminder)

    parts = [
        f"Good {get_period().replace('It is ', '').lower()}.",
        f"Today is {get_day()}.",
        f"The time is {get_time()}.",
    ]

    if pending_tasks:
        parts.append(f"You have {len(pending_tasks)} pending tasks.")
    else:
        parts.append("You have no pending tasks.")

    if overdue:
        parts.append(f"You have {len(overdue)} overdue reminders.")

    if due_today:
        parts.append(f"You have {len(due_today)} reminders for today.")
    elif upcoming:
        parts.append(f"You have {len(upcoming)} upcoming reminders in the next 3 days.")
    else:
        parts.append("You have no upcoming reminders.")

    return " ".join(parts)


def build_due_reminder_alert():
    today = datetime.date.today()
    now = datetime.datetime.now()
    data = get_task_data()

    overdue = []
    due_today = []

    for reminder in data.get("reminders", []):
        due_datetime = _get_due_datetime(reminder)
        if due_datetime is None:
            continue

        if due_datetime < now:
            overdue.append(f"{reminder.get('title', 'Untitled reminder')} at {_format_due_for_brief(reminder)}")
        elif due_datetime.date() == today:
            due_today.append(f"{reminder.get('title', 'Untitled reminder')} at {_format_due_for_brief(reminder)}")

    parts = []

    if overdue:
        parts.append("Overdue reminders: " + ", ".join(overdue[:5]) + ".")

    if due_today:
        parts.append("Today's reminders: " + ", ".join(due_today[:5]) + ".")

    if not parts:
        return "No urgent reminders right now."

    return " ".join(parts)


def build_brief_details():
    today = datetime.date.today()
    data = get_task_data()

    pending_tasks = [task for task in data.get("tasks", []) if not task.get("completed")]
    reminders = data.get("reminders", [])

    lines = [build_daily_brief()]

    if pending_tasks:
        task_titles = ", ".join(task.get("title", "Untitled task") for task in pending_tasks[:5])
        lines.append(f"Pending tasks: {task_titles}.")

    dated_reminders = []
    for reminder in reminders:
        due_datetime = _get_due_datetime(reminder)
        if due_datetime is not None and due_datetime.date() <= today + datetime.timedelta(days=3):
            dated_reminders.append((due_datetime, reminder.get("title", "Untitled reminder")))

    dated_reminders.sort(key=lambda item: item[0])

    if dated_reminders:
        reminder_text = ", ".join(
            f"{title} on {due_datetime.strftime('%d %B %I:%M %p')}"
            for due_datetime, title in dated_reminders[:5]
        )
        lines.append(f"Upcoming reminders: {reminder_text}.")

    return " ".join(lines)
