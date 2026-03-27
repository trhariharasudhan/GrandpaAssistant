import datetime
import json
import os
import threading
import time

import win32com.client

from modules.dashboard_module import build_today_agenda
from modules.event_module import get_due_event_titles
from modules.health_module import get_system_status
from modules.task_module import get_task_data
from modules.weather_module import get_weather_report
from modules.briefing_module import build_brief_details
from modules.export_module import export_daily_recap_summary
from utils.config import get_setting


_monitor_thread = None
_monitor_stop_event = threading.Event()
_last_monitor_message = None
_last_agenda_popup_signature = None
_last_health_popup_signature = None
_last_weather_popup_signature = None
_last_status_popup_signature = None
_last_brief_popup_signature = None
_popup_history = {}
STATE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "notification_state.json",
)


def _load_notification_state():
    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def _save_notification_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=4)


def _get_state_value(key, default=None):
    state = _load_notification_state()
    return state.get(key, default)


def _set_state_value(key, value):
    state = _load_notification_state()
    state[key] = value
    _save_notification_state(state)


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


def _collect_monitor_lines():
    data = get_task_data()
    today = datetime.date.today()
    due_events = get_due_event_titles(days_ahead=1)

    due_reminders = []
    for reminder in data.get("reminders", []):
        due_date = _parse_date(reminder.get("due_date"))
        if due_date is None:
            continue
        if due_date <= today:
            due_reminders.append(reminder.get("title", "Untitled reminder"))

    pending_tasks = [
        task.get("title", "Untitled task")
        for task in data.get("tasks", [])
        if not task.get("completed")
    ]

    lines = []
    if due_reminders:
        lines.append(f"Due reminders ({len(due_reminders)}): {', '.join(due_reminders[:3])}")
    if pending_tasks:
        lines.append(f"Pending tasks ({len(pending_tasks)}): {', '.join(pending_tasks[:3])}")
    if get_setting("notifications.event_monitor_enabled", True):
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

    previous_summary = _get_state_value("last_startup_summary")
    if previous_summary == summary:
        return summary

    _show_popup(
        _notification_title("Startup Summary"),
        summary,
        timeout=max(_default_popup_timeout(), 12),
        dedupe_key="startup_summary",
    )
    _set_state_value("last_startup_summary", summary)
    return summary


def show_startup_agenda_popup():
    if not get_setting("notifications.agenda_popup_on_startup", False):
        return None

    agenda = build_today_agenda()
    previous_agenda = _get_state_value("last_startup_agenda")
    if previous_agenda == agenda:
        return agenda

    shown = _show_popup(
        _notification_title("Today Agenda"),
        agenda,
        timeout=max(_default_popup_timeout(), 12),
        dedupe_key="startup_agenda",
    )
    if shown:
        _set_state_value("last_startup_agenda", agenda)
    return agenda


def show_startup_health_popup():
    if not get_setting("notifications.health_popup_on_startup", False):
        return None

    health_status = get_system_status()
    previous_status = _get_state_value("last_startup_health_status")
    if previous_status == health_status:
        return health_status

    shown = _show_popup(
        _notification_title("System Health"),
        health_status,
        timeout=max(_default_popup_timeout(), 12),
        dedupe_key="startup_health",
    )
    if shown:
        _set_state_value("last_startup_health_status", health_status)
    return health_status


def show_startup_weather_popup():
    if not get_setting("notifications.weather_popup_on_startup", False):
        return None

    weather_status = get_weather_report("weather")
    previous_status = _get_state_value("last_startup_weather_status")
    if previous_status == weather_status:
        return weather_status

    shown = _show_popup(
        _notification_title("Weather"),
        weather_status,
        timeout=max(_default_popup_timeout(), 12),
        dedupe_key="startup_weather",
    )
    if shown:
        _set_state_value("last_startup_weather_status", weather_status)
    return weather_status


def show_startup_status_popup():
    if not get_setting("notifications.status_popup_on_startup", False):
        return None

    status_message = build_status_snapshot()
    previous_status = _get_state_value("last_startup_status_popup")
    if previous_status == status_message:
        return status_message

    shown = _show_popup(
        _notification_title("Status Snapshot"),
        status_message,
        timeout=max(_default_popup_timeout(), 12),
        dedupe_key="startup_status",
    )
    if shown:
        _set_state_value("last_startup_status_popup", status_message)
    return status_message


def show_startup_brief_popup():
    if not get_setting("notifications.brief_popup_on_startup", False):
        return None

    brief_message = build_brief_details()
    previous_brief = _get_state_value("last_startup_brief_popup")
    if previous_brief == brief_message:
        return brief_message

    shown = _show_popup(
        _notification_title("Daily Brief"),
        brief_message,
        timeout=max(_default_popup_timeout(), 12),
        dedupe_key="startup_brief",
    )
    if shown:
        _set_state_value("last_startup_brief_popup", brief_message)
    return brief_message


def run_startup_daily_automations():
    now = datetime.datetime.now()
    results = []

    if get_setting("notifications.morning_brief_automation_enabled", False) and 5 <= now.hour < 12:
        results.append(show_startup_brief_popup())

    if get_setting("notifications.night_summary_export_enabled", False) and now.hour >= 20:
        last_export_date = _get_state_value("last_night_summary_export_date")
        today_str = now.date().isoformat()
        if last_export_date != today_str:
            export_result = export_daily_recap_summary()
            _set_state_value("last_night_summary_export_date", today_str)
            results.append(export_result)

    return [item for item in results if item]


def show_health_popup():
    message = get_system_status()
    if _show_popup(_notification_title("System Health"), message, force=True):
        return "System health popup shown."
    return "I could not show the system health popup right now."


def show_weather_popup():
    message = get_weather_report("weather")
    if _show_popup(_notification_title("Weather"), message, force=True):
        return "Weather popup shown."
    return "I could not show the weather popup right now."


def build_status_snapshot():
    health = get_system_status()
    weather = get_weather_report("weather")
    return f"{health}\n\n{weather}"


def show_status_popup():
    message = build_status_snapshot()
    if _show_popup(_notification_title("Status Snapshot"), message, timeout=max(_default_popup_timeout(), 12), force=True):
        return "Status snapshot popup shown."
    return "I could not show the status snapshot popup right now."


def show_brief_popup():
    message = build_brief_details()
    if _show_popup(_notification_title("Daily Brief"), message, timeout=max(_default_popup_timeout(), 12), force=True):
        return "Daily brief popup shown."
    return "I could not show the daily brief popup right now."


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


def show_agenda_popup():
    message = build_today_agenda()
    if _show_popup(_notification_title("Today Agenda"), message, timeout=max(_default_popup_timeout(), 12), force=True):
        return "Agenda popup shown."
    return "I could not show the agenda popup right now."


def show_custom_popup(title_suffix, message, dedupe_key=None, force=True):
    if _show_popup(
        _notification_title(title_suffix),
        message,
        dedupe_key=dedupe_key,
        force=force,
    ):
        return True
    return False


def _build_due_monitor_message():
    lines = _collect_monitor_lines()
    return _format_lines(lines) if lines else None


def _monitor_worker():
    global _last_monitor_message, _last_agenda_popup_signature, _last_health_popup_signature
    global _last_weather_popup_signature, _last_status_popup_signature, _last_brief_popup_signature

    while not _monitor_stop_event.is_set():
        if get_setting("notifications.reminder_monitor_enabled", True) or get_setting(
            "notifications.event_monitor_enabled", True
        ):
            message = _build_due_monitor_message()
            if message and message != _last_monitor_message:
                previous_persisted_message = _get_state_value("last_monitor_message")
                if message == previous_persisted_message:
                    _last_monitor_message = message
                else:
                    shown = _show_popup(
                        _notification_title("Reminder Monitor"),
                        message,
                        dedupe_key="reminder_monitor",
                    )
                    if shown:
                        _last_monitor_message = message
                        _set_state_value("last_monitor_message", message)

        if get_setting("notifications.agenda_popup_enabled", False):
            agenda_interval = max(
                5, int(get_setting("notifications.agenda_popup_interval_minutes", 60))
            )
            now = datetime.datetime.now()
            minute_slot = now.replace(
                minute=(now.minute // agenda_interval) * agenda_interval,
                second=0,
                microsecond=0,
            )
            agenda_signature = minute_slot.isoformat()
            if agenda_signature != _last_agenda_popup_signature:
                agenda_message = build_today_agenda()
                shown = _show_popup(
                    _notification_title("Today Agenda"),
                    agenda_message,
                    dedupe_key="agenda_monitor",
                    force=False,
                )
                if shown:
                    _last_agenda_popup_signature = agenda_signature

        if get_setting("notifications.health_popup_enabled", False):
            health_interval = max(
                5, int(get_setting("notifications.health_popup_interval_minutes", 60))
            )
            now = datetime.datetime.now()
            minute_slot = now.replace(
                minute=(now.minute // health_interval) * health_interval,
                second=0,
                microsecond=0,
            )
            health_signature = minute_slot.isoformat()
            if health_signature != _last_health_popup_signature:
                health_message = get_system_status()
                shown = _show_popup(
                    _notification_title("System Health"),
                    health_message,
                    dedupe_key="health_monitor",
                    force=False,
                )
                if shown:
                    _last_health_popup_signature = health_signature

        if get_setting("notifications.weather_popup_enabled", False):
            weather_interval = max(
                15, int(get_setting("notifications.weather_popup_interval_minutes", 120))
            )
            now = datetime.datetime.now()
            minute_slot = now.replace(
                minute=(now.minute // weather_interval) * weather_interval,
                second=0,
                microsecond=0,
            )
            weather_signature = minute_slot.isoformat()
            if weather_signature != _last_weather_popup_signature:
                weather_message = get_weather_report("weather")
                shown = _show_popup(
                    _notification_title("Weather"),
                    weather_message,
                    dedupe_key="weather_monitor",
                    force=False,
                )
                if shown:
                    _last_weather_popup_signature = weather_signature

        if get_setting("notifications.status_popup_enabled", False):
            status_interval = max(
                15, int(get_setting("notifications.status_popup_interval_minutes", 120))
            )
            now = datetime.datetime.now()
            minute_slot = now.replace(
                minute=(now.minute // status_interval) * status_interval,
                second=0,
                microsecond=0,
            )
            status_signature = minute_slot.isoformat()
            if status_signature != _last_status_popup_signature:
                status_message = build_status_snapshot()
                shown = _show_popup(
                    _notification_title("Status Snapshot"),
                    status_message,
                    dedupe_key="status_monitor",
                    force=False,
                )
                if shown:
                    _last_status_popup_signature = status_signature

        if get_setting("notifications.brief_popup_enabled", False):
            brief_interval = max(
                30, int(get_setting("notifications.brief_popup_interval_minutes", 180))
            )
            now = datetime.datetime.now()
            minute_slot = now.replace(
                minute=(now.minute // brief_interval) * brief_interval,
                second=0,
                microsecond=0,
            )
            brief_signature = minute_slot.isoformat()
            if brief_signature != _last_brief_popup_signature:
                brief_message = build_brief_details()
                shown = _show_popup(
                    _notification_title("Daily Brief"),
                    brief_message,
                    dedupe_key="brief_monitor",
                    force=False,
                )
                if shown:
                    _last_brief_popup_signature = brief_signature

        reminder_interval = max(
            1, int(get_setting("notifications.reminder_check_interval_minutes", 15))
        )
        event_interval = max(
            1, int(get_setting("notifications.event_check_interval_minutes", 15))
        )
        agenda_interval = max(
            5, int(get_setting("notifications.agenda_popup_interval_minutes", 60))
        )
        interval_candidates = [reminder_interval, event_interval]
        if get_setting("notifications.agenda_popup_enabled", False):
            interval_candidates.append(agenda_interval)
        if get_setting("notifications.health_popup_enabled", False):
            interval_candidates.append(
                max(5, int(get_setting("notifications.health_popup_interval_minutes", 60)))
            )
        if get_setting("notifications.weather_popup_enabled", False):
            interval_candidates.append(
                max(15, int(get_setting("notifications.weather_popup_interval_minutes", 120)))
            )
        if get_setting("notifications.status_popup_enabled", False):
            interval_candidates.append(
                max(15, int(get_setting("notifications.status_popup_interval_minutes", 120)))
            )
        if get_setting("notifications.brief_popup_enabled", False):
            interval_candidates.append(
                max(30, int(get_setting("notifications.brief_popup_interval_minutes", 180)))
            )
        interval = min(interval_candidates)
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
