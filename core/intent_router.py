import datetime

from modules.briefing_module import build_brief_details, build_due_reminder_alert
from modules.calendar_module import get_date, get_day, get_period, get_time
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
        "patterns": ["time now", "current time", "what time", "what is time"],
        "type": "contains_any",
        "handler": _time_reply,
        "category": "date_time",
        "confidence": 0.95,
    },
    {
        "intent": "date.current",
        "patterns": ["today date", "current date", "what is date"],
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
        "intent": "brief.daily",
        "patterns": ["daily brief", "morning brief", "brief me", "status report"],
        "type": "exact",
        "handler": lambda command: build_brief_details(),
        "category": "briefing",
        "confidence": 0.98,
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
