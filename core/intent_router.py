import datetime

from modules.briefing_module import build_brief_details, build_due_reminder_alert
from modules.calendar_module import get_date, get_day, get_period, get_time
from modules.dashboard_module import build_dashboard_report
from modules.notes_module import add_note, delete_note, list_notes
from modules.profile_module import (
    build_focus_suggestion,
    build_personal_snapshot,
    build_profile_summary,
    build_proactive_nudge,
)
from modules.weather_module import get_weather_report
from modules.window_context_module import (
    describe_active_window,
    get_active_app_name,
    get_active_window_title,
    summarize_active_window,
    summarize_browser_page,
    summarize_code_editor,
    summarize_if_browser,
    summarize_if_code_editor,
    summarize_if_file_explorer,
    summarize_current_folder,
    summarize_whatsapp_context,
)
from modules.routine_module import (
    create_custom_routine,
    delete_custom_routine,
    list_custom_routines,
    list_routines,
    run_routine,
)
from modules.task_module import (
    add_reminder,
    add_task,
    complete_task,
    delete_reminder,
    delete_task,
    list_reminders,
    list_tasks,
)


def _reply_text(handler_result):
    return {"handled": True, "reply": handler_result}


def _time_reply(_command):
    return f"The current time is {get_time()} and {get_period()}"


def _date_reply(_command):
    return f"Today's date is {get_date()}"


def _day_reply(_command):
    return f"Today is {get_day()}"


def _week_reply(_command):
    return f"This week is week number {datetime.datetime.now().isocalendar()[1]}"


def _month_reply(_command):
    return f"The current month is {datetime.datetime.now().strftime('%B')}"


def _year_reply(_command):
    return f"The current year is {datetime.datetime.now().year}"


COMMAND_REGISTRY = [
    {
        "intent": "time.current",
        "patterns": [
            "time now",
            "current time",
            "what time",
            "what is time",
            "what is the time",
            "what is the time now",
            "tell me the time",
        ],
        "type": "contains_any",
        "handler": _time_reply,
        "category": "date_time",
        "confidence": 0.95,
    },
    {
        "intent": "date.current",
        "patterns": [
            "today date",
            "current date",
            "what is date",
            "what is the date",
            "what is today's date",
        ],
        "type": "contains_any",
        "handler": _date_reply,
        "category": "date_time",
        "confidence": 0.95,
    },
    {
        "intent": "day.current",
        "patterns": ["what day", "today day"],
        "type": "contains_any",
        "handler": _day_reply,
        "category": "date_time",
        "confidence": 0.95,
    },
    {
        "intent": "week.current",
        "patterns": ["week number", "current week"],
        "type": "contains_any",
        "handler": _week_reply,
        "category": "date_time",
        "confidence": 0.9,
    },
    {
        "intent": "month.current",
        "patterns": ["what month", "current month"],
        "type": "contains_any",
        "handler": _month_reply,
        "category": "date_time",
        "confidence": 0.9,
    },
    {
        "intent": "year.current",
        "patterns": ["what year", "current year"],
        "type": "contains_any",
        "handler": _year_reply,
        "category": "date_time",
        "confidence": 0.9,
    },
    {
        "intent": "weather.current",
        "patterns": [
            "weather",
            "what is the weather",
            "today weather",
            "weather today",
            "weather in",
            "forecast in",
        ],
        "type": "weather",
        "handler": get_weather_report,
        "category": "weather",
        "confidence": 0.96,
    },
    {
        "intent": "brief.daily",
        "patterns": ["daily brief", "morning brief", "brief me", "status report"],
        "type": "exact",
        "handler": lambda command: build_brief_details(),
        "category": "briefing",
        "confidence": 0.98,
    },
    {
        "intent": "dashboard.report",
        "patterns": ["dashboard", "status center", "my day summary", "full report"],
        "type": "exact",
        "handler": lambda command: build_dashboard_report(),
        "category": "dashboard",
        "confidence": 0.98,
    },
    {
        "intent": "notes.add",
        "patterns": ["take a note", "save this idea", "save note", "add note", "note this"],
        "type": "startswith",
        "handler": add_note,
        "category": "notes",
        "confidence": 0.98,
    },
    {
        "intent": "notes.list",
        "patterns": ["list notes", "show notes", "my notes"],
        "type": "exact",
        "handler": lambda command: list_notes(),
        "category": "notes",
        "confidence": 0.98,
    },
    {
        "intent": "notes.delete",
        "patterns": ["delete note"],
        "type": "startswith",
        "handler": delete_note,
        "category": "notes",
        "confidence": 0.98,
    },
    {
        "intent": "profile.summary",
        "patterns": [
            "tell me about myself",
            "summarize my profile",
            "my profile summary",
            "who am i really",
        ],
        "type": "exact",
        "handler": lambda command: build_profile_summary(),
        "category": "profile",
        "confidence": 0.98,
    },
    {
        "intent": "profile.focus",
        "patterns": [
            "what should i focus on",
            "what should i do next",
            "what is my focus",
            "guide my focus",
        ],
        "type": "exact",
        "handler": lambda command: build_focus_suggestion(),
        "category": "profile",
        "confidence": 0.98,
    },
    {
        "intent": "profile.snapshot",
        "patterns": [
            "personal snapshot",
            "tell me my habits",
            "summarize my personal details",
        ],
        "type": "exact",
        "handler": lambda command: build_personal_snapshot(),
        "category": "profile",
        "confidence": 0.97,
    },
    {
        "intent": "profile.nudge",
        "patterns": [
            "give me a suggestion",
            "give me a nudge",
            "motivate me",
            "what should i do now",
            "any suggestion for me",
        ],
        "type": "exact",
        "handler": lambda command: build_proactive_nudge(),
        "category": "profile",
        "confidence": 0.97,
    },
    {
        "intent": "window.active_app",
        "patterns": [
            "what app am i using",
            "which app am i using",
            "what application is open",
        ],
        "type": "exact",
        "handler": lambda command: get_active_app_name(),
        "category": "window_context",
        "confidence": 0.97,
    },
    {
        "intent": "window.active_title",
        "patterns": [
            "what window is open",
            "what is the current window",
            "what is my current window",
        ],
        "type": "exact",
        "handler": lambda command: get_active_window_title(),
        "category": "window_context",
        "confidence": 0.97,
    },
    {
        "intent": "window.describe",
        "patterns": [
            "what am i seeing",
            "what am i looking at",
            "describe my screen",
            "describe active window",
        ],
        "type": "exact",
        "handler": lambda command: summarize_active_window(),
        "category": "window_context",
        "confidence": 0.97,
    },
    {
        "intent": "window.browser",
        "patterns": [
            "am i in browser",
            "what tab is open",
            "summarize this page",
            "which tab is open",
        ],
        "type": "exact",
        "handler": lambda command: summarize_if_browser(),
        "category": "window_context",
        "confidence": 0.96,
    },
    {
        "intent": "app.browser.summary",
        "patterns": [
            "summarize current browser page",
            "read current browser page",
            "summarize browser page",
        ],
        "type": "exact",
        "handler": lambda command: summarize_browser_page(),
        "category": "app_intelligence",
        "confidence": 0.96,
    },
    {
        "intent": "window.editor",
        "patterns": [
            "am i in vscode",
            "what file is open",
            "am i coding now",
            "which file is open",
        ],
        "type": "exact",
        "handler": lambda command: summarize_if_code_editor(),
        "category": "window_context",
        "confidence": 0.96,
    },
    {
        "intent": "app.editor.summary",
        "patterns": [
            "summarize current code editor",
            "summarize current file",
            "read current file context",
        ],
        "type": "exact",
        "handler": lambda command: summarize_code_editor(),
        "category": "app_intelligence",
        "confidence": 0.96,
    },
    {
        "intent": "window.explorer",
        "patterns": [
            "am i in file explorer",
            "which folder is open",
            "what folder is open",
        ],
        "type": "exact",
        "handler": lambda command: summarize_if_file_explorer(),
        "category": "window_context",
        "confidence": 0.96,
    },
    {
        "intent": "app.explorer.summary",
        "patterns": [
            "summarize current folder",
            "read current folder",
            "what folder am i in",
        ],
        "type": "exact",
        "handler": lambda command: summarize_current_folder(),
        "category": "app_intelligence",
        "confidence": 0.96,
    },
    {
        "intent": "app.whatsapp.summary",
        "patterns": [
            "summarize whatsapp",
            "what chat am i on",
            "read whatsapp screen",
        ],
        "type": "exact",
        "handler": lambda command: summarize_whatsapp_context(),
        "category": "app_intelligence",
        "confidence": 0.95,
    },
    {
        "intent": "window.describe_app",
        "patterns": [
            "describe current app",
            "tell me current app",
        ],
        "type": "exact",
        "handler": lambda command: describe_active_window(),
        "category": "window_context",
        "confidence": 0.96,
    },
    {
        "intent": "reminders.urgent",
        "patterns": ["check reminders", "due reminders", "urgent reminders"],
        "type": "exact",
        "handler": lambda command: build_due_reminder_alert(),
        "category": "briefing",
        "confidence": 0.98,
    },
    {
        "intent": "tasks.add",
        "patterns": ["add task"],
        "type": "startswith",
        "handler": add_task,
        "category": "tasks",
        "confidence": 0.98,
    },
    {
        "intent": "tasks.list",
        "patterns": ["show tasks", "list tasks", "my tasks"],
        "type": "exact",
        "handler": lambda command: list_tasks(),
        "category": "tasks",
        "confidence": 0.98,
    },
    {
        "intent": "tasks.complete",
        "patterns": ["complete task"],
        "type": "startswith",
        "handler": complete_task,
        "category": "tasks",
        "confidence": 0.98,
    },
    {
        "intent": "tasks.delete",
        "patterns": ["delete task"],
        "type": "startswith",
        "handler": delete_task,
        "category": "tasks",
        "confidence": 0.98,
    },
    {
        "intent": "reminders.add",
        "patterns": ["remind me to"],
        "type": "startswith",
        "handler": add_reminder,
        "category": "reminders",
        "confidence": 0.98,
    },
    {
        "intent": "reminders.list",
        "patterns": ["show reminders", "list reminders", "my reminders"],
        "type": "exact",
        "handler": lambda command: list_reminders(),
        "category": "reminders",
        "confidence": 0.98,
    },
    {
        "intent": "reminders.delete",
        "patterns": ["delete reminder"],
        "type": "startswith",
        "handler": delete_reminder,
        "category": "reminders",
        "confidence": 0.98,
    },
    {
        "intent": "modes.list",
        "patterns": ["list modes", "show modes", "what modes do you have"],
        "type": "exact",
        "handler": lambda command: list_routines(),
        "category": "modes",
        "confidence": 0.98,
    },
    {
        "intent": "modes.custom.list",
        "patterns": ["list custom modes", "show custom modes", "my custom modes"],
        "type": "exact",
        "handler": lambda command: list_custom_routines(),
        "category": "modes",
        "confidence": 0.98,
    },
    {
        "intent": "modes.custom.create",
        "patterns": ["create mode"],
        "type": "startswith",
        "handler": create_custom_routine,
        "category": "modes",
        "confidence": 0.98,
    },
    {
        "intent": "modes.custom.delete",
        "patterns": ["delete mode"],
        "type": "startswith",
        "handler": delete_custom_routine,
        "category": "modes",
        "confidence": 0.98,
    },
    {
        "intent": "modes.start",
        "patterns": ["start"],
        "type": "mode_start",
        "handler": run_routine,
        "category": "modes",
        "confidence": 0.95,
    },
]


def _matches(command, entry):
    match_type = entry["type"]
    patterns = entry["patterns"]

    if match_type == "exact":
        return command in patterns

    if match_type == "startswith":
        return any(command.startswith(pattern) for pattern in patterns)

    if match_type == "contains_any":
        return any(pattern in command for pattern in patterns)

    if match_type == "mode_start":
        return command.startswith("start") and "mode" in command

    if match_type == "weather":
        return command in patterns[:4] or command.startswith("weather in") or command.startswith("forecast in")

    return False


def resolve_intent(command):
    command = command.lower().strip()

    for entry in COMMAND_REGISTRY:
        if _matches(command, entry):
            return {
                "intent": entry["intent"],
                "category": entry["category"],
                "confidence": entry["confidence"],
                "handler": entry["handler"],
            }

    return None


def try_handle_intent(command):
    intent = resolve_intent(command)
    if not intent:
        return {"handled": False}

    reply = intent["handler"](command)
    if reply is None:
        return {"handled": False}

    result = _reply_text(reply)
    result["intent"] = intent["intent"]
    result["category"] = intent["category"]
    result["confidence"] = intent["confidence"]
    return result
