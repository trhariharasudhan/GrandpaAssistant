import urllib.parse
import webbrowser
import time

import keyboard
import pyperclip

from brain.ai_engine import ask_ollama
from modules.notes_module import add_note
from modules.task_module import add_reminder
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


def _get_selected_browser_text():
    try:
        previous = pyperclip.paste()
    except Exception:
        previous = None

    try:
        keyboard.send("ctrl+c")
        time.sleep(0.25)
        selected = (pyperclip.paste() or "").strip()
    except Exception:
        selected = ""

    if previous is not None and selected == previous:
        selected = ""

    return selected


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


def _send_browser_shortcut(shortcut, success_message):
    try:
        keyboard.send(shortcut)
        return success_message
    except Exception:
        return "I could not control the current browser right now."


def browser_go_back():
    return _send_browser_shortcut("alt+left", "Going back in the current browser tab.")


def browser_go_forward():
    return _send_browser_shortcut("alt+right", "Going forward in the current browser tab.")


def browser_refresh():
    return _send_browser_shortcut("ctrl+r", "Refreshing the current browser page.")


def browser_scroll_down():
    try:
        keyboard.send("pagedown")
        return "Scrolling down the current browser page."
    except Exception:
        return "I could not scroll the current browser page."


def browser_scroll_up():
    try:
        keyboard.send("pageup")
        return "Scrolling up the current browser page."
    except Exception:
        return "I could not scroll the current browser page."


def copy_current_page_title(command=None):
    try:
        keyboard.send("alt+d")
        time.sleep(0.15)
        keyboard.send("ctrl+c")
        time.sleep(0.15)
        keyboard.send("esc")
        return "I copied the current page title or address focus text to the clipboard."
    except Exception:
        return "I could not copy the current page title right now."


def copy_selected_browser_text(command=None):
    selected = _get_selected_browser_text()

    if not selected:
        return "I could not copy selected browser text right now."

    return "Copied selected browser text to the clipboard."


def search_selected_text_on_google(command=None):
    selected = _get_selected_browser_text()

    if not selected:
        return "I could not read selected browser text right now."

    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(selected)
    if _open_url(url):
        return _with_feedback(f"Searching Google for selected text: {selected[:80]}.", None)
    return "I could not search the selected browser text right now."


def search_selected_text_on_youtube(command=None):
    selected = _get_selected_browser_text()

    if not selected:
        return "I could not read selected browser text right now."

    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(selected)
    if _open_url(url):
        return _with_feedback(f"Searching YouTube for selected text: {selected[:80]}.", None)
    return "I could not search the selected browser text on YouTube right now."


def summarize_selected_browser_text_ai(command=None):
    selected = _get_selected_browser_text()
    if not selected:
        return "I could not read selected browser text right now."

    prompt = (
        "Summarize this browser-selected text in a short practical way.\n\n"
        f"Selected text:\n{selected[:4000]}"
    )
    reply = ask_ollama(prompt, compact=True)
    return f"Selected text summary: {reply}"


def explain_selected_browser_text_ai(command=None):
    selected = _get_selected_browser_text()
    if not selected:
        return "I could not read selected browser text right now."

    prompt = (
        "Explain this browser-selected text in simple terms and mention the main point.\n\n"
        f"Selected text:\n{selected[:4000]}"
    )
    reply = ask_ollama(prompt, compact=True)
    return f"Selected text explanation: {reply}"


def ask_selected_browser_text_ai(command):
    selected = _get_selected_browser_text()
    if not selected:
        return "I could not read selected browser text right now."

    question = command
    prefixes = [
        "ask selected text",
        "ask browser selection",
        "question on selected text",
    ]
    for prefix in prefixes:
        if command.startswith(prefix):
            question = command.replace(prefix, "", 1).strip(" :,-")
            break

    if not question:
        return "Tell me what you want to know about the selected browser text."

    prompt = (
        "Answer the user's question using only this selected browser text. "
        "If the answer is not clear, say that briefly.\n\n"
        f"Question: {question}\n\n"
        f"Selected text:\n{selected[:4000]}"
    )
    reply = ask_ollama(prompt, compact=True)
    return f"From the selected text: {reply}"


def read_selected_browser_text_aloud(command=None):
    selected = _get_selected_browser_text()
    if not selected:
        return "I could not read selected browser text right now."

    cleaned = " ".join(selected.split())
    if len(cleaned) > 700:
        cleaned = cleaned[:700].rsplit(" ", 1)[0] + " ..."
    return f"Selected text says: {cleaned}"


def save_selected_browser_text_as_note(command=None):
    selected = _get_selected_browser_text()
    if not selected:
        return "I could not read selected browser text right now."

    cleaned = " ".join(selected.split())
    return add_note(f"add note {cleaned[:1200]}")


def create_reminder_from_selected_browser_text(command):
    selected = _get_selected_browser_text()
    if not selected:
        return "I could not read selected browser text right now."

    suffix = command
    prefixes = [
        "remind me about selected text",
        "create reminder from selected text",
        "remind me to review selected text",
    ]
    for prefix in prefixes:
        if command.startswith(prefix):
            suffix = command.replace(prefix, "", 1).strip()
            break

    selected_summary = " ".join(selected.split())
    if len(selected_summary) > 140:
        selected_summary = selected_summary[:140].rsplit(" ", 1)[0] + " ..."

    reminder_command = f"remind me to review {selected_summary}"
    if suffix:
        reminder_command = f"{reminder_command} {suffix}"

    return add_reminder(reminder_command)
