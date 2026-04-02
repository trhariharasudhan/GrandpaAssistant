import datetime
import json
import os
import re
import uuid

from productivity.event_module import get_event_data
from productivity.task_module import get_task_data
from utils.config import get_setting, update_setting


DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data",
    "nextgen_features.json",
)

VOICE_TRAINER_PRESETS = {
    "quiet": {
        "voice.mode": "normal",
        "voice.wake_match_threshold": 0.64,
        "voice.follow_up_timeout_seconds": 14,
        "voice.follow_up_listen_timeout": 4,
        "voice.follow_up_phrase_time_limit": 6,
        "voice.interrupt_follow_up_seconds": 4,
    },
    "normal": {
        "voice.mode": "sensitive",
        "voice.wake_match_threshold": 0.68,
        "voice.follow_up_timeout_seconds": 12,
        "voice.follow_up_listen_timeout": 3,
        "voice.follow_up_phrase_time_limit": 5,
        "voice.interrupt_follow_up_seconds": 5,
    },
    "noisy": {
        "voice.mode": "noise_cancel",
        "voice.wake_match_threshold": 0.74,
        "voice.follow_up_timeout_seconds": 11,
        "voice.follow_up_listen_timeout": 2,
        "voice.follow_up_phrase_time_limit": 4,
        "voice.interrupt_follow_up_seconds": 6,
    },
}


def _default_data():
    return {
        "habits": [],
        "goals": [],
        "meetings": [],
        "rag_library": {},
        "automation_rules": [],
        "mobile_companion": {
            "enabled": False,
            "device_name": "",
            "history": [],
        },
        "last_day_plan": {
            "created_at": "",
            "summary": "",
            "blocks": [],
        },
    }


def _utc_now():
    return datetime.datetime.utcnow().isoformat() + "Z"


def _clean_text(value):
    return " ".join(str(value or "").split()).strip(" ,.-")


def _load_data():
    if not os.path.exists(DATA_FILE):
        return _default_data()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            raw = json.load(file)
    except Exception:
        return _default_data()

    data = _default_data()
    if isinstance(raw, dict):
        data.update({key: value for key, value in raw.items() if key in data})
    if not isinstance(data.get("rag_library"), dict):
        data["rag_library"] = {}
    if not isinstance(data.get("automation_rules"), list):
        data["automation_rules"] = []
    if not isinstance(data.get("habits"), list):
        data["habits"] = []
    if not isinstance(data.get("goals"), list):
        data["goals"] = []
    if not isinstance(data.get("meetings"), list):
        data["meetings"] = []
    if not isinstance(data.get("mobile_companion"), dict):
        data["mobile_companion"] = _default_data()["mobile_companion"]
    return data


def _save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def _parse_due_datetime(reminder):
    due_at = reminder.get("due_at")
    if due_at:
        try:
            return datetime.datetime.fromisoformat(due_at)
        except ValueError:
            pass

    due_date = reminder.get("due_date")
    if due_date:
        try:
            date_part = datetime.date.fromisoformat(due_date)
            return datetime.datetime.combine(date_part, datetime.time(hour=9, minute=0))
        except ValueError:
            pass

    return None


def _collect_today_events():
    today = datetime.date.today().isoformat()
    events = get_event_data().get("events", [])
    today_events = [event for event in events if str(event.get("date") or "").strip() == today]
    today_events.sort(key=lambda event: str(event.get("time") or "23:59"))
    return today_events


def _collect_today_reminders():
    today = datetime.date.today()
    reminders = get_task_data().get("reminders", [])
    due_today = []
    overdue = []
    for reminder in reminders:
        due_dt = _parse_due_datetime(reminder)
        if due_dt is None:
            continue
        item = {
            "title": _clean_text(reminder.get("title") or "Reminder"),
            "due_at": due_dt,
        }
        if due_dt.date() == today:
            due_today.append(item)
        elif due_dt < datetime.datetime.now():
            overdue.append(item)
    due_today.sort(key=lambda item: item["due_at"])
    overdue.sort(key=lambda item: item["due_at"])
    return due_today, overdue


def generate_ai_day_plan(block_minutes=45, max_blocks=6):
    tasks = [task for task in get_task_data().get("tasks", []) if not task.get("completed")]
    tasks.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    today_events = _collect_today_events()
    due_today, overdue = _collect_today_reminders()

    now = datetime.datetime.now()
    hour_start = max(7, min(20, now.hour + 1))
    cursor = now.replace(hour=hour_start, minute=0, second=0, microsecond=0)
    blocks = []

    for event in today_events[:2]:
        time_label = _clean_text(event.get("time") or "09:00")
        blocks.append(
            {
                "start": time_label,
                "end": "",
                "title": _clean_text(event.get("title") or "Event"),
                "kind": "event",
            }
        )

    for task in tasks[:max_blocks]:
        end = cursor + datetime.timedelta(minutes=block_minutes)
        blocks.append(
            {
                "start": cursor.strftime("%I:%M %p"),
                "end": end.strftime("%I:%M %p"),
                "title": _clean_text(task.get("title") or "Task"),
                "kind": "task",
            }
        )
        cursor = end + datetime.timedelta(minutes=10)

    due_lines = [f"{item['title']} at {item['due_at'].strftime('%I:%M %p')}" for item in due_today[:3]]
    overdue_lines = [f"{item['title']} ({item['due_at'].strftime('%d %b')})" for item in overdue[:3]]

    summary_parts = []
    if blocks:
        summary_parts.append(f"Planned {len(blocks)} focused blocks for today.")
    if due_lines:
        summary_parts.append("Due today: " + " | ".join(due_lines) + ".")
    if overdue_lines:
        summary_parts.append("Overdue first: " + " | ".join(overdue_lines) + ".")
    if not summary_parts:
        summary_parts.append("Your day looks open. Start with one high-impact task and one quick win.")

    summary = " ".join(summary_parts)
    payload = {
        "created_at": _utc_now(),
        "summary": summary,
        "blocks": blocks[:max_blocks],
    }

    data = _load_data()
    data["last_day_plan"] = payload
    _save_data(data)
    return payload


def _find_by_title(items, title):
    query = _clean_text(title).lower()
    for item in items:
        name = _clean_text(item.get("name") or item.get("title")).lower()
        if not name:
            continue
        if name == query or query in name:
            return item
    return None


def add_habit(name):
    clean_name = _clean_text(name)
    if not clean_name:
        return "Tell me the habit name."
    data = _load_data()
    habits = data["habits"]
    if _find_by_title(habits, clean_name):
        return f"Habit already exists: {clean_name}."
    habits.append(
        {
            "id": str(uuid.uuid4()),
            "name": clean_name,
            "created_at": _utc_now(),
            "done_dates": [],
            "last_done": "",
        }
    )
    _save_data(data)
    return f"Habit added: {clean_name}."


def _habit_streak(done_dates):
    if not done_dates:
        return 0
    parsed = sorted(
        {
            datetime.date.fromisoformat(str(item))
            for item in done_dates
            if re.match(r"^\d{4}-\d{2}-\d{2}$", str(item))
        },
        reverse=True,
    )
    if not parsed:
        return 0
    streak = 0
    cursor = datetime.date.today()
    for day in parsed:
        if day == cursor:
            streak += 1
            cursor = cursor - datetime.timedelta(days=1)
        elif streak == 0 and day == cursor - datetime.timedelta(days=1):
            streak += 1
            cursor = day - datetime.timedelta(days=1)
        else:
            break
    return streak


def check_in_habit(name):
    clean_name = _clean_text(name)
    if not clean_name:
        return "Tell me which habit to mark done."
    data = _load_data()
    habit = _find_by_title(data["habits"], clean_name)
    if habit is None:
        return f"I could not find habit {clean_name}."

    today_iso = datetime.date.today().isoformat()
    done_dates = list(habit.get("done_dates") or [])
    if today_iso not in done_dates:
        done_dates.append(today_iso)
    habit["done_dates"] = sorted(set(done_dates))
    habit["last_done"] = today_iso
    streak = _habit_streak(habit["done_dates"])
    _save_data(data)
    return f"Marked habit done: {habit['name']}. Current streak is {streak} day(s)."


def habit_dashboard_summary():
    data = _load_data()
    habits = data["habits"]
    if not habits:
        return "No habits tracked yet. Add one with add habit <name>."

    now = datetime.date.today()
    week_start = now - datetime.timedelta(days=6)
    weekly_hits = 0
    streak_lines = []
    for habit in habits:
        dates = habit.get("done_dates") or []
        streak = _habit_streak(dates)
        streak_lines.append(f"{habit.get('name', 'Habit')}: {streak} day streak")
        valid_dates = [str(item) for item in dates if re.match(r"^\d{4}-\d{2}-\d{2}$", str(item))]
        weekly_hits += sum(1 for item in valid_dates if week_start.isoformat() <= item <= now.isoformat())

    weekly_score = int(round((weekly_hits / max(1, len(habits) * 7)) * 100))
    summary = "Habit score this week is " + str(weekly_score) + "%. " + " | ".join(streak_lines[:6])
    return summary


def create_goal(title):
    clean_title = _clean_text(title)
    if not clean_title:
        return "Tell me the goal title."
    data = _load_data()
    if _find_by_title(data["goals"], clean_title):
        return f"Goal already exists: {clean_title}."
    data["goals"].append(
        {
            "id": str(uuid.uuid4()),
            "title": clean_title,
            "created_at": _utc_now(),
            "milestones": [],
        }
    )
    _save_data(data)
    return f"Goal added: {clean_title}."


def add_goal_milestone(goal_title, milestone_title):
    clean_goal = _clean_text(goal_title)
    clean_milestone = _clean_text(milestone_title)
    if not clean_goal or not clean_milestone:
        return "Use add milestone <milestone> to goal <goal>."
    data = _load_data()
    goal = _find_by_title(data["goals"], clean_goal)
    if goal is None:
        return f"I could not find goal {clean_goal}."
    milestones = goal.get("milestones") or []
    if _find_by_title(milestones, clean_milestone):
        return f"Milestone already exists in {goal['title']}."
    milestones.append({"title": clean_milestone, "done": False, "updated_at": _utc_now()})
    goal["milestones"] = milestones
    _save_data(data)
    return f"Milestone added to {goal['title']}: {clean_milestone}."


def complete_goal_milestone(goal_title, milestone_title):
    clean_goal = _clean_text(goal_title)
    clean_milestone = _clean_text(milestone_title)
    data = _load_data()
    goal = _find_by_title(data["goals"], clean_goal)
    if goal is None:
        return f"I could not find goal {clean_goal}."
    milestone = _find_by_title(goal.get("milestones") or [], clean_milestone)
    if milestone is None:
        return f"I could not find milestone {clean_milestone} in {goal['title']}."
    milestone["done"] = True
    milestone["updated_at"] = _utc_now()
    _save_data(data)
    return f"Milestone completed in {goal['title']}: {milestone['title']}."


def goal_board_summary():
    data = _load_data()
    goals = data["goals"]
    if not goals:
        return "No goals yet. Add one with add goal <title>."
    lines = []
    for goal in goals[:8]:
        milestones = goal.get("milestones") or []
        done_count = sum(1 for item in milestones if item.get("done"))
        total = len(milestones)
        progress = int(round((done_count / max(1, total)) * 100)) if total else 0
        lines.append(f"{goal.get('title', 'Goal')} - {done_count}/{total} milestones ({progress}%)")
    return "Goal board: " + " | ".join(lines)


def smart_reminder_priority_summary(limit=6):
    reminders = get_task_data().get("reminders", [])
    now = datetime.datetime.now()
    ranked = []
    for reminder in reminders:
        title = _clean_text(reminder.get("title") or "Reminder")
        due_dt = _parse_due_datetime(reminder)
        score = 0
        if due_dt:
            delta_hours = (due_dt - now).total_seconds() / 3600.0
            if delta_hours < 0:
                score += 120
            elif delta_hours <= 24:
                score += 90
            elif delta_hours <= 72:
                score += 60
            else:
                score += 30
        keywords = ("bill", "deadline", "doctor", "meeting", "exam", "payment")
        if any(keyword in title.lower() for keyword in keywords):
            score += 25
        ranked.append((score, title, due_dt))

    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked:
        return "No reminders to rank right now."

    lines = []
    for index, (score, title, due_dt) in enumerate(ranked[:limit], start=1):
        due_label = due_dt.strftime("%d %b %I:%M %p") if due_dt else "No schedule"
        priority = "P1" if score >= 100 else "P2" if score >= 70 else "P3"
        lines.append(f"{index}. {priority} {title} - {due_label}")
    return "Smart reminder priority: " + " | ".join(lines)


def apply_voice_trainer(profile):
    clean_profile = _clean_text(profile).lower()
    if clean_profile not in VOICE_TRAINER_PRESETS:
        return "Use voice trainer quiet, normal, or noisy."

    for key, value in VOICE_TRAINER_PRESETS[clean_profile].items():
        update_setting(key, value)
    return (
        f"Voice trainer applied for {clean_profile} environment. "
        f"Wake threshold {VOICE_TRAINER_PRESETS[clean_profile]['voice.wake_match_threshold']}, "
        f"follow-up timeout {VOICE_TRAINER_PRESETS[clean_profile]['voice.follow_up_timeout_seconds']} seconds."
    )


def voice_trainer_status():
    mode = _clean_text(get_setting("voice.mode", "normal"))
    threshold = float(get_setting("voice.wake_match_threshold", 0.68))
    follow_up_timeout = float(get_setting("voice.follow_up_timeout_seconds", 12))
    follow_up_listen = float(get_setting("voice.follow_up_listen_timeout", 3))
    interrupt_follow_up = float(get_setting("voice.interrupt_follow_up_seconds", 5))
    return (
        f"Voice trainer status: mode {mode}, wake threshold {threshold}, "
        f"follow-up timeout {follow_up_timeout}s, follow-up listen {follow_up_listen}s, "
        f"interrupt window {interrupt_follow_up}s."
    )


def set_language_mode(mode):
    clean_mode = _clean_text(mode).lower()
    if clean_mode not in {"auto", "english", "tamil"}:
        return "Use language mode auto, english, or tamil."
    update_setting("assistant.auto_language_mode", clean_mode)
    return f"Language mode updated to {clean_mode}."


def get_language_mode():
    return _clean_text(get_setting("assistant.auto_language_mode", "auto")).lower() or "auto"


def _predict_language(text):
    content = str(text or "")
    if re.search(r"[\u0B80-\u0BFF]", content):
        return "tamil"
    lowered = content.lower()
    tamil_markers = ("vanakkam", "enna", "epdi", "saptiya", "seri", "nandri", "macha")
    if any(marker in lowered for marker in tamil_markers):
        return "tamil"
    return "english"


def preview_language_response(text):
    mode = get_language_mode()
    predicted = _predict_language(text) if mode == "auto" else mode
    if predicted == "tamil":
        return "Language preview: Tamil response mode selected."
    return "Language preview: English response mode selected."


def language_mode_status():
    mode = get_language_mode()
    return f"Language mode is {mode}. Use preview language switch <text> to test auto detection."


def _extract_action_items(text):
    lines = re.split(r"[.\n;]+", str(text or ""))
    triggers = ("send", "call", "prepare", "review", "finish", "schedule", "follow up", "update")
    actions = []
    for line in lines:
        clean_line = _clean_text(line)
        if not clean_line:
            continue
        lowered = clean_line.lower()
        if any(lowered.startswith(trigger) or f" {trigger} " in lowered for trigger in triggers):
            actions.append(clean_line)
    if not actions:
        actions = [_clean_text(item) for item in lines if _clean_text(item)][:3]
    return actions[:6]


def capture_meeting_note(text, title=None):
    body = _clean_text(text)
    if not body:
        return "Give me meeting notes text to capture."
    meeting_title = _clean_text(title) or f"Meeting {datetime.date.today().isoformat()}"
    actions = _extract_action_items(body)
    data = _load_data()
    data["meetings"].append(
        {
            "id": str(uuid.uuid4()),
            "title": meeting_title,
            "notes": body,
            "actions": actions,
            "created_at": _utc_now(),
        }
    )
    _save_data(data)
    if actions:
        return f"Meeting saved: {meeting_title}. Action items: " + " | ".join(actions[:4])
    return f"Meeting saved: {meeting_title}."


def meeting_mode_summary(limit=3):
    data = _load_data()
    meetings = data["meetings"][-limit:]
    if not meetings:
        return "No meeting notes captured yet."
    lines = []
    for item in reversed(meetings):
        actions = item.get("actions") or []
        lines.append(f"{item.get('title', 'Meeting')} - {len(actions)} action item(s)")
    return "Meeting summary: " + " | ".join(lines)


def _rag_entry(data, filename):
    clean_name = _clean_text(filename)
    if not clean_name:
        return None, ""
    library = data["rag_library"]
    entry = library.get(clean_name) or {"tags": [], "folder": "inbox", "updated_at": _utc_now()}
    library[clean_name] = entry
    return entry, clean_name


def tag_document(filename, tags_text):
    data = _load_data()
    entry, clean_name = _rag_entry(data, filename)
    if entry is None:
        return "Tell me the document name to tag."
    tags = [
        _clean_text(item).lower()
        for item in re.split(r"[,\|]", str(tags_text or ""))
        if _clean_text(item)
    ]
    if not tags:
        return "Give at least one tag."
    merged = sorted(set((entry.get("tags") or []) + tags))
    entry["tags"] = merged
    entry["updated_at"] = _utc_now()
    _save_data(data)
    return f"Document {clean_name} tagged as: {', '.join(merged[:8])}."


def move_document_to_folder(filename, folder):
    data = _load_data()
    entry, clean_name = _rag_entry(data, filename)
    if entry is None:
        return "Tell me the document name."
    clean_folder = _clean_text(folder).lower()
    if not clean_folder:
        return "Tell me the folder name."
    entry["folder"] = clean_folder
    entry["updated_at"] = _utc_now()
    _save_data(data)
    return f"Moved {clean_name} to folder {clean_folder}."


def rag_library_summary(limit=10):
    data = _load_data()
    library = data["rag_library"]
    if not library:
        return "RAG library is empty. Tag a document with tag document <name> as <tags>."
    lines = []
    for index, (name, entry) in enumerate(library.items()):
        if index >= limit:
            break
        tags = ", ".join((entry.get("tags") or [])[:4]) or "no tags"
        folder = _clean_text(entry.get("folder") or "inbox")
        lines.append(f"{name} [{folder}] ({tags})")
    return "RAG library: " + " | ".join(lines)


def create_automation_rule(name, trigger, action):
    clean_name = _clean_text(name)
    clean_trigger = _clean_text(trigger)
    clean_action = _clean_text(action)
    if not clean_name or not clean_trigger or not clean_action:
        return "Use create automation <name> when <trigger> then <action>."
    data = _load_data()
    rules = data["automation_rules"]
    existing = _find_by_title(rules, clean_name)
    if existing:
        existing["trigger"] = clean_trigger
        existing["action"] = clean_action
        existing["enabled"] = True
        existing["updated_at"] = _utc_now()
        _save_data(data)
        return f"Automation updated: {clean_name}."
    rules.append(
        {
            "id": str(uuid.uuid4()),
            "name": clean_name,
            "trigger": clean_trigger,
            "action": clean_action,
            "enabled": True,
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }
    )
    _save_data(data)
    return f"Automation created: {clean_name}."


def list_automation_rules(limit=10):
    rules = _load_data()["automation_rules"]
    if not rules:
        return "No automation rules yet."
    lines = []
    for rule in rules[:limit]:
        status = "on" if rule.get("enabled", True) else "off"
        lines.append(
            f"{rule.get('name', 'Rule')} [{status}] when {rule.get('trigger', '')} then {rule.get('action', '')}"
        )
    return "Automation rules: " + " | ".join(lines)


def set_automation_enabled(name, enabled):
    clean_name = _clean_text(name)
    if not clean_name:
        return "Tell me which automation to update."
    data = _load_data()
    rule = _find_by_title(data["automation_rules"], clean_name)
    if rule is None:
        return f"I could not find automation {clean_name}."
    rule["enabled"] = bool(enabled)
    rule["updated_at"] = _utc_now()
    _save_data(data)
    return f"Automation {rule.get('name', clean_name)} {'enabled' if enabled else 'disabled'}."


def setup_mobile_companion(device_name):
    clean_name = _clean_text(device_name)
    if not clean_name:
        return "Tell me your mobile companion name."
    data = _load_data()
    mobile = data["mobile_companion"]
    mobile["enabled"] = True
    mobile["device_name"] = clean_name
    mobile.setdefault("history", [])
    _save_data(data)
    return f"Mobile companion connected as {clean_name}."


def send_mobile_update(message):
    clean_message = _clean_text(message)
    if not clean_message:
        return "Tell me the message to send."
    data = _load_data()
    mobile = data["mobile_companion"]
    if not mobile.get("enabled"):
        return "Mobile companion is not setup. Run setup mobile companion <name> first."
    history = mobile.setdefault("history", [])
    history.append(
        {
            "id": str(uuid.uuid4()),
            "message": clean_message,
            "sent_at": _utc_now(),
            "status": "queued",
        }
    )
    if len(history) > 40:
        del history[:-40]
    _save_data(data)
    return f"Mobile update queued for {mobile.get('device_name', 'device')}: {clean_message}."


def mobile_companion_status():
    mobile = _load_data()["mobile_companion"]
    if not mobile.get("enabled"):
        return "Mobile companion is not enabled."
    history = mobile.get("history") or []
    last = history[-1]["message"] if history else "No updates yet."
    return (
        f"Mobile companion active as {mobile.get('device_name', 'device')}. "
        f"Queued updates: {len(history)}. Last: {last}"
    )


def nextgen_status_snapshot():
    data = _load_data()
    day_plan = data.get("last_day_plan") or {}
    habits = data.get("habits") or []
    goals = data.get("goals") or []
    meetings = data.get("meetings") or []
    rag_library = data.get("rag_library") or {}
    rules = data.get("automation_rules") or []
    mobile = data.get("mobile_companion") or {}

    total_milestones = 0
    done_milestones = 0
    for goal in goals:
        milestones = goal.get("milestones") or []
        total_milestones += len(milestones)
        done_milestones += sum(1 for item in milestones if item.get("done"))

    enabled_rules = sum(1 for rule in rules if rule.get("enabled", True))
    language_mode = get_language_mode()
    voice_mode = _clean_text(get_setting("voice.mode", "normal")) or "normal"
    day_plan_summary = _clean_text(day_plan.get("summary")) or "No AI day plan generated yet."
    mobile_enabled = bool(mobile.get("enabled"))
    mobile_device = _clean_text(mobile.get("device_name"))

    highlights = [
        f"Habits: {len(habits)} tracked",
        f"Goals: {len(goals)} with {done_milestones}/{total_milestones} milestones complete",
        f"Reminders: smart priority available",
        f"Voice trainer mode: {voice_mode}",
        f"Language mode: {language_mode}",
        f"Meetings captured: {len(meetings)}",
        f"RAG docs tagged: {len(rag_library)}",
        f"Automation rules: {enabled_rules}/{len(rules)} enabled",
        (
            "Mobile companion: active"
            + (f" ({mobile_device})" if mobile_device else "")
            if mobile_enabled
            else "Mobile companion: not connected"
        ),
    ]

    return {
        "day_plan_summary": day_plan_summary,
        "habits_count": len(habits),
        "goals_count": len(goals),
        "milestones_done": done_milestones,
        "milestones_total": total_milestones,
        "meetings_count": len(meetings),
        "rag_docs_count": len(rag_library),
        "automation_total": len(rules),
        "automation_enabled": enabled_rules,
        "language_mode": language_mode,
        "voice_mode": voice_mode,
        "mobile_enabled": mobile_enabled,
        "mobile_device": mobile_device or "",
        "highlights": highlights,
    }
