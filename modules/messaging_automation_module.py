import threading
import time
import urllib.parse
import webbrowser

import keyboard
from brain.memory_engine import load_memory


def _clean_text(text):
    return " ".join(text.strip().split())


def _open_url(url):
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


def _open_gmail_draft(recipient="", subject="", body=""):
    url = "https://mail.google.com/mail/?view=cm&fs=1&tf=1"

    if recipient:
        url += f"&to={urllib.parse.quote(recipient)}"
    if subject:
        url += f"&su={urllib.parse.quote(subject)}"
    if body:
        url += f"&body={urllib.parse.quote(body)}"

    return _open_url(url)


def _extract_known_contact(name_text):
    memory = load_memory()
    normalized = _clean_text(name_text).lower()
    candidates = []

    emergency = (
        memory.get("personal", {})
        .get("contact", {})
        .get("emergency_contact", {})
    )
    if emergency.get("name"):
        candidates.append(emergency["name"])

    for person_key in ["father", "mother"]:
        person = (
            memory.get("personal", {})
            .get("family", {})
            .get(person_key, {})
        )
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


def _type_after_delay(text, delay_seconds=8):
    def worker():
        time.sleep(delay_seconds)
        keyboard.write(text, delay=0.03)

    threading.Thread(target=worker, daemon=True).start()


def _whatsapp_contact_message_after_delay(contact_name, message_text, delay_seconds=8):
    def worker():
        time.sleep(delay_seconds)
        try:
            keyboard.send("ctrl+alt+/")
            time.sleep(0.8)
            keyboard.write(contact_name, delay=0.03)
            time.sleep(1.2)
            keyboard.send("enter")
            time.sleep(1.0)
            keyboard.write(message_text, delay=0.03)
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()


def open_whatsapp_and_type(command):
    text = command.replace("open whatsapp web and type", "", 1).strip()
    text = _clean_text(text)

    if not text:
        return "Tell me what you want to type in WhatsApp Web."

    if not _open_url("https://web.whatsapp.com/"):
        return "I could not open WhatsApp Web right now."

    _type_after_delay(text, delay_seconds=8)
    return "Opening WhatsApp Web and I will type your message in a few seconds."


def type_in_whatsapp(command):
    text = command.replace("type in whatsapp", "", 1).strip()
    text = _clean_text(text)

    if not text:
        return "Tell me what you want to type in WhatsApp."

    _type_after_delay(text, delay_seconds=1)
    return "I will type your WhatsApp message now."


def open_gmail_and_type(command):
    text = command.replace("open gmail and type", "", 1).strip()
    text = _clean_text(text)

    if not text:
        return "Tell me what you want to type in Gmail."

    compose_url = "https://mail.google.com/mail/?view=cm&fs=1&tf=1"
    if not _open_url(compose_url):
        return "I could not open Gmail compose right now."

    _type_after_delay(text, delay_seconds=8)
    return "Opening Gmail compose and I will type your message in a few seconds."


def draft_gmail(command):
    text = command.replace("draft gmail", "", 1).strip()
    text = _clean_text(text)

    if not text:
        return "Tell me what you want in the Gmail draft."

    body = urllib.parse.quote(text)
    compose_url = f"https://mail.google.com/mail/?view=cm&fs=1&tf=1&body={body}"
    if _open_url(compose_url):
        return "Opening a Gmail draft with your message."
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

    recipient = _clean_text(to_part)
    subject = _clean_text(subject_part)
    body = _clean_text(body_part)

    if not recipient or not subject or not body:
        return (
            "Please give recipient, subject, and body. "
            "Example: draft gmail to someone@example.com subject Meeting body We will meet at 5 PM."
        )

    if _open_gmail_draft(recipient, subject, body):
        return f"Opening Gmail draft to {recipient} with your subject and body."
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
    recipient = _clean_text(recipient_part)
    topic = _clean_text(topic_part)

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
        return f"Opening a professional Gmail draft to {recipient} about {topic}."
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
    recipient = _clean_text(recipient_part)
    reason = _clean_text(reason_part)

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
        return f"Opening a leave request mail draft to {recipient}."
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
    recipient = _clean_text(recipient_part)
    topic = _clean_text(topic_part)

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
        return f"Opening a follow-up Gmail draft to {recipient} about {topic}."
    return "I could not open the follow-up Gmail draft right now."


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
        return (
            "Use this format: send whatsapp message to Jeevan saying hello machi."
        )

    contact_name = _extract_known_contact(contact_part)
    message_text = _clean_text(message_part)

    if not contact_name or not message_text:
        return "Tell me the contact name and the message text."

    if not _open_url("https://web.whatsapp.com/"):
        return "I could not open WhatsApp Web right now."

    _whatsapp_contact_message_after_delay(contact_name, message_text, delay_seconds=8)
    return (
        f"Opening WhatsApp Web and I will search for {contact_name} and type your message."
    )
