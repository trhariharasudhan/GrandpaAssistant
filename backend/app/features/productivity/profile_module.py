import datetime

from brain.database import get_command_frequency
from brain.memory_engine import load_memory
from brain.memory_engine import get_memory, set_memory
from productivity.task_module import get_task_data


EMOTION_KEYWORDS = {
    "happy": ["happy", "good", "great", "excited", "awesome", "super"],
    "sad": ["sad", "down", "upset", "hurt", "crying", "depressed"],
    "stressed": ["stress", "stressed", "pressure", "overwhelmed", "anxious"],
    "angry": ["angry", "mad", "annoyed", "irritated", "furious"],
    "tired": ["tired", "sleepy", "exhausted", "drained", "low energy"],
    "confused": ["confused", "lost", "stuck", "blank", "unclear"],
}


def _safe_get(data, path, default=None):
    current = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def _compact_list(values, limit=3):
    values = [str(value) for value in values if value]
    return values[:limit]


def _join_values(values):
    values = [str(value) for value in values if value]
    return ", ".join(values)


def _first_value(value, fallback="not saved yet"):
    if isinstance(value, list):
        return value[0] if value else fallback
    return value or fallback


def build_profile_summary():
    memory = load_memory()
    if not memory:
        return "I do not have enough profile details saved yet."

    name = _safe_get(memory, "personal.identity.name", "You")
    city = _safe_get(memory, "personal.location.current_location.city")
    state = _safe_get(memory, "personal.location.current_location.state")
    job_status = _safe_get(memory, "professional.career_preferences.current_job_status")
    preferred_role = _safe_get(memory, "professional.career_preferences.preferred_job_role")
    current_focus = _safe_get(memory, "professional.learning_path.current_focus", [])
    strongest_skill = _safe_get(memory, "professional.career_preferences.strongest_skill", [])
    one_year_goal = _safe_get(memory, "professional.goal_timeline.one_year_goal")
    dream_company = _safe_get(memory, "professional.career_preferences.dream_company", [])
    favorite_browser = _safe_get(memory, "personal.favorites.favorite_browser")
    favorite_series = _safe_get(memory, "personal.favorites.favorite_series", [])
    best_time = _safe_get(memory, "personal.routine.best_productive_time")

    parts = [f"Your name is {name}."]

    location = _join_values([city, state])
    if location:
        parts.append(f"You are based in {location}.")

    if job_status:
        parts.append(f"You are currently working as a {job_status}.")

    if preferred_role:
        parts.append(f"Your preferred career direction is {preferred_role}.")

    if strongest_skill:
        parts.append(f"Your strongest skills are {_join_values(strongest_skill)}.")

    if current_focus:
        parts.append(f"Right now you are focusing on {_join_values(current_focus[:3])}.")

    if one_year_goal:
        parts.append(f"Your one year goal is {one_year_goal}")

    if dream_company:
        parts.append(f"Your dream companies are {_join_values(dream_company)}.")

    if best_time:
        parts.append(f"Your best productive time is {best_time}.")

    if favorite_browser:
        parts.append(f"You like using {favorite_browser}.")

    if favorite_series:
        parts.append(f"One of your favorite series is {_first_value(favorite_series)}.")

    return " ".join(parts)


def detect_emotion(text):
    normalized = " " + " ".join((text or "").lower().split()) + " "
    for emotion, keywords in EMOTION_KEYWORDS.items():
        for keyword in keywords:
            if f" {keyword} " in normalized:
                return emotion
    return None


def remember_emotion_signal(text):
    emotion = detect_emotion(text)
    if not emotion:
        return None
    set_memory("personal.assistant.last_detected_emotion", emotion)
    set_memory("personal.assistant.last_detected_emotion_at", datetime.datetime.now().isoformat())
    return emotion


def build_emotion_snapshot():
    emotion = get_memory("personal.assistant.last_detected_emotion")
    detected_at = get_memory("personal.assistant.last_detected_emotion_at")
    if not emotion:
        return "I have not picked up a clear emotional signal from you yet."

    soft_map = {
        "happy": "You seem to be in a positive mood.",
        "sad": "You seem a bit low right now.",
        "stressed": "You seem under pressure right now.",
        "angry": "You sound frustrated right now.",
        "tired": "You seem tired right now.",
        "confused": "You seem a little stuck right now.",
    }
    response = soft_map.get(emotion, f"You seem {emotion} right now.")
    if detected_at:
        try:
            time_text = datetime.datetime.fromisoformat(detected_at).strftime("%I:%M %p")
            response += f" I last picked that up around {time_text}."
        except ValueError:
            pass
    return response


def _classify_command(command_text):
    text = (command_text or "").lower().strip()
    if not text:
        return "general"
    if text.startswith(("call ", "message ", "mail ", "email ", "send whatsapp")):
        return "communication"
    if text.startswith(("add task", "complete", "delete task", "remind ", "latest reminder", "what is due")):
        return "productivity"
    if text.startswith(("open ", "search ", "summarize selected", "copy selected", "read selected")):
        return "browser"
    if text.startswith(("note", "take a note", "add note", "latest note", "list notes")):
        return "notes"
    if text.startswith(("weather", "system status", "battery", "storage", "show settings")):
        return "system"
    return "general"


def build_habit_snapshot():
    frequency = get_command_frequency(limit=150)
    if not frequency:
        return "I do not have enough command history to learn your habits yet."

    top_commands = frequency[:3]
    category_counts = {}
    for command_text, count in frequency[:25]:
        category = _classify_command(command_text)
        category_counts[category] = category_counts.get(category, 0) + count

    top_category = max(category_counts.items(), key=lambda item: item[1])[0] if category_counts else "general"
    command_line = " | ".join(f"{command} ({count})" for command, count in top_commands)
    category_line = {
        "communication": "You use communication commands the most.",
        "productivity": "You mostly use the assistant for tasks and reminders.",
        "browser": "You often use browser and text-intelligence workflows.",
        "notes": "You regularly use note-related workflows.",
        "system": "You often check system and status commands.",
        "general": "Your command usage is still broad and mixed.",
    }.get(top_category, "Your command usage is still broad and mixed.")
    return f"{category_line} Top repeated commands: {command_line}."


def build_focus_suggestion():
    memory = load_memory()
    data = get_task_data()

    pending_tasks = [task for task in data.get("tasks", []) if not task.get("completed")]
    reminders = [reminder for reminder in data.get("reminders", []) if reminder.get("due_date")]

    current_focus = _safe_get(memory, "professional.learning_path.current_focus", [])
    one_year_goal = _safe_get(memory, "professional.goal_timeline.one_year_goal")
    strongest_skill = _safe_get(memory, "professional.career_preferences.strongest_skill", [])
    weakest_skill = _safe_get(memory, "professional.career_preferences.weakest_skill")
    study_time = _safe_get(memory, "personal.routine.study_time")

    parts = []

    if pending_tasks:
        task_titles = ", ".join(task.get("title", "Untitled task") for task in pending_tasks[:3])
        parts.append(f"Your immediate focus should be on pending tasks like {task_titles}.")

    if one_year_goal:
        parts.append(f"You should stay aligned with your one year goal: {one_year_goal}")

    if current_focus:
        parts.append(f"A strong next step is to continue improving {_join_values(current_focus[:2])}.")

    if strongest_skill:
        parts.append(f"Use your strengths in {_join_values(strongest_skill[:2])} to move faster.")

    if weakest_skill:
        parts.append(f"Also keep improving this area: {weakest_skill}")

    if study_time:
        parts.append(f"You already reserved {study_time} for study, so that is a good slot to focus deeply.")

    if reminders:
        parts.append("Do not ignore your saved reminders while planning your next steps.")

    if not parts:
        return "You should focus on your current goals, build consistency, and keep improving your technical skills."

    return " ".join(parts)


def build_personal_snapshot():
    memory = load_memory()
    if not memory:
        return "I do not have enough personal details saved yet."

    preferred_name = _safe_get(memory, "personal.assistant.preferred_name_for_user")
    language = _safe_get(memory, "personal.assistant.preferred_response_language")
    tone = _safe_get(memory, "personal.assistant.preferred_response_tone")
    wake_time = _safe_get(memory, "personal.routine.wake_up_time")
    sleep_time = _safe_get(memory, "personal.routine.sleep_time")
    favorite_foods = _safe_get(memory, "personal.favorites.foods", [])
    stress_relief = _safe_get(memory, "personal.health.stress_relief_method")
    workout = _safe_get(memory, "personal.health.workout_habit")

    parts = []
    if preferred_name:
        parts.append(f"You prefer to be called {preferred_name}.")
    if language:
        parts.append(f"You prefer responses in {language}.")
    if tone:
        parts.append(f"You like a {tone} response style.")
    if wake_time and sleep_time:
        parts.append(f"Your usual routine is waking up at {wake_time} and sleeping at {sleep_time}.")
    if workout:
        parts.append(f"Your workout habit is {workout}.")
    if stress_relief:
        parts.append(f"You usually handle stress by {stress_relief}.")
    if favorite_foods:
        parts.append(f"You enjoy foods like {_join_values(favorite_foods[:5])}.")

    return " ".join(parts) if parts else "I do not have enough personal snapshot details saved yet."


def build_personalized_suggestion():
    memory = load_memory()
    data = get_task_data()
    pending_tasks = [task for task in data.get("tasks", []) if not task.get("completed")]
    reminders = data.get("reminders", [])
    emotion = get_memory("personal.assistant.last_detected_emotion")
    preferred_name = _safe_get(memory, "personal.assistant.preferred_name_for_user", "Hari")
    study_time = _safe_get(memory, "personal.routine.study_time")
    current_focus = _safe_get(memory, "professional.learning_path.current_focus", [])

    if emotion == "stressed":
        if pending_tasks:
            return (
                f"{preferred_name}, keep it simple now. "
                f"Finish one clear task first: {pending_tasks[0].get('title', 'your top task')}."
            )
        return f"{preferred_name}, take one small step now and avoid overloading yourself."

    if emotion == "tired":
        return (
            f"{preferred_name}, keep this session light. "
            "Use quick actions or finish one small pending item before taking a break."
        )

    if pending_tasks:
        task_titles = _compact_list([task.get("title", "Untitled task") for task in pending_tasks], limit=2)
        return f"{preferred_name}, your best next move is to finish {', '.join(task_titles)}."

    if reminders:
        reminder_title = reminders[0].get("title", "your reminder")
        return f"{preferred_name}, clear {reminder_title} first so the rest of the day stays clean."

    if current_focus:
        return f"{preferred_name}, a strong next step is to spend focused time on {_join_values(current_focus[:2])}."

    if study_time:
        return f"{preferred_name}, your planned study slot is {study_time}. Use that block intentionally."

    return build_proactive_nudge()


def _parse_time_label(time_text):
    if not time_text:
        return None

    candidates = [time_text]
    if "to" in time_text.lower():
        candidates.append(time_text.lower().split("to", 1)[0].strip())

    for candidate in candidates:
        try:
            return datetime.datetime.strptime(candidate.strip(), "%I:%M %p").time()
        except ValueError:
            continue

    return None


def _is_within_window(target_time, window_minutes=90):
    if not target_time:
        return False

    now = datetime.datetime.now()
    target = datetime.datetime.combine(now.date(), target_time)
    delta = abs((target - now).total_seconds()) / 60
    return delta <= window_minutes


def build_proactive_nudge():
    memory = load_memory()
    data = get_task_data()

    if not memory:
        return "Keep moving on your current goals and stay consistent today."

    preferred_name = _safe_get(memory, "personal.assistant.preferred_name_for_user", "Hari")
    study_time = _parse_time_label(_safe_get(memory, "personal.routine.study_time"))
    work_time = _parse_time_label(_safe_get(memory, "personal.routine.work_time"))
    one_year_goal = _safe_get(memory, "professional.goal_timeline.one_year_goal")
    current_focus = _safe_get(memory, "professional.learning_path.current_focus", [])
    strongest_skill = _safe_get(memory, "professional.career_preferences.strongest_skill", [])
    pending_tasks = [task for task in data.get("tasks", []) if not task.get("completed")]
    reminders = data.get("reminders", [])

    if _is_within_window(study_time):
        return (
            f"{preferred_name}, this is close to your study time. "
            "This is a good slot to focus without distractions."
        )

    if _is_within_window(work_time):
        return (
            f"{preferred_name}, this matches your work routine. "
            "Try to finish your most important technical task first."
        )

    if pending_tasks:
        top_task = pending_tasks[0].get("title", "your pending task")
        return f"{preferred_name}, your next best move is to finish {top_task} before starting something new."

    if reminders:
        reminder_title = reminders[0].get("title", "your reminder")
        return f"{preferred_name}, do not forget {reminder_title}. Keep your day aligned with your reminders."

    if one_year_goal:
        return f"{preferred_name}, one good proactive step today is to move closer to this goal: {one_year_goal}"

    if current_focus:
        return f"{preferred_name}, today you can spend focused time on {_join_values(current_focus[:2])}."

    if strongest_skill:
        return f"{preferred_name}, use your strength in {_join_values(strongest_skill[:2])} to make visible progress today."

    return f"{preferred_name}, stay consistent today and make one meaningful step toward your long term vision."
