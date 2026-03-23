import datetime
import threading
import time

import win32com.client

from modules.health_module import get_system_status
from modules.task_module import get_task_data
from utils.config import get_setting


_monitor_thread = None
_monitor_stop_event = threading.Event()
_last_monitor_message = None


def _parse_date(date_str):
    if not date_str:
        return None

    try:
        return datetime.date.fromisoformat(date_str)
    except ValueError:
        return None


def _show_popup(title, message, timeout=8):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        threading.Thread(
            target=lambda: shell.Popup(message, timeout, title, 64), daemon=True
        ).start()
        return True
    except Exception:
        return False


def build_notification_summary():
    data = get_task_data()
    today = datetime.date.today()

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

    parts = []
    if pending_tasks:
        parts.append(f"Pending tasks: {len(pending_tasks)}")
    if overdue:
        parts.append("Overdue reminders: " + ", ".join(overdue[:3]))
    if due_today:
        parts.append("Today's reminders: " + ", ".join(due_today[:3]))

    if not parts:
        return "You do not have any urgent reminders or pending tasks right now."

    return " | ".join(parts)


def show_notification_summary():
    message = build_notification_summary()
    if _show_popup("Grandpa Assistant", message):
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

    message = "Due reminders:\n" + "\n".join(items[:5])
    if _show_popup("Reminder Alert", message):
        return "Reminder popup shown."
    return "I could not show the reminder popup right now."


def show_task_popup():
    data = get_task_data()
    items = [task.get("title", "Untitled task") for task in data.get("tasks", []) if not task.get("completed")]

    if not items:
        return "You do not have any pending task popups right now."

    message = "Pending tasks:\n" + "\n".join(items[:5])
    if _show_popup("Task Alert", message):
        return "Task popup shown."
    return "I could not show the task popup right now."


def show_startup_notifications():
    summary = build_notification_summary()
    if summary == "You do not have any urgent reminders or pending tasks right now.":
        return None

    _show_popup("Grandpa Assistant", summary, timeout=10)
    return summary


def show_health_popup():
    message = get_system_status()
    if _show_popup("System Health", message, timeout=10):
        return "System health popup shown."
    return "I could not show the system health popup right now."


def _build_due_monitor_message():
    data = get_task_data()
    today = datetime.date.today()
    due_items = []

    for reminder in data.get("reminders", []):
        due_date = _parse_date(reminder.get("due_date"))
        if due_date is None:
            continue
        if due_date <= today:
            due_items.append(reminder.get("title", "Untitled reminder"))

    pending_tasks = [
        task.get("title", "Untitled task")
        for task in data.get("tasks", [])
        if not task.get("completed")
    ]

    parts = []
    if due_items:
        parts.append("Due reminders: " + ", ".join(due_items[:3]))
    if pending_tasks:
        parts.append("Pending tasks: " + ", ".join(pending_tasks[:3]))

    return " | ".join(parts) if parts else None


def _monitor_worker():
    global _last_monitor_message

    while not _monitor_stop_event.is_set():
        if get_setting("notifications.reminder_monitor_enabled", True):
            message = _build_due_monitor_message()
            if message and message != _last_monitor_message:
                _show_popup("Grandpa Reminder Monitor", message, timeout=10)
                _last_monitor_message = message

        interval = max(1, int(get_setting("notifications.reminder_check_interval_minutes", 15)))
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
