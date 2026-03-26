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


def open_whatsapp_web():
    if _open_url("https://web.whatsapp.com/"):
        return "Opening WhatsApp Web."
    return "I could not open WhatsApp Web right now."


def open_youtube():
    if _open_url("https://www.youtube.com/"):
        return "Opening YouTube."
    return "I could not open YouTube right now."


def open_gmail():
    if _open_url("https://mail.google.com/"):
        return "Opening Gmail."
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
        return f"Searching Google for {query}."
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
        return f"Searching YouTube for {query}."
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
        return f"Opening maps for {query}."
    return "I could not open maps right now."
