import json
import os
import re

from brain.database import (
    LEGACY_MEMORY_PATH,
    get_all_memory_entries,
    get_memory_value,
    initialize_database,
    migrate_legacy_memory,
    set_memory_value,
)

# -------- STOP WORDS (ignore these words in questions) --------
STOP_WORDS = [
    "what",
    "is",
    "my",
    "who",
    "am",
    "i",
    "tell",
    "me",
    "about",
    "please",
    "id",
    "the",
    "a",
    "an",
    "your",
]

DIRECT_PATH_HINTS = [
    (["my name", "tell my name", "who am i"], "personal.identity.name"),
    (["my email", "my mail"], "personal.contact.email_primary"),
    (["my phone", "my number", "my mobile"], "personal.contact.mobile_number"),
    (["my whatsapp"], "personal.contact.whatsapp_number"),
    (["my birthday", "my date of birth", "my dob"], "personal.identity.date_of_birth"),
    (["my father", "my father name", "father age", "father dob", "father occupation", "father phone"], "personal.family.father"),
    (["my mother", "my mother name", "mother age", "mother dob", "mother occupation", "mother phone"], "personal.family.mother"),
    (["my sister", "my sibling"], "personal.family.siblings"),
    (["my friends", "my close friends"], "personal.friends.close_friends"),
    (["my city"], "personal.location.current_location.city"),
    (["my location", "where do i live", "my address"], "personal.location"),
    (["my github"], "personal.social_media.github"),
    (["my instagram"], "personal.social_media.instagram"),
    (["my linkedin"], "personal.social_media.linkedin"),
    (["my twitter", "my x account"], "personal.social_media.twitter"),
    (["my portfolio"], "personal.contact.portfolio_website"),
    (["emergency contact"], "personal.contact.emergency_contact"),
    (["my routine", "my wake up time", "my sleep time", "my study time", "my work time"], "personal.routine"),
    (["my favorite browser"], "personal.favorites.favorite_browser"),
    (["my favorite app"], "personal.favorites.favorite_app"),
    (["my favorite series"], "personal.favorites.favorite_series"),
    (["my favorite book"], "personal.favorites.books"),
    (["my favorite football team"], "personal.favorites.favorite_football_team"),
    (["my favorite football player"], "personal.favorites.favorite_football_player"),
    (["my favorite cricketer"], "personal.favorites.favorite_cricketer"),
    (["my favorite singer"], "personal.favorites.favorite_singer"),
    (["my favorite actor"], "personal.favorites.actors"),
    (["my favorite actress"], "personal.favorites.actresses"),
    (["my favorite food"], "personal.favorites.foods"),
    (["my dream company"], "professional.career_preferences.dream_company"),
    (["my dream business"], "professional.career_preferences.dream_business"),
    (["my favorite coding language"], "professional.career_preferences.favorite_coding_language"),
    (["my strongest skill"], "professional.career_preferences.strongest_skill"),
    (["my weakest skill"], "professional.career_preferences.weakest_skill"),
    (["my biggest achievement"], "professional.career_preferences.biggest_achievement"),
    (["my proudest moment"], "professional.career_preferences.proudest_moment"),
    (["my current job status"], "professional.career_preferences.current_job_status"),
    (["my preferred job role"], "professional.career_preferences.preferred_job_role"),
    (["my preferred job location"], "professional.career_preferences.preferred_job_location"),
    (["my expected salary"], "professional.career_preferences.expected_salary"),
    (["my one year goal", "my 1 year goal"], "professional.goal_timeline.one_year_goal"),
    (["my five year goal", "my 5 year goal"], "professional.goal_timeline.five_year_goal"),
    (["my ten year goal", "my 10 year goal"], "professional.goal_timeline.ten_year_goal"),
    (["my goal", "my goals", "my vision"], "professional.goal_timeline"),
]

FIELD_LABELS = {
    "date_of_birth": "date of birth",
    "mobile_number": "mobile number",
    "whatsapp_number": "WhatsApp number",
    "email_primary": "primary email address",
    "email_secondary": "secondary email address",
    "portfolio_website": "portfolio website",
    "current_job_status": "current job status",
    "preferred_job_role": "preferred job role",
    "preferred_job_location": "preferred job location",
    "expected_salary": "expected salary",
    "dream_company": "dream companies",
    "dream_business": "dream businesses",
    "favorite_coding_language": "favorite coding language",
    "favorite_browser": "favorite browser",
    "favorite_app": "favorite app",
    "favorite_series": "favorite series",
}

MEMORY_UPDATE_ALIASES = {
    "name": "personal.identity.name",
    "email": "personal.contact.email_primary",
    "primary email": "personal.contact.email_primary",
    "secondary email": "personal.contact.email_secondary",
    "phone": "personal.contact.mobile_number",
    "mobile": "personal.contact.mobile_number",
    "whatsapp": "personal.contact.whatsapp_number",
    "alternate mobile": "personal.contact.alternate_mobile_number",
    "address": "personal.contact.address",
    "github": "personal.social_media.github",
    "github url": "personal.social_media.github_url",
    "instagram": "personal.social_media.instagram",
    "instagram url": "personal.social_media.instagram_url",
    "linkedin": "personal.social_media.linkedin",
    "linkedin url": "personal.social_media.linkedin_url",
    "twitter": "personal.social_media.twitter",
    "twitter url": "personal.social_media.twitter_url",
    "preferred response language": "personal.assistant.preferred_response_language",
    "preferred response tone": "personal.assistant.preferred_response_tone",
    "preferred name": "personal.assistant.preferred_name_for_user",
    "wake up time": "personal.routine.wake_up_time",
    "sleep time": "personal.routine.sleep_time",
    "study time": "personal.routine.study_time",
    "work time": "personal.routine.work_time",
    "best productive time": "personal.routine.best_productive_time",
    "father age": "personal.family.father.age",
    "father occupation": "personal.family.father.occupation",
    "father phone": "personal.family.father.phone",
    "mother age": "personal.family.mother.age",
    "mother occupation": "personal.family.mother.occupation",
    "mother phone": "personal.family.mother.phone",
    "sister phone": "personal.family.siblings.0.phone",
    "sister occupation": "personal.family.siblings.0.occupation",
    "favorite browser": "personal.favorites.favorite_browser",
    "favorite app": "personal.favorites.favorite_app",
    "favorite book": "personal.favorites.books",
    "favorite series": "personal.favorites.favorite_series",
    "favorite actor": "personal.favorites.actors",
    "favorite actress": "personal.favorites.actresses",
    "favorite food": "personal.favorites.foods",
    "dream company": "professional.career_preferences.dream_company",
    "dream business": "professional.career_preferences.dream_business",
    "favorite coding language": "professional.career_preferences.favorite_coding_language",
    "strongest skill": "professional.career_preferences.strongest_skill",
    "weakest skill": "professional.career_preferences.weakest_skill",
    "biggest achievement": "professional.career_preferences.biggest_achievement",
    "proudest moment": "professional.career_preferences.proudest_moment",
    "current job status": "professional.career_preferences.current_job_status",
    "preferred job role": "professional.career_preferences.preferred_job_role",
    "preferred job location": "professional.career_preferences.preferred_job_location",
    "expected salary": "professional.career_preferences.expected_salary",
    "one year goal": "professional.goal_timeline.one_year_goal",
    "five year goal": "professional.goal_timeline.five_year_goal",
    "ten year goal": "professional.goal_timeline.ten_year_goal",
}


CONTACT_FIELD_ALIASES = {
    "email": "email",
    "mail": "email",
    "phone": "phone",
    "mobile": "phone",
    "number": "phone",
    "whatsapp": "phone",
}


initialize_database()
migrate_legacy_memory()


def _unflatten_memory(flat_entries):
    nested = {}

    for path, value in flat_entries.items():
        keys = path.split(".")
        current = nested

        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    return nested


def _load_memory_file():
    if not os.path.exists(LEGACY_MEMORY_PATH):
        return None

    try:
        with open(LEGACY_MEMORY_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None


def _save_memory_file(memory):
    with open(LEGACY_MEMORY_PATH, "w", encoding="utf-8") as file:
        json.dump(memory, file, indent=4, ensure_ascii=False)


def load_memory():
    file_memory = _load_memory_file()
    if file_memory is not None:
        return file_memory
    return _unflatten_memory(get_all_memory_entries())


def _get_nested_value(data, path):
    current = data
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _set_nested_value(data, path, value):
    keys = path.split(".")
    current = data

    for index_pos, key in enumerate(keys[:-1]):
        if key.isdigit():
            index = int(key)
            if not isinstance(current, list):
                return
            while len(current) <= index:
                current.append({})
            if not isinstance(current[index], dict):
                current[index] = {}
            current = current[index]
            continue

        next_key = keys[index_pos + 1]
        if key not in current:
            current[key] = [] if next_key.isdigit() else {}
        elif not isinstance(current[key], (dict, list)):
            current[key] = [] if next_key.isdigit() else {}

        current = current[key]

    last_key = keys[-1]
    if last_key.isdigit():
        index = int(last_key)
        if not isinstance(current, list):
            return
        while len(current) <= index:
            current.append(None)
        current[index] = value
    else:
        current[last_key] = value


def _remove_nested_value(data, path):
    keys = path.split(".")
    current = data

    for key in keys[:-1]:
        if key.isdigit():
            index = int(key)
            if not isinstance(current, list) or index >= len(current):
                return False
            current = current[index]
        else:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]

    last_key = keys[-1]
    if last_key.isdigit():
        index = int(last_key)
        if not isinstance(current, list) or index >= len(current):
            return False
        current[index] = None
        return True

    if not isinstance(current, dict) or last_key not in current:
        return False

    current[last_key] = None
    return True


def _is_blank(value):
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _normalize_question(question):
    cleaned = re.sub(r"[^\w\s]", " ", question.lower())
    return " ".join(cleaned.split())


def _normalize_alias(text):
    return " ".join(text.lower().strip().split())


def resolve_memory_path(field_name):
    field_name = _normalize_alias(field_name)
    if field_name in MEMORY_UPDATE_ALIASES:
        return MEMORY_UPDATE_ALIASES[field_name]

    for alias, path in sorted(MEMORY_UPDATE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if field_name == alias:
            return path

    return None


def _parse_value_for_path(path, raw_value):
    raw_value = raw_value.strip()
    if raw_value.lower() in {"null", "none", "empty", "blank"}:
        return None

    if path.endswith(
        (
            ".age",
            ".marks_10",
            ".marks_11",
            ".marks_12",
        )
    ):
        digits = re.sub(r"[^\d]", "", raw_value)
        return int(digits) if digits else raw_value

    if path.endswith(
        (
            ".dream_company",
            ".dream_business",
            ".preferred_job_location",
            ".work_preference",
            ".strongest_skill",
            ".favorite_series",
            ".books",
            ".actors",
            ".actresses",
            ".foods",
        )
    ):
        return [item.strip() for item in re.split(r"[,/]", raw_value) if item.strip()]

    return raw_value


def _humanize_label(path):
    field = path.split(".")[-1]
    return FIELD_LABELS.get(field, field.replace("_", " "))


def _format_scalar(value):
    if value is None:
        return "not saved yet"
    return str(value)


def _format_memory_value(value):
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            formatted_items = []
            for item in value:
                parts = []
                for key, item_value in item.items():
                    if _is_blank(item_value):
                        continue
                    parts.append(f"{key.replace('_', ' ')}: {item_value}")
                if parts:
                    formatted_items.append(", ".join(parts))
            return " | ".join(formatted_items)

        return ", ".join(map(str, value))

    if isinstance(value, dict):
        ordered_parts = []
        for key, item_value in value.items():
            if _is_blank(item_value):
                continue
            ordered_parts.append(f"{key.replace('_', ' ')}: {item_value}")
        return ", ".join(ordered_parts)

    return str(value)


def _iter_named_contacts(memory):
    family = memory.get("personal", {}).get("family", {})
    for person_key in ["father", "mother"]:
        person = family.get(person_key, {})
        if person.get("name"):
            yield person.get("name"), person, f"personal.family.{person_key}"

    for index, sibling in enumerate(family.get("siblings", [])):
        if sibling.get("name"):
            yield sibling.get("name"), sibling, f"personal.family.siblings.{index}"

    emergency = memory.get("personal", {}).get("contact", {}).get("emergency_contact", {})
    if emergency.get("name"):
        yield emergency.get("name"), emergency, "personal.contact.emergency_contact"

    for index, friend in enumerate(memory.get("personal", {}).get("friends", {}).get("close_friends", [])):
        if friend.get("name"):
            yield friend.get("name"), friend, f"personal.friends.close_friends.{index}"
        if friend.get("nickname"):
            yield friend.get("nickname"), friend, f"personal.friends.close_friends.{index}"


def _find_named_contact(memory, contact_name):
    target = _normalize_alias(contact_name)
    best_match = None

    for label, contact, path in _iter_named_contacts(memory):
        normalized = _normalize_alias(label)
        if normalized == target:
            return contact, label, path
        if target in normalized or normalized in target:
            best_match = (contact, label, path)

    return best_match if best_match else (None, None, None)


def update_named_contact_field(contact_name, field_name, raw_value):
    memory = load_memory()
    contact, resolved_name, contact_path = _find_named_contact(memory, contact_name)
    if not contact:
        return False, f"I could not find a saved contact matching {contact_name}."

    normalized_field = CONTACT_FIELD_ALIASES.get(_normalize_alias(field_name))
    if not normalized_field:
        return False, f"I can update email or phone for {resolved_name} right now."

    contact[normalized_field] = raw_value.strip()
    _save_memory_file(memory)
    set_memory_value(f"{contact_path}.{normalized_field}", raw_value.strip())
    return True, f"I updated {resolved_name}'s {normalized_field}."


def get_named_contact_field(contact_name, field_name):
    memory = load_memory()
    contact, resolved_name, _contact_path = _find_named_contact(memory, contact_name)
    if not contact:
        return None, f"I could not find a saved contact matching {contact_name}."

    normalized_field = CONTACT_FIELD_ALIASES.get(_normalize_alias(field_name))
    if not normalized_field:
        return None, f"I can check email or phone for {resolved_name} right now."

    value = contact.get(normalized_field)
    if _is_blank(value):
        return None, f"I do not have {resolved_name}'s {normalized_field} saved yet."

    return value, f"{resolved_name}'s {normalized_field} is {value}."


def remove_named_contact_field(contact_name, field_name):
    memory = load_memory()
    contact, resolved_name, contact_path = _find_named_contact(memory, contact_name)
    if not contact:
        return False, f"I could not find a saved contact matching {contact_name}."

    normalized_field = CONTACT_FIELD_ALIASES.get(_normalize_alias(field_name))
    if not normalized_field:
        return False, f"I can remove email or phone for {resolved_name} right now."

    if _is_blank(contact.get(normalized_field)):
        return False, f"I do not have {resolved_name}'s {normalized_field} saved yet."

    contact[normalized_field] = None
    _save_memory_file(memory)
    set_memory_value(f"{contact_path}.{normalized_field}", None)
    return True, f"I removed {resolved_name}'s {normalized_field}."


def _build_person_detail_response(title, details):
    saved_parts = []
    missing_parts = []

    for label, value in details:
        if _is_blank(value):
            missing_parts.append(label)
        else:
            saved_parts.append(f"{label} is {value}")

    if not saved_parts and missing_parts:
        return f"I do not have {title} details saved yet."

    response = f"{title}: " + ". ".join(saved_parts) + "."
    if missing_parts:
        response += " I do not have " + ", ".join(missing_parts) + " saved yet."
    return response


def _custom_memory_response(question, path, value, memory):
    if path == "personal.friends.close_friends" and isinstance(value, list):
        if not value:
            return "You do not have any close friends saved yet."

        lines = []
        for index, friend in enumerate(value, start=1):
            parts = [f"{index}. {friend.get('name', 'Unknown')}"]
            if friend.get("nickname"):
                parts.append(f"nickname {friend['nickname']}")
            if friend.get("relation"):
                parts.append(friend["relation"])
            if friend.get("since"):
                parts.append(f"since {friend['since']}")
            if friend.get("notes"):
                parts.append(friend["notes"])
            if friend.get("phone"):
                parts.append(f"phone {friend['phone']}")
            lines.append(", ".join(parts))

        return "Your close friends are: " + " | ".join(lines)

    if path == "personal.family.father":
        return _build_person_detail_response(
            "Your father's details",
            [
                ("name", value.get("name")),
                ("age", value.get("age")),
                ("date of birth", value.get("date_of_birth")),
                ("occupation", value.get("occupation")),
                ("phone", value.get("phone")),
            ],
        )

    if path == "personal.family.mother":
        return _build_person_detail_response(
            "Your mother's details",
            [
                ("name", value.get("name")),
                ("age", value.get("age")),
                ("date of birth", value.get("date_of_birth")),
                ("occupation", value.get("occupation")),
                ("phone", value.get("phone")),
            ],
        )

    if path == "personal.family.siblings" and isinstance(value, list):
        if not value:
            return "I do not have sibling details saved yet."

        parts = []
        for index, sibling in enumerate(value, start=1):
            details = [f"{index}. {sibling.get('name', 'Unknown')}"]
            if sibling.get("relation"):
                details.append(sibling["relation"])
            if sibling.get("age") is not None:
                details.append(f"age {sibling['age']}")
            if sibling.get("date_of_birth"):
                details.append(f"date of birth {sibling['date_of_birth']}")
            if sibling.get("occupation"):
                details.append(f"occupation {sibling['occupation']}")
            if sibling.get("phone"):
                details.append(f"phone {sibling['phone']}")
            parts.append(", ".join(details))
        return "Your sibling details are: " + " | ".join(parts)

    if path == "personal.social_media.github":
        github_url = _get_nested_value(memory, "personal.social_media.github_url")
        response = f"Your GitHub username is {value}."
        if github_url:
            response += f" Your GitHub URL is {github_url}."
        return response

    if path == "personal.social_media.instagram":
        instagram_url = _get_nested_value(memory, "personal.social_media.instagram_url")
        response = f"Your Instagram username is {value}."
        if instagram_url:
            response += f" Your Instagram URL is {instagram_url}."
        return response

    if path == "personal.social_media.linkedin":
        linkedin_url = _get_nested_value(memory, "personal.social_media.linkedin_url")
        response = f"Your LinkedIn id is {value}."
        if linkedin_url:
            response += f" Your LinkedIn URL is {linkedin_url}."
        return response

    if path == "personal.social_media.twitter":
        twitter_url = _get_nested_value(memory, "personal.social_media.twitter_url")
        response = f"Your Twitter username is {value}."
        if twitter_url:
            response += f" Your Twitter URL is {twitter_url}."
        return response

    if path == "personal.contact.email_primary":
        secondary = _get_nested_value(memory, "personal.contact.email_secondary")
        response = f"Your primary email address is {value}."
        if secondary:
            response += f" Your secondary email address is {secondary}."
        return response

    if path == "personal.contact.mobile_number":
        whatsapp = _get_nested_value(memory, "personal.contact.whatsapp_number")
        alternate = _get_nested_value(memory, "personal.contact.alternate_mobile_number")
        response = f"Your mobile number is {value}."
        if whatsapp:
            response += f" Your WhatsApp number is {whatsapp}."
        if alternate:
            response += f" Your alternate mobile number is {alternate}."
        return response

    if path == "personal.contact.emergency_contact":
        return _build_person_detail_response(
            "Your emergency contact",
            [
                ("name", value.get("name")),
                ("relation", value.get("relation")),
                ("phone", value.get("phone")),
            ],
        )

    if path == "personal.location":
        current_location = value.get("current_location", {})
        address = _get_nested_value(memory, "personal.contact.address")
        parts = []
        if current_location:
            location_parts = [
                current_location.get("area"),
                current_location.get("city"),
                current_location.get("state"),
                current_location.get("country"),
            ]
            parts.append(", ".join(part for part in location_parts if part))
        if address:
            parts.append(f"full address: {address}")
        return "Your location details are " + ". ".join(parts) + "."

    if path == "personal.location.current_location.city":
        area = _get_nested_value(memory, "personal.location.current_location.area")
        state = _get_nested_value(memory, "personal.location.current_location.state")
        country = _get_nested_value(memory, "personal.location.current_location.country")
        parts = [area, value, state, country]
        return "Your current location is " + ", ".join(part for part in parts if part) + "."

    if path == "personal.routine":
        return _build_person_detail_response(
            "Your routine details",
            [
                ("wake up time", value.get("wake_up_time")),
                ("sleep time", value.get("sleep_time")),
                ("study time", value.get("study_time")),
                ("work time", value.get("work_time")),
                ("best productive time", value.get("best_productive_time")),
            ],
        )

    if path == "professional.goal_timeline":
        return _build_person_detail_response(
            "Your goal timeline",
            [
                ("one year goal", value.get("one_year_goal")),
                ("five year goal", value.get("five_year_goal")),
                ("ten year goal", value.get("ten_year_goal")),
                ("overall goal", value.get("overall_goal")),
            ],
        )

    if path in {
        "professional.career_preferences.dream_company",
        "professional.career_preferences.dream_business",
        "professional.career_preferences.strongest_skill",
        "personal.favorites.favorite_football_team",
        "personal.favorites.favorite_football_player",
        "personal.favorites.favorite_cricketer",
        "personal.favorites.favorite_singer",
        "personal.favorites.actors",
        "personal.favorites.actresses",
        "personal.favorites.books",
        "personal.favorites.favorite_series",
        "personal.favorites.foods",
    }:
        label = _humanize_label(path)
        return f"Your {label} are {_format_memory_value(value)}."

    if path in {
        "professional.career_preferences.favorite_coding_language",
        "professional.career_preferences.current_job_status",
        "professional.career_preferences.preferred_job_role",
        "professional.career_preferences.expected_salary",
        "personal.favorites.favorite_browser",
        "personal.favorites.favorite_app",
        "personal.contact.portfolio_website",
    }:
        label = _humanize_label(path)
        return f"Your {label} is {_format_scalar(value)}."

    return None


# -------- SET MEMORY VALUE --------
def set_memory(path, value):
    memory = load_memory()
    _set_nested_value(memory, path, value)
    _save_memory_file(memory)
    set_memory_value(path, value)


def update_memory_field(field_name, raw_value):
    path = resolve_memory_path(field_name)
    if not path:
        return False, f"I do not know how to update {field_name} yet."

    value = _parse_value_for_path(path, raw_value)
    set_memory(path, value)
    return True, f"I updated your {field_name}."


def remove_memory_field(field_name):
    path = resolve_memory_path(field_name)
    if not path:
        return False, f"I do not know how to remove {field_name} yet."

    memory = load_memory()
    removed = _remove_nested_value(memory, path)
    if not removed:
        return False, f"I could not find {field_name} in memory."

    _save_memory_file(memory)
    set_memory_value(path, None)
    return True, f"I removed your {field_name}."


# -------- GET MEMORY VALUE --------
def get_memory(path):
    memory = load_memory()
    value = _get_nested_value(memory, path)
    if value is not None:
        return value
    return get_memory_value(path)


# -------- FLATTEN JSON --------
def flatten_dict(data, parent_key="", sep="."):
    items = {}

    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key

        if isinstance(value, dict):
            items.update(flatten_dict(value, new_key, sep))
        else:
            items[new_key] = value

    return items


# -------- SMART MEMORY SEARCH --------
def search_memory(question):
    memory = load_memory()

    if not memory:
        return None

    flat_memory = flatten_dict(memory)
    normalized_question = _normalize_question(question)

    for phrases, path in DIRECT_PATH_HINTS:
        if any(phrase in normalized_question for phrase in phrases):
            value = _get_nested_value(memory, path)
            if value is None:
                value = flat_memory.get(path)

            if value is not None:
                custom_response = _custom_memory_response(normalized_question, path, value, memory)
                if custom_response:
                    return custom_response

                field = _humanize_label(path)
                formatted_value = _format_memory_value(value)
                verb = "are" if isinstance(value, list) else "is"
                return f"Your {field} {verb} {formatted_value}."

    words = [w for w in normalized_question.split() if w not in STOP_WORDS]

    best_key = None
    best_score = float("-inf")

    for key, value in flat_memory.items():
        clean_key = key.lower().replace("_", " ")
        key_words = clean_key.replace(".", " ").split()
        score = 0

        for word in words:
            if word in key_words:
                score += 2

        if "my" in normalized_question or "who am i" in normalized_question:
            if key.startswith("personal.") or key.startswith("professional."):
                score += 3

        if words and all(word in key_words for word in words):
            score += 3

        if value is not None and not isinstance(value, (dict, list)):
            value_text = str(value).lower()
            if any(word in value_text for word in words):
                score += 1

        if score > best_score:
            best_score = score
            best_key = key

    if best_key and best_score >= 1:
        value = flat_memory[best_key]
        custom_response = _custom_memory_response(normalized_question, best_key, value, memory)
        if custom_response:
            return custom_response

        field = _humanize_label(best_key)
        formatted_value = _format_memory_value(value)
        verb = "are" if isinstance(value, list) else "is"
        return f"Your {field} {verb} {formatted_value}."

    return None
