import datetime
import json
import os
import re

from brain.memory_engine import CONTACT_REFERENCE_ALIASES, load_memory
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


def _extract_priority(command):
    normalized = (command or "").lower()
    if any(phrase in normalized for phrase in ["high priority", "priority high", "urgent task", "important task"]):
        return "high"
    if any(phrase in normalized for phrase in ["medium priority", "priority medium"]):
        return "medium"
    if any(phrase in normalized for phrase in ["low priority", "priority low"]):
        return "low"
    return "normal"


def _extract_category(command):
    normalized = (command or "").lower()
    match = re.search(r"\b([a-z0-9_-]+)\s+category\b", normalized)
    if match:
        return match.group(1)

    match = re.search(r"\bcategory\s+([a-z0-9_-]+)\b", normalized)
    if match:
        return match.group(1)

    known_categories = ["work", "study", "personal", "health", "finance", "family"]
    for category in known_categories:
        if f"{category} task" in normalized or f"{category} category" in normalized:
            return category
    return ""


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


def _format_due_value(reminder):
    due_at = reminder.get("due_at")
    if due_at:
        try:
            dt = datetime.datetime.fromisoformat(due_at)
            return dt.strftime("%d %B %Y %I:%M %p")
        except ValueError:
            pass

    return _format_due_date(reminder.get("due_date"))


def _today():
    return datetime.date.today()


def _parse_iso_date(date_str):
    if not date_str:
        return None

    try:
        return datetime.date.fromisoformat(date_str)
    except ValueError:
        return None


def _parse_iso_datetime(date_str):
    if not date_str:
        return None

    try:
        return datetime.datetime.fromisoformat(date_str)
    except ValueError:
        return None


def _latest_pending_task(tasks):
    pending_tasks = [task for task in tasks if not task.get("completed")]
    if not pending_tasks:
        return None
    return max(pending_tasks, key=lambda task: task.get("created_at", ""))


def _latest_item(items):
    if not items:
        return None
    return max(items, key=lambda item: item.get("created_at", ""))


def _parse_snooze_target(command):
    latest_requested = "latest reminder" in command
    if latest_requested:
        return {"latest": True, "index": None}

    match = re.search(r"reminder\s+(\d+)", command)
    if match:
        return {"latest": False, "index": int(match.group(1)) - 1}

    return {"latest": False, "index": None}


def _parse_snooze_days(command):
    match = re.search(r"by\s+(\d+)\s*(day|days|week|weeks|month|months)", command)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).lower()

    if "week" in unit:
        return amount * 7
    if "month" in unit:
        return amount * 30
    return amount


def _parse_snooze_delta(command):
    match = re.search(
        r"by\s+(\d+)\s*(minute|minutes|hour|hours|day|days|week|weeks|month|months)",
        command,
    )
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).lower()

    if "minute" in unit:
        return datetime.timedelta(minutes=amount)
    if "hour" in unit:
        return datetime.timedelta(hours=amount)
    if "week" in unit:
        return datetime.timedelta(days=amount * 7)
    if "month" in unit:
        return datetime.timedelta(days=amount * 30)
    return datetime.timedelta(days=amount)


def _extract_relative_due_datetime(command):
    match = re.search(
        r"\bin\s+(\d+)\s*(minute|minutes|hour|hours|day|days|week|weeks)\b",
        command,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).lower()
    now = datetime.datetime.now()

    if "minute" in unit:
        return now + datetime.timedelta(minutes=amount)
    if "hour" in unit:
        return now + datetime.timedelta(hours=amount)
    if "week" in unit:
        return now + datetime.timedelta(days=amount * 7)
    return now + datetime.timedelta(days=amount)


def _extract_due_time(command):
    match = re.search(
        r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
        command,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = (match.group(3) or "").lower()

    if meridiem:
        if hour == 12:
            hour = 0
        if meridiem == "pm":
            hour += 12

    if hour > 23 or minute > 59:
        return None

    return datetime.time(hour=hour, minute=minute)


def _get_reminder_datetime(reminder):
    due_at = _parse_iso_datetime(reminder.get("due_at"))
    if due_at:
        return due_at

    due_date = _parse_iso_date(reminder.get("due_date"))
    if due_date:
        return datetime.datetime.combine(due_date, datetime.time(hour=9, minute=0))

    return None


def _extract_title_text(command, prefixes):
    for prefix in prefixes:
        if command.startswith(prefix):
            return _clean_text(command[len(prefix):])
    return ""


def _match_by_title(items, title_text, *, pending_only=False):
    query = _clean_text(title_text).lower()
    if not query:
        return None

    candidates = []
    for item in items:
        if pending_only and item.get("completed"):
            continue

        title = item.get("title", "")
        normalized = _clean_text(title).lower()
        if not normalized:
            continue

        score = 0
        if normalized == query:
            score = 100
        elif normalized.startswith(query):
            score = 90
        elif query in normalized:
            score = 80
        else:
            query_words = [word for word in query.split() if word]
            overlap = sum(1 for word in query_words if word in normalized)
            if overlap:
                score = overlap * 10

        if score:
            candidates.append((score, item))

    if not candidates:
        return None

    candidates.sort(key=lambda entry: (entry[0], entry[1].get("created_at", "")), reverse=True)
    return candidates[0][1]


def _remove_date_phrases(text):
    patterns = [
        r"\b(today|tomorrow|yesterday|next week|last week|next month|last month|next year|last year)\b",
        r"\bin\s+\d+\s*(minute|minutes|hour|hours|day|days|week|weeks)\b",
        r"\bon\s+\d{1,2}\s+[a-zA-Z]+\s+\d{4}\b",
        r"\b\d{1,2}\s+[a-zA-Z]+\s+\d{4}\b",
        r"\bon\s+\d{1,2}\s+\d{1,2}\s+\d{4}\b",
        r"\b\d{1,2}\s+\d{1,2}\s+\d{4}\b",
        r"\bat\s+\d{1,2}(?::\d{2})?\s*(am|pm)?\b",
    ]

    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    return _clean_text(cleaned)


def _extract_recurrence(command):
    normalized = (command or "").lower()
    if "every day" in normalized or "daily" in normalized:
        return "daily"

    weekday_match = re.search(
        r"\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        normalized,
    )
    if weekday_match:
        return f"weekly:{weekday_match.group(1)}"

    if "every week" in normalized or "weekly" in normalized:
        return "weekly"

    if "every month" in normalized or "monthly" in normalized:
        return "monthly"

    return None


def _strip_recurrence_phrases(text):
    cleaned = re.sub(
        r"\bevery\s+(day|week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\b(daily|weekly|monthly)\b", " ", cleaned, flags=re.IGNORECASE)
    return _clean_text(cleaned)


def _format_recurrence(recurrence):
    if not recurrence:
        return ""
    if recurrence == "daily":
        return " (recurs daily)"
    if recurrence == "weekly":
        return " (recurs weekly)"
    if recurrence == "monthly":
        return " (recurs monthly)"
    if recurrence.startswith("weekly:"):
        return f" (recurs every {recurrence.split(':', 1)[1]})"
    return f" ({recurrence})"


def _iter_contact_candidates():
    memory = load_memory()
    seen = set()

    def add_candidate(name, aliases=None):
        clean_name = _clean_text(name or "")
        if not clean_name:
            return
        normalized = clean_name.lower()
        if normalized in seen:
            return
        seen.add(normalized)
        yield {
            "name": clean_name,
            "aliases": {normalized, *{_clean_text(alias).lower() for alias in (aliases or []) if alias}},
        }

    personal = memory.get("personal", {})
    contact = personal.get("contact", {})
    family = personal.get("family", {})
    friends = personal.get("friends", {})

    for alias, (base_path, field_name) in CONTACT_REFERENCE_ALIASES.items():
        parts = base_path.split(".")
        value = personal
        if parts[0] == "personal":
            parts = parts[1:]
        try:
            for part in parts:
                if part.isdigit():
                    value = value[int(part)]
                else:
                    value = value.get(part, {})
            if isinstance(value, dict):
                name = value.get(field_name)
            else:
                name = None
        except Exception:
            name = None
        if name:
            yield from add_candidate(name, aliases=[alias])

    for friend in friends.get("close_friends", []):
        aliases = []
        if friend.get("nickname"):
            aliases.append(friend.get("nickname"))
        yield from add_candidate(friend.get("name"), aliases=aliases)

    emergency = contact.get("emergency_contact", {})
    yield from add_candidate(emergency.get("name"), aliases=["emergency contact", "my emergency contact"])

    for person_key in ["father", "mother"]:
        person = family.get(person_key, {})
        yield from add_candidate(person.get("name"), aliases=[person_key, f"my {person_key}"])

    for sibling in family.get("siblings", []):
        aliases = ["sister", "my sister"]
        if sibling.get("nickname"):
            aliases.append(sibling.get("nickname"))
        yield from add_candidate(sibling.get("name"), aliases=aliases)


def _resolve_contact_target(target_text):
    normalized = _clean_text(target_text).lower()
    if not normalized or normalized in {"me", "myself"}:
        return None

    candidates = list(_iter_contact_candidates())
    for candidate in candidates:
        if normalized in candidate["aliases"]:
            return candidate["name"]

    for candidate in candidates:
        if normalized == candidate["name"].lower():
            return candidate["name"]

    for candidate in candidates:
        if normalized in candidate["name"].lower():
            return candidate["name"]

    return None


def _extract_due_date(command):
    date_obj = get_relative_base(command) or extract_specific_date(command)
    if not date_obj:
        return None

    if isinstance(date_obj, datetime.datetime):
        date_obj = date_obj.date()

    return date_obj.isoformat()


def _extract_due_datetime(command):
    relative_due = _extract_relative_due_datetime(command)
    if relative_due is not None:
        return relative_due.replace(second=0, microsecond=0)

    due_date = get_relative_base(command) or extract_specific_date(command)
    due_time = _extract_due_time(command)

    if isinstance(due_date, datetime.datetime):
        due_date = due_date.date()

    if due_date is None and due_time is None:
        return None

    if due_date is None:
        due_date = datetime.date.today()

    if due_time is None:
        due_time = datetime.time(hour=9, minute=0)

    return datetime.datetime.combine(due_date, due_time)


def add_task(command):
    recurrence = _extract_recurrence(command)
    priority = _extract_priority(command)
    category = _extract_category(command)
    task_text = _strip_recurrence_phrases(_clean_text(command.replace("add task", "", 1)))
    task_text = re.sub(r"\b(high|medium|low)\s+priority\b", " ", task_text, flags=re.IGNORECASE)
    task_text = re.sub(r"\bpriority\s+(high|medium|low)\b", " ", task_text, flags=re.IGNORECASE)
    task_text = re.sub(r"\burgent task\b", " ", task_text, flags=re.IGNORECASE)
    task_text = re.sub(r"\bimportant task\b", " ", task_text, flags=re.IGNORECASE)
    task_text = re.sub(r"\b[a-z0-9_-]+\s+category\b", " ", task_text, flags=re.IGNORECASE)
    task_text = re.sub(r"\bcategory\s+[a-z0-9_-]+\b", " ", task_text, flags=re.IGNORECASE)
    task_text = re.sub(r"\b(work|study|personal|health|finance|family)\s+task\b", " ", task_text, flags=re.IGNORECASE)
    task_text = _clean_text(task_text)
    if not task_text:
        return "Tell me what task you want to add."

    data = _load_data()
    data["tasks"].append(
        {
            "title": task_text,
            "completed": False,
            "recurrence": recurrence,
            "priority": priority,
            "category": category,
            "created_at": datetime.datetime.now().isoformat(),
        }
    )
    _save_data(data)
    extras = []
    if priority != "normal":
        extras.append(f"{priority} priority")
    if category:
        extras.append(f"{category} category")
    extra_text = f" ({', '.join(extras)})" if extras else ""
    if recurrence:
        return f"Recurring task added{_format_recurrence(recurrence)}{extra_text}: {task_text}"
    return f"Task added{extra_text}: {task_text}"


def list_tasks():
    data = _load_data()
    tasks = data["tasks"]

    if not tasks:
        return "You have no tasks right now."

    lines = []
    for index, task in enumerate(tasks, start=1):
        status = "done" if task.get("completed") else "pending"
        metadata = []
        if task.get("priority") and task.get("priority") != "normal":
            metadata.append(task.get("priority"))
        if task.get("category"):
            metadata.append(task.get("category"))
        meta_text = f" [{', '.join(metadata)}]" if metadata else ""
        lines.append(
            f"{index}. {task.get('title', 'Untitled task')} - {status}{meta_text}{_format_recurrence(task.get('recurrence'))}"
        )

    return "Your tasks are: " + " | ".join(lines)


def list_high_priority_tasks():
    data = _load_data()
    tasks = [task for task in data["tasks"] if task.get("priority") == "high" and not task.get("completed")]
    if not tasks:
        return "You do not have any high priority pending tasks right now."
    lines = [task.get("title", "Untitled task") for task in tasks[:10]]
    return "Your high priority tasks are: " + " | ".join(lines)


def list_tasks_by_category(command):
    match = re.search(r"(?:tasks|task)\s+(?:in|for|under)\s+([a-z0-9_-]+)", command)
    if not match:
        match = re.search(r"([a-z0-9_-]+)\s+tasks", command)
    if not match:
        return "Tell me which task category you want to see."

    category = match.group(1).strip().lower()
    data = _load_data()
    tasks = [task for task in data["tasks"] if (task.get("category") or "").lower() == category]
    if not tasks:
        return f"You do not have any tasks in the {category} category right now."

    lines = []
    for task in tasks[:10]:
        status = "done" if task.get("completed") else "pending"
        priority = task.get("priority", "normal")
        suffix = f" ({priority})" if priority != "normal" else ""
        lines.append(f"{task.get('title', 'Untitled task')} - {status}{suffix}")
    return f"Your {category} tasks are: " + " | ".join(lines)


def latest_task():
    data = _load_data()
    task = _latest_pending_task(data["tasks"])

    if not task:
        return "You have no pending tasks right now."

    return f"Your latest pending task is: {task.get('title', 'Untitled task')}"


def due_today_summary():
    data = _load_data()
    today = _today()
    due_today = []

    for reminder in data["reminders"]:
        due_datetime = _get_reminder_datetime(reminder)
        if due_datetime and due_datetime.date() == today:
            due_today.append(
                f"{reminder.get('title', 'Untitled reminder')} ({_format_due_value(reminder)})"
            )

    pending_tasks = [task.get("title", "Untitled task") for task in data["tasks"] if not task.get("completed")]

    parts = []
    if due_today:
        parts.append("Reminders due today: " + " | ".join(due_today))
    if pending_tasks:
        parts.append("Pending tasks: " + " | ".join(pending_tasks[:5]))

    if not parts:
        return "You have nothing due today."

    return " | ".join(parts)


def overdue_items():
    data = _load_data()
    now = datetime.datetime.now()
    overdue_reminders = []

    for reminder in data["reminders"]:
        due_datetime = _get_reminder_datetime(reminder)
        if due_datetime and due_datetime < now:
            overdue_reminders.append(
                f"{reminder.get('title', 'Untitled reminder')} ({_format_due_value(reminder)})"
            )

    if not overdue_reminders:
        return "You have no overdue reminders right now."

    return "Your overdue items are: " + " | ".join(overdue_reminders)


def complete_task(command):
    index = _parse_index(command, "complete task")
    if index is None:
        return "Tell me the task number to complete."

    data = _load_data()
    tasks = data["tasks"]

    if index < 0 or index >= len(tasks):
        return "That task number does not exist."

    tasks[index]["completed"] = True
    tasks[index]["completed_at"] = datetime.datetime.now().isoformat()
    _save_data(data)
    return f"Completed task {index + 1}: {tasks[index]['title']}"


def complete_latest_task():
    data = _load_data()
    task = _latest_pending_task(data["tasks"])

    if not task:
        return "You have no pending tasks to complete."

    task["completed"] = True
    task["completed_at"] = datetime.datetime.now().isoformat()
    _save_data(data)
    return f"Completed latest task: {task.get('title', 'Untitled task')}"


def complete_all_tasks():
    data = _load_data()
    tasks = data["tasks"]
    pending_tasks = [task for task in tasks if not task.get("completed")]

    if not pending_tasks:
        return "You do not have any pending tasks right now."

    for task in pending_tasks:
        task["completed"] = True
        task["completed_at"] = datetime.datetime.now().isoformat()

    _save_data(data)
    return f"Completed all pending tasks: {len(pending_tasks)} task(s)."


def complete_task_by_title(command):
    title_text = _extract_title_text(command, ["complete task titled", "complete task about", "complete task"])
    if not title_text:
        return "Tell me which task title you want to complete."

    data = _load_data()
    task = _match_by_title(data["tasks"], title_text, pending_only=True)

    if not task:
        return f"I could not find a pending task matching '{title_text}'."

    task["completed"] = True
    task["completed_at"] = datetime.datetime.now().isoformat()
    _save_data(data)
    return f"Completed task: {task.get('title', 'Untitled task')}"


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


def delete_latest_task():
    data = _load_data()
    tasks = data["tasks"]
    task = _latest_item(tasks)

    if not task:
        return "You have no tasks to delete."

    tasks.remove(task)
    _save_data(data)
    return f"Deleted latest task: {task.get('title', 'Untitled task')}"


def delete_completed_tasks():
    data = _load_data()
    tasks = data["tasks"]
    completed_tasks = [task for task in tasks if task.get("completed")]

    if not completed_tasks:
        return "You do not have any completed tasks to delete."

    data["tasks"] = [task for task in tasks if not task.get("completed")]
    _save_data(data)
    return f"Deleted completed tasks: {len(completed_tasks)} task(s)."


def mark_all_tasks_pending():
    data = _load_data()
    tasks = data["tasks"]
    completed_tasks = [task for task in tasks if task.get("completed")]

    if not tasks:
        return "You do not have any tasks right now."

    if not completed_tasks:
        return "All tasks are already pending."

    for task in completed_tasks:
        task["completed"] = False
        task["completed_at"] = None

    _save_data(data)
    return f"Marked {len(completed_tasks)} task(s) as pending."


def mark_all_tasks_done():
    return complete_all_tasks()


def delete_task_by_title(command):
    title_text = _extract_title_text(command, ["delete task titled", "delete task about", "remove task titled", "remove task about"])
    if not title_text:
        return "Tell me which task title you want to delete."

    data = _load_data()
    tasks = data["tasks"]
    task = _match_by_title(tasks, title_text)

    if not task:
        return f"I could not find a task matching '{title_text}'."

    tasks.remove(task)
    _save_data(data)
    return f"Deleted task: {task.get('title', 'Untitled task')}"


def add_reminder(command):
    recurrence = _extract_recurrence(command)
    due_datetime = _extract_due_datetime(command)
    due_date = due_datetime.date().isoformat() if due_datetime else _extract_due_date(command)
    reminder_text = command
    for prefix in ["remind me to", "remind me every"]:
        if command.startswith(prefix):
            reminder_text = command.replace(prefix, "", 1)
            break
    reminder_text = _strip_recurrence_phrases(_remove_date_phrases(reminder_text))

    if not reminder_text:
        return "Tell me what you want me to remind you about."

    data = _load_data()
    data["reminders"].append(
        {
            "title": reminder_text,
            "due_date": due_date,
            "due_at": due_datetime.isoformat(timespec="minutes") if due_datetime else None,
            "recurrence": recurrence,
            "created_at": datetime.datetime.now().isoformat(),
        }
    )
    _save_data(data)

    if due_datetime:
        prefix = "Recurring reminder added" if recurrence else "Reminder added"
        return f"{prefix}{_format_recurrence(recurrence)} for {due_datetime.strftime('%d %B %Y %I:%M %p')}: {reminder_text}"
    if due_date:
        prefix = "Recurring reminder added" if recurrence else "Reminder added"
        return f"{prefix}{_format_recurrence(recurrence)} for {_format_due_date(due_date)}: {reminder_text}"
    return f"Reminder added: {reminder_text}"


def add_contact_reminder(command):
    recurrence = _extract_recurrence(command)
    match = re.match(
        r"^(?:remind|set reminder for)\s+(.+?)\s+(about|to)\s+(.+)$",
        command,
        flags=re.IGNORECASE,
    )
    if not match:
        return "Tell me which contact you want the reminder to be about."

    target_text = _clean_text(match.group(1))
    connector = match.group(2).lower()
    reminder_body = _remove_date_phrases(_clean_text(match.group(3)))
    if not target_text or not reminder_body:
        return "Tell me the contact and what you want to be reminded about."

    contact_name = _resolve_contact_target(target_text)
    if not contact_name:
        return f"I could not find a saved contact matching {target_text} in memory."

    due_datetime = _extract_due_datetime(command)
    due_date = due_datetime.date().isoformat() if due_datetime else _extract_due_date(command)
    reminder_text = (
        f"{contact_name} - {reminder_body}"
        if connector == "about"
        else f"{contact_name} - to {reminder_body}"
    )

    data = _load_data()
    data["reminders"].append(
        {
            "title": reminder_text,
            "due_date": due_date,
            "due_at": due_datetime.isoformat(timespec="minutes") if due_datetime else None,
            "recurrence": recurrence,
            "created_at": datetime.datetime.now().isoformat(),
        }
    )
    _save_data(data)

    if due_datetime:
        prefix = "Recurring reminder added" if recurrence else "Reminder added"
        return f"{prefix}{_format_recurrence(recurrence)} for {due_datetime.strftime('%d %B %Y %I:%M %p')}: {reminder_text}"
    if due_date:
        prefix = "Recurring reminder added" if recurrence else "Reminder added"
        return f"{prefix}{_format_recurrence(recurrence)} for {_format_due_date(due_date)}: {reminder_text}"
    return f"Reminder added: {reminder_text}"


def list_reminders():
    data = _load_data()
    reminders = data["reminders"]

    if not reminders:
        return "You have no reminders right now."

    lines = []
    for index, reminder in enumerate(reminders, start=1):
        due = _format_due_value(reminder)
        lines.append(
            f"{index}. {reminder.get('title', 'Untitled reminder')} - {due}{_format_recurrence(reminder.get('recurrence'))}"
        )

    return "Your reminders are: " + " | ".join(lines)


def latest_reminder():
    data = _load_data()
    reminder = _latest_item(data["reminders"])

    if not reminder:
        return "You have no reminders right now."

    due = _format_due_value(reminder)
    return f"Your latest reminder is: {reminder.get('title', 'Untitled reminder')} - {due}{_format_recurrence(reminder.get('recurrence'))}"


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


def delete_latest_reminder():
    data = _load_data()
    reminders = data["reminders"]
    reminder = _latest_item(reminders)

    if not reminder:
        return "You have no reminders to delete."

    reminders.remove(reminder)
    _save_data(data)
    return f"Deleted latest reminder: {reminder.get('title', 'Untitled reminder')}"


def clear_all_reminders():
    data = _load_data()
    reminders = data["reminders"]

    if not reminders:
        return "You do not have any reminders to clear."

    count = len(reminders)
    data["reminders"] = []
    _save_data(data)
    return f"Cleared all reminders: {count} reminder(s)."


def clear_overdue_reminders():
    data = _load_data()
    reminders = data["reminders"]
    now = datetime.datetime.now()
    overdue_reminders = [reminder for reminder in reminders if (_get_reminder_datetime(reminder) and _get_reminder_datetime(reminder) < now)]

    if not overdue_reminders:
        return "You do not have any overdue reminders to clear."

    data["reminders"] = [
        reminder
        for reminder in reminders
        if not (_get_reminder_datetime(reminder) and _get_reminder_datetime(reminder) < now)
    ]
    _save_data(data)
    return f"Cleared overdue reminders: {len(overdue_reminders)} reminder(s)."


def delete_reminder_by_title(command):
    title_text = _extract_title_text(
        command,
        ["delete reminder about", "delete reminder titled", "remove reminder about", "remove reminder titled"],
    )
    if not title_text:
        return "Tell me which reminder title you want to delete."

    data = _load_data()
    reminders = data["reminders"]
    reminder = _match_by_title(reminders, title_text)

    if not reminder:
        return f"I could not find a reminder matching '{title_text}'."

    reminders.remove(reminder)
    _save_data(data)
    return f"Deleted reminder: {reminder.get('title', 'Untitled reminder')}"


def rename_reminder(command):
    match = re.match(
        r"^(?:rename|update|change)\s+reminder\s+(?:about|titled)\s+(.+?)\s+to\s+(.+)$",
        command,
    )
    if not match:
        return "Tell me which reminder you want to rename and the new title."

    current_title = _clean_text(match.group(1))
    new_title = _clean_text(match.group(2))
    if not current_title or not new_title:
        return "I need both the current reminder title and the new title."

    data = _load_data()
    reminder = _match_by_title(data["reminders"], current_title)
    if not reminder:
        return f"I could not find a reminder matching '{current_title}'."

    reminder["title"] = new_title
    _save_data(data)
    return f"Reminder renamed to: {new_title}"


def reschedule_reminder(command):
    match = re.match(
        r"^(?:reschedule|update|change)\s+reminder\s+(?:about|titled)\s+(.+?)\s+to\s+(.+)$",
        command,
    )
    if not match:
        return "Tell me which reminder you want to reschedule and the new time."

    title_text = _clean_text(match.group(1))
    schedule_text = _clean_text(match.group(2))
    if not title_text or not schedule_text:
        return "I need the reminder title and the new schedule."

    data = _load_data()
    reminder = _match_by_title(data["reminders"], title_text)
    if not reminder:
        return f"I could not find a reminder matching '{title_text}'."

    due_datetime = _extract_due_datetime(schedule_text)
    due_date = due_datetime.date().isoformat() if due_datetime else _extract_due_date(schedule_text)

    if due_datetime is None and due_date is None:
        return "Tell me the new date or time for that reminder."

    reminder["due_date"] = due_date
    reminder["due_at"] = due_datetime.isoformat(timespec="minutes") if due_datetime else None
    _save_data(data)
    return f"Reminder rescheduled to {_format_due_value(reminder)}."


def snooze_reminder(command):
    target = _parse_snooze_target(command)
    snooze_delta = _parse_snooze_delta(command)

    if snooze_delta is None:
        return "Tell me how many minutes, hours, days, weeks, or months to snooze the reminder by."

    data = _load_data()
    reminders = data["reminders"]

    if not reminders:
        return "You have no reminders to snooze."

    if target["latest"]:
        reminder = _latest_item(reminders)
        reminder_index = reminders.index(reminder) if reminder else None
    elif "about" in command or "titled" in command:
        title_text = _extract_title_text(
            command,
            ["snooze reminder about", "snooze reminder titled", "snooze latest reminder about"],
        )
        reminder = _match_by_title(reminders, title_text)
        reminder_index = reminders.index(reminder) if reminder else None
    else:
        reminder_index = target["index"]
        reminder = reminders[reminder_index] if reminder_index is not None and 0 <= reminder_index < len(reminders) else None

    if reminder is None:
        return "That reminder does not exist."

    base_datetime = _get_reminder_datetime(reminder) or datetime.datetime.now()
    new_datetime = base_datetime + snooze_delta
    reminder["due_at"] = new_datetime.isoformat(timespec="minutes")
    reminder["due_date"] = new_datetime.date().isoformat()
    _save_data(data)

    return (
        f"Snoozed reminder '{reminder.get('title', 'Untitled reminder')}' "
        f"to {_format_due_value(reminder)}."
    )
