import datetime
import threading
import time

import win32com.client

from modules.event_module import get_due_event_titles
from modules.health_module import get_system_status
from modules.task_module import get_task_data
from utils.config import get_setting


_monitor_thread = None
_monitor_stop_event = threading.Event()
_last_monitor_message = None
_popup_history = {}


def _notification_title(suffix=None):
    return f"Grandpa Assistant - {suffix}" if suffix else "Grandpa Assistant"


def _default_popup_timeout():
    return max(3, int(get_setting("notifications.popup_timeout_seconds", 10)))


def _popup_cooldown_seconds():
    return max(0, int(get_setting("notifications.popup_cooldown_seconds", 180)))


def _parse_date(date_str):
    if not date_str:
        return None

    try:
        return datetime.date.fromisoformat(date_str)
    except ValueError:
        return None


def _format_lines(lines):
    return "\n".join(f"- {line}" for line in lines if line)


def _dedupe_popup(dedupe_key, message, cooldown_seconds):
    if not dedupe_key:
        return False

    now = time.time()
    last = _popup_history.get(dedupe_key)
    if last and last["message"] == message and (now - last["shown_at"]) < cooldown_seconds:
        return True

    _popup_history[dedupe_key] = {"message": message, "shown_at": now}
    return False


def _show_popup(
    title,
    message,
    timeout=None,
    dedupe_key=None,
    cooldown_seconds=None,
    force=False,
):
    timeout = _default_popup_timeout() if timeout is None else timeout
    cooldown_seconds = (
        _popup_cooldown_seconds() if cooldown_seconds is None else cooldown_seconds
    )

    if not message:
        return False

    if not force and _dedupe_popup(dedupe_key, message, cooldown_seconds):
        return False

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        threading.Thread(
            target=lambda: shell.Popup(message, timeout, title, 64), daemon=True
        ).start()
        return True
    except Exception:
        return False


def _collect_notification_lines():
    data = get_task_data()
    today = datetime.date.today()
    due_events = get_due_event_titles(days_ahead=1)

    pending_tasks = [task for task in data.get("tasks", []) if not task.get("completed")]
    overdue = []
    due_today = []

    for reminder in data.get("reminders", []):
        due_date = _parse_date(reminder.get("due_date"))
        if due_date is None:
            continue
        if due_date < today:
            overdue.append(reminder.get("title", "Untitled reminder"))
        elif due_date == today:
            due_today.append(reminder.get("title", "Untitled reminder"))

    lines = []
    if pending_tasks:
        task_titles = [task.get("title", "Untitled task") for task in pending_tasks[:3]]
        lines.append(f"Pending tasks ({len(pending_tasks)}): {', '.join(task_titles)}")
    if overdue:
        lines.append(f"Overdue reminders ({len(overdue)}): {', '.join(overdue[:3])}")
    if due_today:
        lines.append(f"Today's reminders ({len(due_today)}): {', '.join(due_today[:3])}")
    if due_events["today"]:
        lines.append(f"Today's events ({len(due_events['today'])}): {', '.join(due_events['today'][:3])}")
    if due_events["upcoming"]:
        lines.append(
            f"Upcoming events ({len(due_events['upcoming'])}): {', '.join(due_events['upcoming'][:2])}"
        )

    return lines


def build_notification_summary():
    lines = _collect_notification_lines()
    if not lines:
        return "You do not have any urgent reminders, pending tasks, or upcoming events right now."

    return _format_lines(lines)


def show_notification_summary():
    message = build_notification_summary()
    if _show_popup(_notification_title("Summary"), message, force=True):
        return "Notification popup shown."
    return "I could not show the desktop notification right now."


def show_reminder_popup():
    data = get_task_data()
    today = datetime.date.today()
    items = []

    for reminder in data.get("reminders", []):
        due_date = _parse_date(reminder.get("due_date"))
        if due_date is None:
            continue
        if due_date <= today:
            items.append(reminder.get("title", "Untitled reminder"))

    if not items:
        return "You do not have any due reminder popups right now."

    message = _format_lines([f"Due reminders: {', '.join(items[:5])}"])
    if _show_popup(_notification_title("Reminders"), message, force=True):
        return "Reminder popup shown."
    return "I could not show the reminder popup right now."


def show_task_popup():
    data = get_task_data()
    items = [task.get("title", "Untitled task") for task in data.get("tasks", []) if not task.get("completed")]

    if not items:
        return "You do not have any pending task popups right now."

    message = _format_lines([f"Pending tasks: {', '.join(items[:5])}"])
    if _show_popup(_notification_title("Tasks"), message, force=True):
        return "Task popup shown."
    return "I could not show the task popup right now."


def show_startup_notifications():
    summary = build_notification_summary()
    if summary == "You do not have any urgent reminders, pending tasks, or upcoming events right now.":
        return None

    _show_popup(
        _notification_title("Startup Summary"),
        summary,
        timeout=max(_default_popup_timeout(), 12),
        dedupe_key="startup_summary",
    )
    return summary


def show_health_popup():
    message = get_system_status()
    if _show_popup(_notification_title("System Health"), message, force=True):
        return "System health popup shown."
    return "I could not show the system health popup right now."


def show_event_popup():
    due_events = get_due_event_titles(days_ahead=1)
    parts = []

    if due_events["today"]:
        parts.append("Today's events:\n" + "\n".join(due_events["today"][:5]))
    if due_events["upcoming"]:
        parts.append("Upcoming events:\n" + "\n".join(due_events["upcoming"][:5]))

    if not parts:
        return "You do not have any event popups right now."

    message = "\n\n".join(parts)
    if _show_popup(_notification_title("Events"), message, force=True):
        return "Event popup shown."
    return "I could not show the event popup right now."


def _build_due_monitor_message():
    lines = _collect_notification_lines()
    if not get_setting("notifications.event_monitor_enabled", True):
        lines = [line for line in lines if "events" not in line.lower()]
    return _format_lines(lines) if lines else None


def _monitor_worker():
    global _last_monitor_message

    while not _monitor_stop_event.is_set():
        if get_setting("notifications.reminder_monitor_enabled", True) or get_setting(
            "notifications.event_monitor_enabled", True
        ):
            message = _build_due_monitor_message()
            if message and message != _last_monitor_message:
                shown = _show_popup(
                    _notification_title("Reminder Monitor"),
                    message,
                    dedupe_key="reminder_monitor",
                )
                if shown:
                    _last_monitor_message = message

        reminder_interval = max(
            1, int(get_setting("notifications.reminder_check_interval_minutes", 15))
        )
        event_interval = max(
            1, int(get_setting("notifications.event_check_interval_minutes", 15))
        )
        interval = min(reminder_interval, event_interval)
        sleep_seconds = interval * 60

        for _ in range(sleep_seconds):
            if _monitor_stop_event.is_set():
                return
            time.sleep(1)


def start_notification_monitor():
    global _monitor_thread

    if _monitor_thread and _monitor_thread.is_alive():
        return False

    _monitor_stop_event.clear()
    _monitor_thread = threading.Thread(target=_monitor_worker, daemon=True)
    _monitor_thread.start()
    return True


def stop_notification_monitor():
    _monitor_stop_event.set()
    return True
