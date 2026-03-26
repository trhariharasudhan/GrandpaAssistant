import urllib.parse
import webbrowser
import time

from utils.config import get_setting


def _clean_query(text):
    return " ".join(text.strip().split())


def _open_url(url, retries=2, delay_seconds=None):
    delay_seconds = delay_seconds or get_setting("browser.page_load_delay_seconds", 3)

    for attempt in range(max(1, retries)):
        try:
            if webbrowser.open(url, new=2):
                return True
        except Exception:
            pass
        if attempt < retries - 1:
            time.sleep(delay_seconds)
    return False


def _with_feedback(success_message, failure_message, delay_seconds=None):
    delay_seconds = delay_seconds or get_setting("browser.page_load_delay_seconds", 3)
    return (
        f"{success_message} Give it about {delay_seconds} seconds to load."
        if success_message
        else failure_message
    )


def open_whatsapp_web():
    delay_seconds = get_setting("browser.whatsapp_load_delay_seconds", 8)
    if _open_url("https://web.whatsapp.com/", delay_seconds=delay_seconds):
        return f"Opening WhatsApp Web. Give it about {delay_seconds} seconds to load."
    return "I could not open WhatsApp Web right now."


def open_youtube():
    if _open_url("https://www.youtube.com/"):
        return _with_feedback("Opening YouTube.", None)
    return "I could not open YouTube right now."


def open_gmail():
    delay_seconds = get_setting("browser.gmail_load_delay_seconds", 8)
    if _open_url("https://mail.google.com/", delay_seconds=delay_seconds):
        return f"Opening Gmail. Give it about {delay_seconds} seconds to load."
    return "I could not open Gmail right now."


def search_google(command):
    query = command
    prefixes = [
        "search google for",
        "google",
        "search for",
        "search",
    ]

    for prefix in prefixes:
        if command.startswith(prefix):
            query = command.replace(prefix, "", 1)
            break

    query = _clean_query(query)
    if not query:
        return "Tell me what you want to search on Google."

    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
    if _open_url(url):
        return _with_feedback(f"Searching Google for {query}.", None)
    return "I could not open Google search right now."


def search_youtube(command):
    query = command
    prefixes = [
        "search youtube for",
        "open youtube and search",
        "youtube search",
        "youtube",
    ]

    for prefix in prefixes:
        if command.startswith(prefix):
            query = command.replace(prefix, "", 1)
            break

    query = _clean_query(query)
    if not query:
        return "Tell me what you want to search on YouTube."

    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    if _open_url(url):
        return _with_feedback(f"Searching YouTube for {query}.", None)
    return "I could not open YouTube search right now."


def open_maps_search(command):
    query = command
    prefixes = [
        "open maps for",
        "find place",
        "search maps for",
    ]

    for prefix in prefixes:
        if command.startswith(prefix):
            query = command.replace(prefix, "", 1)
            break

    query = _clean_query(query)
    if not query:
        return "Tell me which place you want to find."

    url = "https://www.google.com/maps/search/" + urllib.parse.quote_plus(query)
    if _open_url(url):
        return _with_feedback(f"Opening maps for {query}.", None)
    return "I could not open maps right now."
