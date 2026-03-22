import datetime
import json
import os
import re

from modules.calendar_module import extract_specific_date, get_relative_base

DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "tasks.json",
)


def _default_data():
    return {"tasks": [], "reminders": []}


def _load_data():
    if not os.path.exists(DATA_FILE):
        return _default_data()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return _default_data()

    if "tasks" not in data:
        data["tasks"] = []
    if "reminders" not in data:
        data["reminders"] = []

    return data


def get_task_data():
    return _load_data()


def _save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def _clean_text(value):
    return re.sub(r"\s+", " ", value).strip(" ,.-")


def _parse_index(command, prefix):
    raw = command.replace(prefix, "", 1).strip()
    if not raw.isdigit():
        return None
    return int(raw) - 1


def _format_due_date(date_str):
    if not date_str:
        return "No date"

    try:
        date_obj = datetime.date.fromisoformat(date_str)
    except ValueError:
        return date_str

    return date_obj.strftime("%d %B %Y")


def _remove_date_phrases(text):
    patterns = [
        r"\b(today|tomorrow|yesterday|next week|last week|next month|last month|next year|last year)\b",
        r"\bon\s+\d{1,2}\s+[a-zA-Z]+\s+\d{4}\b",
        r"\b\d{1,2}\s+[a-zA-Z]+\s+\d{4}\b",
        r"\bon\s+\d{1,2}\s+\d{1,2}\s+\d{4}\b",
        r"\b\d{1,2}\s+\d{1,2}\s+\d{4}\b",
    ]

    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    return _clean_text(cleaned)


def _extract_due_date(command):
    date_obj = get_relative_base(command) or extract_specific_date(command)
    if not date_obj:
        return None

    if isinstance(date_obj, datetime.datetime):
        date_obj = date_obj.date()

    return date_obj.isoformat()


def add_task(command):
    task_text = _clean_text(command.replace("add task", "", 1))
    if not task_text:
        return "Tell me what task you want to add."

    data = _load_data()
    data["tasks"].append(
        {
            "title": task_text,
            "completed": False,
            "created_at": datetime.datetime.now().isoformat(),
        }
    )
    _save_data(data)
    return f"Task added: {task_text}"


def list_tasks():
    data = _load_data()
    tasks = data["tasks"]

    if not tasks:
        return "You have no tasks right now."

    lines = []
    for index, task in enumerate(tasks, start=1):
        status = "done" if task.get("completed") else "pending"
        lines.append(f"{index}. {task.get('title', 'Untitled task')} - {status}")

    return "Your tasks are: " + " | ".join(lines)


def complete_task(command):
    index = _parse_index(command, "complete task")
    if index is None:
        return "Tell me the task number to complete."

    data = _load_data()
    tasks = data["tasks"]

    if index < 0 or index >= len(tasks):
        return "That task number does not exist."

    tasks[index]["completed"] = True
    _save_data(data)
    return f"Completed task {index + 1}: {tasks[index]['title']}"


def delete_task(command):
    index = _parse_index(command, "delete task")
    if index is None:
        return "Tell me the task number to delete."

    data = _load_data()
    tasks = data["tasks"]

    if index < 0 or index >= len(tasks):
        return "That task number does not exist."

    removed = tasks.pop(index)
    _save_data(data)
    return f"Deleted task: {removed['title']}"


def add_reminder(command):
    due_date = _extract_due_date(command)
    reminder_text = _remove_date_phrases(command.replace("remind me to", "", 1))

    if not reminder_text:
        return "Tell me what you want me to remind you about."

    data = _load_data()
    data["reminders"].append(
        {
            "title": reminder_text,
            "due_date": due_date,
            "created_at": datetime.datetime.now().isoformat(),
        }
    )
    _save_data(data)

    if due_date:
        return f"Reminder added for {_format_due_date(due_date)}: {reminder_text}"
    return f"Reminder added: {reminder_text}"


def list_reminders():
    data = _load_data()
    reminders = data["reminders"]

    if not reminders:
        return "You have no reminders right now."

    lines = []
    for index, reminder in enumerate(reminders, start=1):
        due = _format_due_date(reminder.get("due_date"))
        lines.append(f"{index}. {reminder.get('title', 'Untitled reminder')} - {due}")

    return "Your reminders are: " + " | ".join(lines)


def delete_reminder(command):
    index = _parse_index(command, "delete reminder")
    if index is None:
        return "Tell me the reminder number to delete."

    data = _load_data()
    reminders = data["reminders"]

    if index < 0 or index >= len(reminders):
        return "That reminder number does not exist."

    removed = reminders.pop(index)
    _save_data(data)
    return f"Deleted reminder: {removed['title']}"
