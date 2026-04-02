import datetime
import json
import os
import re
import threading
import time
import urllib.parse
import webbrowser

import keyboard

from brain.memory_engine import get_named_contact_field, load_memory
from integrations.google_contacts_module import ensure_google_contacts_fresh, get_google_contact_field
from automation.notification_module import show_custom_popup
from utils.config import get_setting


DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data",
    "scheduled_messages.json",
)

_scheduled_whatsapp_jobs = []
_scheduled_job_lock = threading.Lock()
_scheduled_gmail_jobs = []
_scheduled_gmail_lock = threading.Lock()
_loaded_scheduled_jobs = False


def _clean_text(text):
    return " ".join(text.strip().split())


def _load_scheduled_data():
    if not os.path.exists(DATA_FILE):
        return {"whatsapp": [], "gmail": []}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return {"whatsapp": [], "gmail": []}

    data.setdefault("whatsapp", [])
    data.setdefault("gmail", [])
    return data


def _save_scheduled_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def _datetime_to_string(value):
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    return value


def _datetime_from_string(value):
    try:
        return datetime.datetime.fromisoformat(value)
    except Exception:
        return None


def _persist_current_jobs():
    with _scheduled_job_lock:
        whatsapp_jobs = [
            {
                "id": job["id"],
                "contact": job["contact"],
                "message": job["message"],
                "scheduled_for": _datetime_to_string(job["scheduled_for"]),
            }
            for job in _scheduled_whatsapp_jobs
        ]

    with _scheduled_gmail_lock:
        gmail_jobs = [
            {
                "id": job["id"],
                "recipient": job["recipient"],
                "subject": job["subject"],
                "body": job.get("body", ""),
                "scheduled_for": _datetime_to_string(job["scheduled_for"]),
            }
            for job in _scheduled_gmail_jobs
        ]

    _save_scheduled_data({"whatsapp": whatsapp_jobs, "gmail": gmail_jobs})


def _prune_expired_jobs():
    now = datetime.datetime.now()
    changed = False

    with _scheduled_job_lock:
        original_len = len(_scheduled_whatsapp_jobs)
        _scheduled_whatsapp_jobs[:] = [
            job for job in _scheduled_whatsapp_jobs if job["scheduled_for"] > now
        ]
        if len(_scheduled_whatsapp_jobs) != original_len:
            changed = True

    with _scheduled_gmail_lock:
        original_len = len(_scheduled_gmail_jobs)
        _scheduled_gmail_jobs[:] = [
            job for job in _scheduled_gmail_jobs if job["scheduled_for"] > now
        ]
        if len(_scheduled_gmail_jobs) != original_len:
            changed = True

    if changed:
        _persist_current_jobs()


def _open_url(url):
    try:
        return bool(webbrowser.open(url, new=2))
    except Exception:
        return False


def _normalize_phone_number(value):
    digits = re.sub(r"\D+", "", str(value or ""))
    if not digits:
        return None
    if digits.startswith("0"):
        digits = digits.lstrip("0")
    if len(digits) == 10:
        digits = f"91{digits}"
    return digits


def _open_whatsapp_direct_chat(contact_name, message_text=""):
    ensure_google_contacts_fresh(force=True)
    phone_value, _reply = get_named_contact_field(contact_name, "phone")
    phone_number = _normalize_phone_number(phone_value)
    if not phone_number:
        return False

    url = f"https://wa.me/{phone_number}"
    if message_text:
        url += f"?text={urllib.parse.quote(message_text)}"
    return _open_url(url)


def _open_gmail_draft(recipient="", subject="", body=""):
    url = "https://mail.google.com/mail/?view=cm&fs=1&tf=1"

    if recipient:
        url += f"&to={urllib.parse.quote(recipient)}"
    if subject:
        url += f"&su={urllib.parse.quote(subject)}"
    if body:
        url += f"&body={urllib.parse.quote(body)}"

    return _open_url(url)


def _summarize_target_name(target_text, fallback=None):
    cleaned = _clean_text(target_text)
    return cleaned or fallback or "that contact"


def preview_whatsapp_message(command):
    match = re.match(r"^(?:preview whatsapp message to|preview message to)\s+(.+?)\s+(?:saying|that)\s+(.+)$", command)
    if not match:
        return "Use this format: preview whatsapp message to appa saying I reached home."

    target = _clean_text(match.group(1))
    message_text = _clean_text(match.group(2))
    resolved_target, _ = _resolve_contact_alias(target)
    return f"WhatsApp preview for {resolved_target}: {message_text}"


def preview_email_draft(command):
    match = re.match(r"^(?:preview mail to|preview email to)\s+(.+?)\s+about\s+(.+)$", command)
    if not match:
        return "Use this format: preview mail to appa about today plan."

    target = _clean_text(match.group(1))
    topic = _clean_text(match.group(2))
    recipient, error = _resolve_email_target(target)
    if error:
        return error

    subject = topic.title()[:120]
    body = f"Hi,\n\nThis is a quick draft about {topic}.\n\nRegards,"
    if recipient:
        return f"Email preview to {target} ({recipient}) | Subject: {subject} | Body: {body}"
    return f"Email preview to {target} | Subject: {subject} | Body: {body}"


def _extract_known_contact(name_text):
    memory = load_memory()
    normalized = _clean_text(name_text).lower()
    candidates = []

    emergency = memory.get("personal", {}).get("contact", {}).get("emergency_contact", {})
    if emergency.get("name"):
        candidates.append(emergency["name"])

    for person_key in ["father", "mother"]:
        person = memory.get("personal", {}).get("family", {}).get(person_key, {})
        if person.get("name"):
            candidates.append(person["name"])

    for sibling in memory.get("personal", {}).get("family", {}).get("siblings", []):
        if sibling.get("name"):
            candidates.append(sibling["name"])

    for friend in memory.get("personal", {}).get("friends", {}).get("close_friends", []):
        if friend.get("name"):
            candidates.append(friend["name"])
        if friend.get("nickname"):
            candidates.append(friend["nickname"])

    for candidate in candidates:
        if normalized == candidate.lower():
            return candidate

    return _clean_text(name_text)


def _resolve_contact_alias(target_text):
    memory = load_memory()
    normalized = _clean_text(target_text).lower()

    alias_map = {
        "my emergency contact": memory.get("personal", {}).get("contact", {}).get("emergency_contact", {}).get("name"),
        "emergency contact": memory.get("personal", {}).get("contact", {}).get("emergency_contact", {}).get("name"),
        "my father": memory.get("personal", {}).get("family", {}).get("father", {}).get("name"),
        "my mother": memory.get("personal", {}).get("family", {}).get("mother", {}).get("name"),
        "my sister": (memory.get("personal", {}).get("family", {}).get("siblings", [{}])[0] or {}).get("name"),
        "my brother": None,
        "my best friend": (memory.get("personal", {}).get("friends", {}).get("close_friends", [{}])[0] or {}).get("name"),
        "my close friend": (memory.get("personal", {}).get("friends", {}).get("close_friends", [{}])[0] or {}).get("name"),
    }

    if normalized in alias_map and alias_map[normalized]:
        return alias_map[normalized], None

    return _extract_known_contact(target_text), None


def _resolve_email_target(target_text):
    ensure_google_contacts_fresh(force=True)
    memory = load_memory()
    normalized = _clean_text(target_text).lower()

    if normalized in {"myself", "me", "my email", "my primary email", "my mail"}:
        primary = memory.get("personal", {}).get("contact", {}).get("email_primary")
        if primary:
            return primary, None
        return None, "I could not find your primary email in memory."

    if normalized in {"my secondary email", "my alternate email", "secondary email"}:
        secondary = memory.get("personal", {}).get("contact", {}).get("email_secondary")
        if secondary:
            return secondary, None
        return None, "I could not find your secondary email in memory."

    candidates = []

    def add_candidate(name=None, nickname=None, email=None):
        if not name and not nickname:
            return
        candidates.append(
            {
                "name": _clean_text(name or ""),
                "nickname": _clean_text(nickname or ""),
                "email": _clean_text(email or ""),
            }
        )

    contact = memory.get("personal", {}).get("contact", {})
    add_candidate(
        name=memory.get("personal", {}).get("identity", {}).get("name"),
        email=contact.get("email_primary"),
    )

    emergency = contact.get("emergency_contact", {})
    add_candidate(name=emergency.get("name"), email=emergency.get("email"))

    family = memory.get("personal", {}).get("family", {})
    for person_key in ["father", "mother"]:
        person = family.get(person_key, {})
        add_candidate(name=person.get("name"), email=person.get("email"))

    for sibling in family.get("siblings", []):
        add_candidate(name=sibling.get("name"), email=sibling.get("email"))

    for friend in memory.get("personal", {}).get("friends", {}).get("close_friends", []):
        add_candidate(
            name=friend.get("name"),
            nickname=friend.get("nickname"),
            email=friend.get("email"),
        )

    for candidate in candidates:
        if normalized in {candidate["name"].lower(), candidate["nickname"].lower()}:
            if candidate["email"]:
                return candidate["email"], None
            display_name = candidate["name"] or candidate["nickname"] or target_text
            return None, f"I found {display_name}, but I do not have an email saved yet."

    google_value, google_name, google_suggestions = get_google_contact_field(target_text, "email")
    if google_value:
        return google_value, None
    if google_suggestions:
        return None, (
            f"I found multiple Google contacts for {target_text}: "
            + " | ".join(google_suggestions)
            + ". Say the exact name or set a contact alias."
        )
    if google_name:
        return None, f"I found {google_name}, but I do not have an email saved yet."

    if "@" in normalized:
        return _clean_text(target_text), None

    return _clean_text(target_text), None


def _type_after_delay(text, delay_seconds=8):
    def worker():
        time.sleep(delay_seconds)
        try:
            keyboard.write(text, delay=0.03)
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()


def _show_whatsapp_popup(contact_name, message_text, was_auto_sent):
    if not get_setting("browser.whatsapp_success_popup_enabled", True):
        return

    preview = message_text[:80]
    if len(message_text) > 80:
        preview += "..."

    if was_auto_sent:
        popup_message = (
            f"Send sequence completed for {contact_name}.\n"
            f"Please confirm it was sent in WhatsApp Web.\n\n"
            f"Message preview: {preview}"
        )
    else:
        popup_message = (
            f"Message to {contact_name} is typed and ready in WhatsApp Web.\n\n"
            f"Message preview: {preview}"
        )

    show_custom_popup(
        "WhatsApp",
        popup_message,
        dedupe_key=f"whatsapp_{contact_name.lower()}_{preview.lower()}",
        force=True,
    )


def _show_whatsapp_failure_popup(contact_name):
    if not get_setting("browser.whatsapp_success_popup_enabled", True):
        return

    show_custom_popup(
        "WhatsApp",
        f"I could not complete the WhatsApp automation for {contact_name}.",
        dedupe_key=f"whatsapp_error_{contact_name.lower()}",
        force=True,
    )


def _show_gmail_popup(recipient, subject):
    preview = (subject or "No subject")[:80]
    show_custom_popup(
        "Gmail",
        f"Gmail draft opened for {recipient}.\n\nSubject: {preview}",
        dedupe_key=f"gmail_{recipient.lower()}_{preview.lower()}",
        force=True,
    )


def _whatsapp_contact_message_after_delay(contact_name, message_text, delay_seconds=8):
    def worker():
        time.sleep(delay_seconds)
        try:
            retry_count = max(1, int(get_setting("browser.whatsapp_search_retry_count", 2)))
            retry_delay = max(
                0.4, float(get_setting("browser.whatsapp_search_retry_delay_seconds", 1.2))
            )
            auto_send = bool(get_setting("browser.whatsapp_auto_send", True))
            send_press_count = max(1, int(get_setting("browser.whatsapp_send_press_count", 1)))
            send_confirm_delay = max(
                0.2, float(get_setting("browser.whatsapp_send_confirm_delay_seconds", 0.8))
            )

            for attempt in range(retry_count):
                keyboard.send("ctrl+alt+/")
                time.sleep(0.8)
                keyboard.send("ctrl+a")
                time.sleep(0.1)
                keyboard.send("backspace")
                time.sleep(0.1)
                keyboard.write(contact_name, delay=0.03)
                time.sleep(retry_delay)
                keyboard.send("enter")
                if attempt < retry_count - 1:
                    time.sleep(retry_delay)

            time.sleep(max(0.8, retry_delay))
            keyboard.write(message_text, delay=0.03)
            if auto_send:
                time.sleep(send_confirm_delay)
                for _ in range(send_press_count):
                    keyboard.send("enter")
                    time.sleep(0.15)
            _show_whatsapp_popup(contact_name, message_text, auto_send)
        except Exception:
            _show_whatsapp_failure_popup(contact_name)

    threading.Thread(target=worker, daemon=True).start()


def _confirm_prefilled_whatsapp_after_delay(contact_name, message_text, delay_seconds=8):
    def worker():
        time.sleep(delay_seconds)
        try:
            auto_send = bool(get_setting("browser.whatsapp_auto_send", True))
            send_press_count = max(1, int(get_setting("browser.whatsapp_send_press_count", 1)))
            send_confirm_delay = max(
                0.2, float(get_setting("browser.whatsapp_send_confirm_delay_seconds", 0.8))
            )
            if auto_send:
                time.sleep(send_confirm_delay)
                for _ in range(send_press_count):
                    keyboard.send("enter")
                    time.sleep(0.15)
            _show_whatsapp_popup(contact_name, message_text, auto_send)
        except Exception:
            _show_whatsapp_failure_popup(contact_name)

    threading.Thread(target=worker, daemon=True).start()


def _open_whatsapp_and_queue_message(contact_name, message_text, launch_delay=8):
    launch_delay = get_setting("browser.whatsapp_load_delay_seconds", launch_delay)
    if not _open_url("https://web.whatsapp.com/"):
        return False

    _whatsapp_contact_message_after_delay(contact_name, message_text, delay_seconds=launch_delay)
    return True


def _open_gmail_and_queue_draft(recipient, subject, body, launch_delay=8):
    launch_delay = get_setting("browser.gmail_load_delay_seconds", launch_delay)
    if not _open_gmail_draft(recipient, subject, body):
        return False
    time.sleep(0)
    return True


def _format_schedule_time(dt):
    return dt.strftime("%d %B %Y %I:%M %p")


def _parse_send_later(command):
    if " saying " not in command:
        return None

    before_message, message_part = command.split(" saying ", 1)
    message_text = _clean_text(message_part)

    match = re.match(
        r"^(?:schedule whatsapp message to|send whatsapp message to)\s+(.+?)\s+after\s+(\d+)\s+minutes?$",
        before_message,
    )
    if match:
        minutes = int(match.group(2))
        return {
            "contact": _extract_known_contact(match.group(1)),
            "message": message_text,
            "delay_seconds": minutes * 60,
            "scheduled_for": datetime.datetime.now() + datetime.timedelta(minutes=minutes),
        }

    match = re.match(
        r"^(?:schedule whatsapp message to|send whatsapp message to)\s+(.+?)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$",
        before_message,
    )
    if not match:
        return None

    contact_name = _extract_known_contact(match.group(1))
    hour = int(match.group(2))
    minute = int(match.group(3) or 0)
    meridiem = (match.group(4) or "").lower()

    if meridiem:
        if hour == 12:
            hour = 0
        if meridiem == "pm":
            hour += 12

    now = datetime.datetime.now()
    scheduled_for = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if scheduled_for <= now:
        scheduled_for += datetime.timedelta(days=1)

    return {
        "contact": contact_name,
        "message": message_text,
        "delay_seconds": int((scheduled_for - now).total_seconds()),
        "scheduled_for": scheduled_for,
    }


def _parse_scheduled_gmail_command(command):
    if " after " in command:
        prefix_match = re.match(
            r"^(?:schedule gmail draft to|send gmail draft to)\s+(.+?)\s+after\s+(\d+)\s+minutes?\s+subject\s+(.+?)\s+body\s+(.+)$",
            command,
        )
        if not prefix_match:
            return None

        recipient, recipient_error = _resolve_email_target(prefix_match.group(1))
        if recipient_error:
            return {"error": recipient_error}

        minutes = int(prefix_match.group(2))
        return {
            "recipient": recipient,
            "subject": _clean_text(prefix_match.group(3)),
            "body": _clean_text(prefix_match.group(4)),
            "delay_seconds": minutes * 60,
            "scheduled_for": datetime.datetime.now() + datetime.timedelta(minutes=minutes),
        }

    prefix_match = re.match(
        r"^(?:schedule gmail draft to|send gmail draft to)\s+(.+?)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+subject\s+(.+?)\s+body\s+(.+)$",
        command,
    )
    if not prefix_match:
        return None

    recipient, recipient_error = _resolve_email_target(prefix_match.group(1))
    if recipient_error:
        return {"error": recipient_error}

    hour = int(prefix_match.group(2))
    minute = int(prefix_match.group(3) or 0)
    meridiem = (prefix_match.group(4) or "").lower()

    if meridiem:
        if hour == 12:
            hour = 0
        if meridiem == "pm":
            hour += 12

    now = datetime.datetime.now()
    scheduled_for = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if scheduled_for <= now:
        scheduled_for += datetime.timedelta(days=1)

    return {
        "recipient": recipient,
        "subject": _clean_text(prefix_match.group(5)),
        "body": _clean_text(prefix_match.group(6)),
        "delay_seconds": int((scheduled_for - now).total_seconds()),
        "scheduled_for": scheduled_for,
    }


def _enqueue_whatsapp_job_with_id(job_id, contact_name, message_text, scheduled_for, delay_seconds):
    def worker():
        time.sleep(max(1, delay_seconds))
        _open_whatsapp_and_queue_message(contact_name, message_text)
        with _scheduled_job_lock:
            _scheduled_whatsapp_jobs[:] = [
                job for job in _scheduled_whatsapp_jobs if job["id"] != job_id
            ]
        _persist_current_jobs()

    with _scheduled_job_lock:
        _scheduled_whatsapp_jobs.append(
            {
                "id": job_id,
                "contact": contact_name,
                "message": message_text,
                "scheduled_for": scheduled_for,
            }
        )
    _persist_current_jobs()
    threading.Thread(target=worker, daemon=True).start()
    return job_id


def _enqueue_whatsapp_job(contact_name, message_text, scheduled_for, delay_seconds):
    job_id = int(time.time() * 1000)
    return _enqueue_whatsapp_job_with_id(
        job_id, contact_name, message_text, scheduled_for, delay_seconds
    )


def _enqueue_gmail_job_with_id(job_id, recipient, subject, body, scheduled_for, delay_seconds):
    def worker():
        time.sleep(max(1, delay_seconds))
        _open_gmail_and_queue_draft(recipient, subject, body)
        with _scheduled_gmail_lock:
            _scheduled_gmail_jobs[:] = [
                job for job in _scheduled_gmail_jobs if job["id"] != job_id
            ]
        _persist_current_jobs()

    with _scheduled_gmail_lock:
        _scheduled_gmail_jobs.append(
            {
                "id": job_id,
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "scheduled_for": scheduled_for,
            }
        )
    _persist_current_jobs()
    threading.Thread(target=worker, daemon=True).start()
    return job_id


def _enqueue_gmail_job(recipient, subject, body, scheduled_for, delay_seconds):
    job_id = int(time.time() * 1000)
    return _enqueue_gmail_job_with_id(
        job_id, recipient, subject, body, scheduled_for, delay_seconds
    )


def restore_scheduled_jobs():
    global _loaded_scheduled_jobs

    if _loaded_scheduled_jobs:
        return False

    data = _load_scheduled_data()
    now = datetime.datetime.now()

    for job in data.get("whatsapp", []):
        scheduled_for = _datetime_from_string(job.get("scheduled_for"))
        if not scheduled_for or scheduled_for <= now:
            continue
        delay_seconds = int((scheduled_for - now).total_seconds())
        _enqueue_whatsapp_job_with_id(
            job.get("id", int(time.time() * 1000)),
            job.get("contact", ""),
            job.get("message", ""),
            scheduled_for,
            delay_seconds,
        )

    for job in data.get("gmail", []):
        scheduled_for = _datetime_from_string(job.get("scheduled_for"))
        if not scheduled_for or scheduled_for <= now:
            continue
        delay_seconds = int((scheduled_for - now).total_seconds())
        _enqueue_gmail_job_with_id(
            job.get("id", int(time.time() * 1000)),
            job.get("recipient", ""),
            job.get("subject", ""),
            job.get("body", ""),
            scheduled_for,
            delay_seconds,
        )

    _loaded_scheduled_jobs = True
    _prune_expired_jobs()
    _persist_current_jobs()
    return True


def schedule_whatsapp_message(command):
    parsed = _parse_send_later(command)
    if not parsed:
        return None

    contact_name = parsed["contact"]
    message_text = parsed["message"]
    delay_seconds = parsed["delay_seconds"]
    scheduled_for = parsed["scheduled_for"]

    if not contact_name or not message_text:
        return "Tell me the WhatsApp contact and the message you want to schedule."

    _enqueue_whatsapp_job(contact_name, message_text, scheduled_for, delay_seconds)
    return (
        f"Okay, I will send your WhatsApp message to {contact_name} at "
        f"{_format_schedule_time(scheduled_for)}."
    )


def list_scheduled_whatsapp_messages():
    _prune_expired_jobs()
    with _scheduled_job_lock:
        jobs = sorted(_scheduled_whatsapp_jobs, key=lambda item: item["scheduled_for"])

    if not jobs:
        return "You do not have any scheduled WhatsApp messages right now."

    lines = []
    for index, job in enumerate(jobs[:10], start=1):
        lines.append(
            f"{index}. to {job['contact']} at {_format_schedule_time(job['scheduled_for'])}"
        )
    return "Scheduled WhatsApp messages: " + " | ".join(lines)


def cancel_scheduled_whatsapp_message(command):
    _prune_expired_jobs()
    raw = (
        command.replace("cancel scheduled whatsapp message", "", 1)
        .replace("delete scheduled whatsapp message", "", 1)
        .strip()
    )
    if not raw.isdigit():
        return "Tell me the scheduled WhatsApp message number to cancel."

    index = int(raw) - 1
    with _scheduled_job_lock:
        jobs = sorted(_scheduled_whatsapp_jobs, key=lambda item: item["scheduled_for"])
        if index < 0 or index >= len(jobs):
            return "That scheduled WhatsApp message number does not exist."
        job_id = jobs[index]["id"]
        removed = jobs[index]
        _scheduled_whatsapp_jobs[:] = [
            job for job in _scheduled_whatsapp_jobs if job["id"] != job_id
        ]
    _persist_current_jobs()
    return (
        f"Cancelled scheduled WhatsApp message to {removed['contact']} at "
        f"{_format_schedule_time(removed['scheduled_for'])}."
    )


def schedule_gmail_draft(command):
    parsed = _parse_scheduled_gmail_command(command)
    if not parsed:
        return (
            "Use this format: schedule gmail draft to my email after 15 minutes subject Test body Hello "
            "or send gmail draft to my email at 10:30 pm subject Test body Hello."
        )

    if parsed.get("error"):
        return parsed["error"]

    _enqueue_gmail_job(
        parsed["recipient"],
        parsed["subject"],
        parsed["body"],
        parsed["scheduled_for"],
        parsed["delay_seconds"],
    )
    return (
        f"Okay, I will open the Gmail draft to {parsed['recipient']} at "
        f"{_format_schedule_time(parsed['scheduled_for'])}."
    )


def list_scheduled_gmail_drafts():
    _prune_expired_jobs()
    with _scheduled_gmail_lock:
        jobs = sorted(_scheduled_gmail_jobs, key=lambda item: item["scheduled_for"])

    if not jobs:
        return "You do not have any scheduled Gmail drafts right now."

    lines = []
    for index, job in enumerate(jobs[:10], start=1):
        lines.append(
            f"{index}. to {job['recipient']} at {_format_schedule_time(job['scheduled_for'])} subject {job['subject']}"
        )
    return "Scheduled Gmail drafts: " + " | ".join(lines)


def cancel_scheduled_gmail_draft(command):
    _prune_expired_jobs()
    raw = (
        command.replace("cancel scheduled gmail draft", "", 1)
        .replace("delete scheduled gmail draft", "", 1)
        .strip()
    )
    if not raw.isdigit():
        return "Tell me the scheduled Gmail draft number to cancel."

    index = int(raw) - 1
    with _scheduled_gmail_lock:
        jobs = sorted(_scheduled_gmail_jobs, key=lambda item: item["scheduled_for"])
        if index < 0 or index >= len(jobs):
            return "That scheduled Gmail draft number does not exist."
        job_id = jobs[index]["id"]
        removed = jobs[index]
        _scheduled_gmail_jobs[:] = [
            job for job in _scheduled_gmail_jobs if job["id"] != job_id
        ]
    _persist_current_jobs()
    return (
        f"Cancelled scheduled Gmail draft to {removed['recipient']} at "
        f"{_format_schedule_time(removed['scheduled_for'])}."
    )


def open_whatsapp_and_type(command):
    text = command.replace("open whatsapp web and type", "", 1).strip()
    text = _clean_text(text)

    if not text:
        return "Tell me what you want to type in WhatsApp Web."

    load_delay = get_setting("browser.whatsapp_load_delay_seconds", 8)
    if not _open_url("https://web.whatsapp.com/"):
        return "I could not open WhatsApp Web right now."

    _type_after_delay(text, delay_seconds=load_delay)
    return f"Opening WhatsApp Web. I will type your message in about {load_delay} seconds."


def type_in_whatsapp(command):
    text = command.replace("type in whatsapp", "", 1).strip()
    text = _clean_text(text)

    if not text:
        return "Tell me what you want to type in WhatsApp."

    _type_after_delay(text, delay_seconds=1)
    return "I will type your WhatsApp message in the current focused box now."


def open_gmail_and_type(command):
    text = command.replace("open gmail and type", "", 1).strip()
    text = _clean_text(text)

    if not text:
        return "Tell me what you want to type in Gmail."

    load_delay = get_setting("browser.gmail_load_delay_seconds", 8)
    compose_url = "https://mail.google.com/mail/?view=cm&fs=1&tf=1"
    if not _open_url(compose_url):
        return "I could not open Gmail compose right now."

    _type_after_delay(text, delay_seconds=load_delay)
    return f"Opening Gmail compose. I will type your message in about {load_delay} seconds."


def draft_gmail(command):
    text = command.replace("draft gmail", "", 1).strip()
    text = _clean_text(text)

    if not text:
        return "Tell me what you want in the Gmail draft."

    body = urllib.parse.quote(text)
    compose_url = f"https://mail.google.com/mail/?view=cm&fs=1&tf=1&body={body}"
    if _open_url(compose_url):
        return (
            "Opening a Gmail draft with your message. "
            f"Give it about {get_setting('browser.gmail_load_delay_seconds', 8)} seconds to load."
        )
    return "I could not open Gmail draft right now."


def smart_gmail_draft(command):
    text = command
    for prefix in ["draft gmail to", "gmail draft to", "compose gmail to"]:
        if command.startswith(prefix):
            text = command.replace(prefix, "", 1).strip()
            break

    if " subject " not in text or " body " not in text:
        return (
            "Use this format: draft gmail to someone@example.com subject Your subject body Your message."
        )

    to_part, remainder = text.split(" subject ", 1)
    subject_part, body_part = remainder.split(" body ", 1)

    recipient, recipient_error = _resolve_email_target(to_part)
    subject = _clean_text(subject_part)
    body = _clean_text(body_part)

    if recipient_error:
        return recipient_error

    if not recipient or not subject or not body:
        return (
            "Please give recipient, subject, and body. "
            "Example: draft gmail to someone@example.com subject Meeting body We will meet at 5 PM."
        )

    if _open_gmail_draft(recipient, subject, body):
        delay = get_setting("browser.gmail_load_delay_seconds", 8)
        return f"Opening Gmail draft to {recipient} with your subject and body. Give it about {delay} seconds to load."
    return "I could not open the smart Gmail draft right now."


def draft_professional_email(command):
    text = command
    prefixes = [
        "draft professional email to",
        "compose professional email to",
        "write professional mail to",
    ]
    for prefix in prefixes:
        if command.startswith(prefix):
            text = command.replace(prefix, "", 1).strip()
            break

    if " about " not in text:
        return (
            "Use this format: draft professional email to someone@example.com about project update."
        )

    recipient_part, topic_part = text.split(" about ", 1)
    recipient, recipient_error = _resolve_email_target(recipient_part)
    topic = _clean_text(topic_part)

    if recipient_error:
        return recipient_error

    if not recipient or not topic:
        return "Tell me the recipient and the topic for the professional email."

    subject = f"Regarding {topic.title()}"
    body = (
        "Dear Sir or Madam,\n\n"
        f"I hope you are doing well. I am writing regarding {topic}. "
        "Please let me know a convenient time to discuss this further.\n\n"
        "Thank you for your time and consideration.\n\n"
        "Best regards,\n"
        "Hari Hara Sudhan"
    )

    if _open_gmail_draft(recipient, subject, body):
        return (
            f"Opening a professional Gmail draft to {recipient} about {topic}. "
            f"Give it about {get_setting('browser.gmail_load_delay_seconds', 8)} seconds to load."
        )
    return "I could not open the professional Gmail draft right now."


def draft_leave_email(command):
    text = command
    prefixes = [
        "draft leave mail to",
        "draft leave email to",
        "write leave mail to",
    ]
    for prefix in prefixes:
        if command.startswith(prefix):
            text = command.replace(prefix, "", 1).strip()
            break

    if " for " not in text:
        return (
            "Use this format: draft leave mail to manager@example.com for sick leave tomorrow."
        )

    recipient_part, reason_part = text.split(" for ", 1)
    recipient, recipient_error = _resolve_email_target(recipient_part)
    reason = _clean_text(reason_part)

    if recipient_error:
        return recipient_error

    if not recipient or not reason:
        return "Tell me the recipient and the leave reason."

    subject = "Leave Request"
    body = (
        "Dear Sir or Madam,\n\n"
        f"I would like to request leave for {reason}. "
        "Kindly approve my request. I will make sure to complete or hand over any important work.\n\n"
        "Thank you for your understanding.\n\n"
        "Best regards,\n"
        "Hari Hara Sudhan"
    )

    if _open_gmail_draft(recipient, subject, body):
        return (
            f"Opening a leave request mail draft to {recipient}. "
            f"Give it about {get_setting('browser.gmail_load_delay_seconds', 8)} seconds to load."
        )
    return "I could not open the leave mail draft right now."


def draft_follow_up_email(command):
    text = command
    prefixes = [
        "draft follow up mail to",
        "draft follow-up mail to",
        "write follow up email to",
    ]
    for prefix in prefixes:
        if command.startswith(prefix):
            text = command.replace(prefix, "", 1).strip()
            break

    if " about " not in text:
        return (
            "Use this format: draft follow up mail to someone@example.com about interview status."
        )

    recipient_part, topic_part = text.split(" about ", 1)
    recipient, recipient_error = _resolve_email_target(recipient_part)
    topic = _clean_text(topic_part)

    if recipient_error:
        return recipient_error

    if not recipient or not topic:
        return "Tell me the recipient and the follow-up topic."

    subject = f"Follow-up on {topic.title()}"
    body = (
        "Dear Sir or Madam,\n\n"
        f"I hope you are doing well. I am following up regarding {topic}. "
        "I would appreciate any update when convenient.\n\n"
        "Thank you for your time.\n\n"
        "Best regards,\n"
        "Hari Hara Sudhan"
    )

    if _open_gmail_draft(recipient, subject, body):
        return (
            f"Opening a follow-up Gmail draft to {recipient} about {topic}. "
            f"Give it about {get_setting('browser.gmail_load_delay_seconds', 8)} seconds to load."
        )
    return "I could not open the follow-up Gmail draft right now."


def draft_job_application_email(command):
    text = command
    prefixes = [
        "draft job application mail to",
        "draft job application email to",
        "write job application mail to",
    ]
    for prefix in prefixes:
        if command.startswith(prefix):
            text = command.replace(prefix, "", 1).strip()
            break

    if " for " not in text:
        return (
            "Use this format: draft job application mail to hr@example.com for technical support engineer."
        )

    recipient_part, role_part = text.split(" for ", 1)
    recipient, recipient_error = _resolve_email_target(recipient_part)
    role = _clean_text(role_part)

    if recipient_error:
        return recipient_error

    if not recipient or not role:
        return "Tell me the recipient and the role for the job application."

    subject = f"Application for {role.title()}"
    body = (
        "Dear Hiring Team,\n\n"
        f"I hope you are doing well. I am writing to express my interest in the {role} role. "
        "I believe my experience in technical support, troubleshooting, and problem solving would allow me to contribute effectively.\n\n"
        "Please find my application for your consideration. I would be glad to discuss my profile further.\n\n"
        "Thank you for your time.\n\n"
        "Best regards,\n"
        "Hari Hara Sudhan"
    )

    if _open_gmail_draft(recipient, subject, body):
        return (
            f"Opening a job application Gmail draft to {recipient} for the {role} role. "
            f"Give it about {get_setting('browser.gmail_load_delay_seconds', 8)} seconds to load."
        )
    return "I could not open the job application Gmail draft right now."


def draft_meeting_request_email(command):
    text = command
    prefixes = [
        "draft meeting request mail to",
        "draft meeting request email to",
        "write meeting request mail to",
    ]
    for prefix in prefixes:
        if command.startswith(prefix):
            text = command.replace(prefix, "", 1).strip()
            break

    if " about " not in text:
        return (
            "Use this format: draft meeting request mail to manager@example.com about project planning."
        )

    recipient_part, topic_part = text.split(" about ", 1)
    recipient, recipient_error = _resolve_email_target(recipient_part)
    topic = _clean_text(topic_part)

    if recipient_error:
        return recipient_error

    if not recipient or not topic:
        return "Tell me the recipient and the meeting topic."

    subject = f"Meeting Request Regarding {topic.title()}"
    body = (
        "Dear Sir or Madam,\n\n"
        f"I hope you are doing well. I would like to request a meeting regarding {topic}. "
        "Please let me know a convenient time for you to discuss this.\n\n"
        "Thank you for your time.\n\n"
        "Best regards,\n"
        "Hari Hara Sudhan"
    )

    if _open_gmail_draft(recipient, subject, body):
        return (
            f"Opening a meeting request Gmail draft to {recipient} about {topic}. "
            f"Give it about {get_setting('browser.gmail_load_delay_seconds', 8)} seconds to load."
        )
    return "I could not open the meeting request Gmail draft right now."


def draft_thank_you_email(command):
    text = command
    prefixes = [
        "draft thank you mail to",
        "draft thank you email to",
        "write thank you mail to",
    ]
    for prefix in prefixes:
        if command.startswith(prefix):
            text = command.replace(prefix, "", 1).strip()
            break

    if " for " not in text:
        return (
            "Use this format: draft thank you mail to manager@example.com for the interview opportunity."
        )

    recipient_part, reason_part = text.split(" for ", 1)
    recipient, recipient_error = _resolve_email_target(recipient_part)
    reason = _clean_text(reason_part)

    if recipient_error:
        return recipient_error

    if not recipient or not reason:
        return "Tell me the recipient and the reason for the thank you mail."

    subject = "Thank You"
    body = (
        "Dear Sir or Madam,\n\n"
        f"Thank you for {reason}. I truly appreciate your time and support. "
        "It was a valuable experience, and I am grateful for the opportunity.\n\n"
        "Thanks again.\n\n"
        "Best regards,\n"
        "Hari Hara Sudhan"
    )

    if _open_gmail_draft(recipient, subject, body):
        return (
            f"Opening a thank you Gmail draft to {recipient}. "
            f"Give it about {get_setting('browser.gmail_load_delay_seconds', 8)} seconds to load."
        )
    return "I could not open the thank you Gmail draft right now."


def whatsapp_message_contact(command):
    text = command
    prefixes = [
        "message on whatsapp",
        "send whatsapp message to",
        "open whatsapp and message",
    ]
    for prefix in prefixes:
        if command.startswith(prefix):
            text = command.replace(prefix, "", 1).strip()
            break

    if " saying " in text:
        contact_part, message_part = text.split(" saying ", 1)
    elif " message " in text:
        contact_part, message_part = text.split(" message ", 1)
    else:
        return "Use this format: send whatsapp message to Jeevan saying hello machi."

    contact_name = _extract_known_contact(contact_part)
    message_text = _clean_text(message_part)

    if not contact_name or not message_text:
        return "Tell me the contact name and the message text."

    load_delay = get_setting("browser.whatsapp_load_delay_seconds", 8)
    opened_direct = _open_whatsapp_direct_chat(contact_name, message_text)
    if not opened_direct and not _open_url("https://web.whatsapp.com/"):
        return "I could not open WhatsApp Web right now."

    if opened_direct:
        auto_send = get_setting("browser.whatsapp_auto_send", True)
        if auto_send:
            _confirm_prefilled_whatsapp_after_delay(contact_name, message_text, delay_seconds=load_delay)
        return (
            f"Opening direct WhatsApp chat for {contact_name}. "
            f"The message is prefilled and I will try to send it in about {load_delay} seconds."
        )

    _whatsapp_contact_message_after_delay(contact_name, message_text, delay_seconds=load_delay)
    return (
        f"Opening WhatsApp Web. I will search for {contact_name} and send your message "
        f"in about {load_delay} seconds. If search misses, I will retry automatically."
    )


def memory_whatsapp_message(command):
    match = re.match(r"^(?:message|whatsapp)\s+(.+?)\s+about\s+(.+)$", command)
    if not match:
        return "Use this format: message Jeevan about the meeting moved to 6 PM."

    target_text = re.sub(r"^to\s+", "", match.group(1).strip(), flags=re.IGNORECASE)
    contact_name = _extract_known_contact(target_text)
    topic = _clean_text(match.group(2))
    if not contact_name or not topic:
        return "Tell me the contact and what message you want to send."

    message_text = topic[0].upper() + topic[1:] if topic else topic
    load_delay = get_setting("browser.whatsapp_load_delay_seconds", 8)
    opened_direct = _open_whatsapp_direct_chat(contact_name, message_text)
    if not opened_direct and not _open_url("https://web.whatsapp.com/"):
        return "I could not open WhatsApp Web right now."

    if opened_direct:
        auto_send = get_setting("browser.whatsapp_auto_send", True)
        if auto_send:
            _confirm_prefilled_whatsapp_after_delay(contact_name, message_text, delay_seconds=load_delay)
        return (
            f"Opening direct WhatsApp chat for {contact_name}. "
            f"The message is prefilled and I will try to send it in about {load_delay} seconds."
        )

    _whatsapp_contact_message_after_delay(contact_name, message_text, delay_seconds=load_delay)
    return f"Opening WhatsApp Web. I will message {contact_name} about {topic} in about {load_delay} seconds."


def relationship_whatsapp_message(command):
    match = re.match(
        r"^(?:message|whatsapp)\s+(my emergency contact|emergency contact|my father|my mother|my sister|my best friend|my close friend)\s+about\s+(.+)$",
        command,
    )
    if not match:
        return "Use this format: message my emergency contact about reach home safely."

    contact_name, error = _resolve_contact_alias(match.group(1))
    if error:
        return error

    topic = _clean_text(match.group(2))
    if not contact_name or not topic:
        return "Tell me the relationship shortcut and what message you want to send."

    load_delay = get_setting("browser.whatsapp_load_delay_seconds", 8)
    opened_direct = _open_whatsapp_direct_chat(contact_name, topic)
    if not opened_direct and not _open_url("https://web.whatsapp.com/"):
        return "I could not open WhatsApp Web right now."

    if opened_direct:
        auto_send = get_setting("browser.whatsapp_auto_send", True)
        if auto_send:
            _confirm_prefilled_whatsapp_after_delay(contact_name, topic, delay_seconds=load_delay)
        return f"Opening direct WhatsApp chat for {contact_name}. I will try to send it in about {load_delay} seconds."

    _whatsapp_contact_message_after_delay(contact_name, topic, delay_seconds=load_delay)
    return f"Opening WhatsApp Web. I will message {contact_name} in about {load_delay} seconds."


def quick_whatsapp_message(command):
    if " about " in command:
        return None
    match = re.match(
        r"^(?:message|whatsapp)\s+(.+?)\s+(?:saying|that)\s+(.+)$",
        command,
    )
    if not match:
        return None

    target_text = re.sub(r"^to\s+", "", match.group(1).strip(), flags=re.IGNORECASE)
    contact_name, error = _resolve_contact_alias(target_text)
    if error:
        return error

    message_text = _clean_text(match.group(2))
    if not contact_name or not message_text:
        return "Tell me who to message and what I should say."

    load_delay = get_setting("browser.whatsapp_load_delay_seconds", 8)
    opened_direct = _open_whatsapp_direct_chat(contact_name, message_text)
    if not opened_direct and not _open_url("https://web.whatsapp.com/"):
        return "I could not open WhatsApp Web right now."

    if opened_direct:
        auto_send = get_setting("browser.whatsapp_auto_send", True)
        if auto_send:
            _confirm_prefilled_whatsapp_after_delay(contact_name, message_text, delay_seconds=load_delay)
        return (
            f"Opening WhatsApp for {_summarize_target_name(contact_name)}. "
            f"I prefilled your message and will try to send it in about {load_delay} seconds."
        )

    _whatsapp_contact_message_after_delay(contact_name, message_text, delay_seconds=load_delay)
    return (
        f"Opening WhatsApp Web for {_summarize_target_name(contact_name)}. "
        f"I will search the chat and type your message in about {load_delay} seconds."
    )


def memory_email_shortcut(command):
    match = re.match(r"^(?:mail|email)\s+(.+?)\s+about\s+(.+)$", command)
    if not match:
        return "Use this format: mail my primary email about project update."

    target_text = re.sub(r"^to\s+", "", match.group(1).strip(), flags=re.IGNORECASE)
    recipient, recipient_error = _resolve_email_target(target_text)
    topic = _clean_text(match.group(2))

    if recipient_error:
        return recipient_error
    if not recipient or not topic:
        return "Tell me who to mail and what it should be about."

    subject = topic.title()
    body = (
        "Hello,\n\n"
        f"This is regarding {topic}. "
        "Please review it when convenient.\n\n"
        "Regards,\n"
        "Hari Hara Sudhan"
    )

    if _open_gmail_draft(recipient, subject, body):
        delay = get_setting("browser.gmail_load_delay_seconds", 8)
        _show_gmail_popup(recipient, subject)
        return f"Opening a Gmail draft to {recipient} about {topic}. It should load in about {delay} seconds."
    return "I could not open the email draft right now."


def relationship_email_shortcut(command):
    match = re.match(
        r"^(?:mail|email)\s+(my emergency contact|emergency contact|my father|my mother|my sister|my best friend|my close friend)\s+about\s+(.+)$",
        command,
    )
    if not match:
        return "Use this format: mail my father about today's plan."

    relation_text = match.group(1)
    topic = _clean_text(match.group(2))
    resolved_target, _error = _resolve_contact_alias(relation_text)
    recipient, recipient_error = _resolve_email_target(resolved_target or relation_text)

    if recipient_error:
        return recipient_error
    if not recipient or not topic:
        return "Tell me who to mail and what it should be about."

    subject = topic.title()
    body = (
        "Hello,\n\n"
        f"This is regarding {topic}. "
        "Please check it when convenient.\n\n"
        "Regards,\n"
        "Hari Hara Sudhan"
    )

    if _open_gmail_draft(recipient, subject, body):
        delay = get_setting("browser.gmail_load_delay_seconds", 8)
        _show_gmail_popup(recipient, subject)
        return f"Opening a Gmail draft to {recipient} about {topic}. It should load in about {delay} seconds."
    return "I could not open the email draft right now."


def quick_email_shortcut(command):
    if " about " in command:
        return None
    match = re.match(r"^(?:mail|email)\s+(.+?)\s+(.+)$", command)
    if not match:
        return None

    target_text = _clean_text(match.group(1))
    remainder = _clean_text(match.group(2))
    recipient, recipient_error = _resolve_email_target(target_text)

    if recipient_error:
        return recipient_error
    if not recipient or not remainder:
        return "Tell me who to mail and what to include."

    memory = load_memory()
    portfolio = memory.get("personal", {}).get("contact", {}).get("portfolio_website")
    github = memory.get("personal", {}).get("social_media", {}).get("github_url")

    if "resume link" in remainder:
        body = (
            "Hello,\n\n"
            "Here is my profile link for reference:\n"
            f"{portfolio or github or 'Link not saved'}\n\n"
            "Regards,\nHari Hara Sudhan"
        )
        subject = "Profile Link"
    else:
        body = f"Hello,\n\n{remainder}\n\nRegards,\nHari Hara Sudhan"
        subject = remainder[:60].title()

    if _open_gmail_draft(recipient, subject, body):
        delay = get_setting("browser.gmail_load_delay_seconds", 8)
        _show_gmail_popup(recipient, subject)
        return (
            f"Opening a Gmail draft for {_summarize_target_name(target_text, recipient)}. "
            f"It should load in about {delay} seconds."
        )
    return "I could not open the email draft right now."
