import threading
import time
import urllib.parse
import webbrowser

import keyboard


def _clean_text(text):
    return " ".join(text.strip().split())


def _open_url(url):
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


def _type_after_delay(text, delay_seconds=8):
    def worker():
        time.sleep(delay_seconds)
        keyboard.write(text, delay=0.03)

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
