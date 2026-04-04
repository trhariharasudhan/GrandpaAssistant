import pyautogui
import pygetwindow as gw
import keyboard
import pyperclip
import re
import time

from vision.screen_reader import (
    click_on_text,
    find_text_details,
    get_screen_text_entries,
    read_named_screen_region,
    read_screen_text,
)


BROWSER_APPS = {"chrome", "msedge", "microsoft edge", "firefox", "brave", "opera"}
EDITOR_APPS = {"visual studio code", "vscode", "antigravity"}
EXPLORER_APPS = {"file explorer", "explorer"}
WHATSAPP_APPS = {"whatsapp"}


def get_active_window_info():
    try:
        window = gw.getActiveWindow()
    except Exception:
        return None

    if not window:
        return None

    title = (window.title or "").strip()
    app_name = _infer_app_name(title)
    app_key = app_name.lower()

    return {
        "title": title or "Unknown window",
        "app_name": app_name,
        "app_key": app_key,
    }


def _split_title_parts(title):
    parts = [title]
    for separator in [" - ", " | ", " • ", ": "]:
        next_parts = []
        for part in parts:
            split_parts = [item.strip() for item in part.split(separator) if item.strip()]
            next_parts.extend(split_parts or [part])
        parts = next_parts
    return [part for part in parts if part]


def _infer_app_name(title):
    if not title:
        return "Unknown application"

    parts = _split_title_parts(title)
    if not parts:
        return title

    # Usually the app name is the last segment in Windows titles.
    return parts[-1]


def _extract_browser_tab_title(title):
    parts = _split_title_parts(title)
    if len(parts) >= 2:
        return parts[0]
    return title


def _extract_editor_file_name(title):
    parts = _split_title_parts(title)
    if not parts:
        return None

    candidate = parts[0]
    return candidate if "." in candidate or "/" in candidate or "\\" in candidate else candidate


def _extract_explorer_location(title):
    parts = _split_title_parts(title)
    if not parts:
        return None

    if len(parts) >= 2:
        return parts[0]
    return title.replace("File Explorer", "").strip(" -")


def describe_active_window():
    info = get_active_window_info()
    if not info:
        return "I could not detect the active window right now."

    return (
        f"You are currently using {info['app_name']}. "
        f"The active window title is {info['title']}."
    )


def summarize_active_window():
    info = get_active_window_info()
    screen_text = read_screen_text()

    if not info and not screen_text:
        return "I could not understand the current screen."

    parts = []
    if info:
        parts.append(describe_active_window())

    if screen_text and "not installed" not in screen_text.lower():
        lines = [line.strip() for line in screen_text.splitlines() if line.strip()]
        preview = " | ".join(lines[:6])
        if preview:
            parts.append(f"I can see text like: {preview}.")

    if not parts:
        return "I could not summarize the active window clearly."

    return " ".join(parts)


def get_active_window_title():
    info = get_active_window_info()
    if not info:
        return "I could not detect the current window title."
    return f"The current window title is {info['title']}."


def get_active_app_name():
    info = get_active_window_info()
    if not info:
        return "I could not detect the active application."
    return f"You are currently using {info['app_name']}."


def summarize_if_code_editor():
    info = get_active_window_info()
    if not info:
        return "I could not detect the active window."

    if info["app_key"] in EDITOR_APPS:
        current_file = _extract_editor_file_name(info["title"])
        if current_file:
            return (
                f"You appear to be in a code editor. "
                f"The current file or tab looks like {current_file}."
            )
        return (
            f"You appear to be in a code editor. "
            f"The current window title is {info['title']}."
        )

    return "The active window does not look like a code editor right now."


def summarize_if_browser():
    info = get_active_window_info()
    if not info:
        return "I could not detect the active window."

    if info["app_key"] in BROWSER_APPS:
        tab_title = _extract_browser_tab_title(info["title"])
        screen_text = read_screen_text()
        parts = [
            f"You appear to be in a browser. The current tab title looks like {tab_title}."
        ]
        if screen_text and "not installed" not in screen_text.lower():
            lines = [line.strip() for line in screen_text.splitlines() if line.strip()]
            preview = " | ".join(lines[:4])
            if preview:
                parts.append(f"Visible page text includes: {preview}.")
        return " ".join(parts)

    return "The active window does not look like a browser right now."


def summarize_if_file_explorer():
    info = get_active_window_info()
    if not info:
        return "I could not detect the active window."

    if info["app_key"] in EXPLORER_APPS or "file explorer" in info["title"].lower():
        location = _extract_explorer_location(info["title"])
        if location:
            return f"You appear to be in File Explorer. The current folder looks like {location}."
        return "You appear to be in File Explorer."

    return "The active window does not look like File Explorer right now."


def summarize_browser_page():
    info = get_active_window_info()
    if not info or info["app_key"] not in BROWSER_APPS:
        return "The active window does not look like a browser right now."

    return summarize_if_browser()


def _browser_only_info():
    info = get_active_window_info()
    if not info or info["app_key"] not in BROWSER_APPS:
        return None
    return info


def _confirm_action(message, info):
    if not info:
        return message
    return f"{message} Active window: {info['title']}."


def _is_whatsapp_window(info):
    if not info:
        return False
    title = (info.get("title") or "").lower()
    app_key = (info.get("app_key") or "").lower()
    return "whatsapp" in title or app_key in WHATSAPP_APPS


def _visible_entries(limit=12):
    entries = get_screen_text_entries()
    if not entries:
        return []
    cleaned = []
    seen = set()
    for entry in entries:
        text = (entry.get("text") or "").strip()
        lowered = text.lower()
        if not text or lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(entry)
        if len(cleaned) >= limit:
            break
    return cleaned


def describe_visible_screen_targets(limit=10):
    entries = _visible_entries(limit=limit)
    if not entries:
        return "I could not clearly detect visible items on the current screen."
    names = [entry["text"] for entry in entries[:limit]]
    return "Visible items include: " + " | ".join(names)


def _click_visible_target(target, click_type="single"):
    details = find_text_details(target)
    if not details:
        return None

    x, y = details["center"]
    if click_type == "double":
        pyautogui.doubleClick(x, y)
    elif click_type == "right":
        pyautogui.rightClick(x, y)
    else:
        pyautogui.click(x, y)
    return details


def handle_visible_screen_action(command):
    normalized = " ".join((command or "").strip().split())
    lowered = normalized.lower()
    info = get_active_window_info()

    if lowered in [
        "what can you see here",
        "what is visible here",
        "what do you see on screen",
        "list visible items",
        "show visible items",
    ]:
        return describe_visible_screen_targets()

    pattern_map = [
        (r"^open (?:this )?(?:file|folder|item)\s+(.+)$", "double", "Opened"),
        (r"^double click (?:this )?(?:file|folder|item )?(.+)$", "double", "Double-clicked"),
        (r"^right click (?:this )?(?:file|folder|item )?(.+)$", "right", "Right-clicked"),
        (r"^select (?:this )?(?:file|folder|item )?(.+)$", "single", "Selected"),
        (r"^click (?:this )?(?:file|folder|item )?(.+)$", "single", "Clicked"),
    ]

    for pattern, click_type, verb in pattern_map:
        match = re.match(pattern, lowered)
        if not match:
            continue
        target = match.group(1).strip()
        if not target:
            return f"Tell me which visible item you want me to {verb.lower()}."
        details = _click_visible_target(target, click_type=click_type)
        if details:
            return _confirm_action(f"{verb} {details['text']}.", info)
        return f"I could not find {target} on the current screen."

    match = re.match(r"^copy (?:this )?(?:file|folder|item )?(.+)$", lowered)
    if match:
        target = match.group(1).strip()
        if not target:
            return "Tell me which visible item you want me to copy."
        details = _click_visible_target(target, click_type="single")
        if not details:
            return f"I could not find {target} on the current screen."
        time.sleep(0.1)
        keyboard.send("ctrl+c")
        return _confirm_action(f"Selected and copied {details['text']}.", info)

    if lowered in ["copy this", "copy selected item", "copy selected file", "copy selected folder"]:
        keyboard.send("ctrl+c")
        return _confirm_action("Copied the currently selected item.", info)

    if lowered in ["paste here", "paste this here", "paste now"]:
        keyboard.send("ctrl+v")
        return _confirm_action("Pasted here.", info)

    if lowered in ["open selected item", "open selected file", "open selected folder"]:
        return explorer_open_selected_item()

    return None


def handle_whatsapp_screen_action(command):
    normalized = " ".join((command or "").strip().split())
    lowered = normalized.lower()
    info = get_active_window_info()
    if not _is_whatsapp_window(info):
        return None

    if lowered in ["whatsapp status", "what is on whatsapp", "summarize whatsapp"]:
        return summarize_whatsapp_context()

    tab_map = {
        "go to status": "Status",
        "go to updates": "Updates",
        "go to calls": "Calls",
        "go to chats": "Chats",
        "go to communities": "Communities",
    }
    if lowered in tab_map:
        target = tab_map[lowered]
        details = _click_visible_target(target, click_type="single")
        if details:
            return f"Opened WhatsApp {target.lower()}."
        return f"I could not find WhatsApp {target.lower()} right now."

    open_chat_match = re.match(r"^(?:open chat|open whatsapp chat|go to chat)\s+(.+)$", lowered)
    if open_chat_match:
        target = open_chat_match.group(1).strip()
        details = _click_visible_target(target, click_type="single")
        if details:
            return f"Opened WhatsApp chat {details['text']}."
        return f"I could not find WhatsApp chat {target} right now."

    call_match = re.match(r"^(?:call on whatsapp|whatsapp call|open whatsapp call for)\s+(.+)$", lowered)
    if call_match:
        target = call_match.group(1).strip()
        details = _click_visible_target(target, click_type="single")
        if not details:
            return f"I could not find WhatsApp chat {target} right now."
        time.sleep(0.8)
        for button_text in ["Voice call", "Call", "voice call"]:
            call_details = _click_visible_target(button_text, click_type="single")
            if call_details:
                return f"Opened WhatsApp chat {details['text']} and started the call flow."
        return f"Opened WhatsApp chat {details['text']}, but I could not find the call button."

    return None


def get_current_browser_page_title():
    info = _browser_only_info()
    if not info:
        return "The active window does not look like a browser right now."

    tab_title = _extract_browser_tab_title(info["title"])
    return f"The current browser page title looks like {tab_title}."


def summarize_visible_browser_section():
    info = _browser_only_info()
    if not info:
        return "The active window does not look like a browser right now."

    region_text = read_named_screen_region("center")
    if not region_text or "not installed" in region_text.lower():
        return "I could not read the visible browser section clearly."

    lines = [line.strip() for line in region_text.splitlines() if line.strip()]
    if not lines:
        return "I could not read the visible browser section clearly."

    preview = " | ".join(lines[:6])
    return f"The visible browser section includes: {preview}."


def find_on_current_browser_page(command):
    info = _browser_only_info()
    if not info:
        return "The active window does not look like a browser right now."

    target = command
    prefixes = [
        "search this page for",
        "find on this page",
        "find this page",
        "search page for",
    ]
    for prefix in prefixes:
        if command.startswith(prefix):
            target = command.replace(prefix, "", 1).strip()
            break

    if not target:
        return "Tell me what you want me to find on this page."

    details = find_text_details(target)
    if not details:
        return f"I could not find {target} on the current browser page."

    x, y = details["center"]
    return f"I found {details['text']} on the current browser page near position {x}, {y}."


def click_on_current_browser_page(command):
    info = _browser_only_info()
    if not info:
        return "The active window does not look like a browser right now."

    target = command
    prefixes = [
        "click on this page",
        "click this page",
        "click first matching result for",
        "click first result for",
    ]
    for prefix in prefixes:
        if command.startswith(prefix):
            target = command.replace(prefix, "", 1).strip()
            break

    if not target:
        return "Tell me what you want me to click on this page."

    found = click_on_text(target)
    if found:
        return f"I clicked {target} on the current browser page."

    return f"I could not find {target} on the current browser page to click."


def search_page_and_click_first_match(command):
    info = _browser_only_info()
    if not info:
        return "The active window does not look like a browser right now."

    target = command
    prefixes = [
        "search page and click first match for",
        "find on this page and click",
        "search this page and click",
    ]
    for prefix in prefixes:
        if command.startswith(prefix):
            target = command.replace(prefix, "", 1).strip()
            break

    if not target:
        return "Tell me what you want me to search and click on this page."

    details = click_on_text(target)
    if details:
        return f"I found and clicked {target} on the current browser page."

    return f"I could not find {target} on the current browser page to click."


def _candidate_browser_results():
    entries = get_screen_text_entries()
    if not entries:
        return []

    screen_width, screen_height = pyautogui.size()
    min_top = int(screen_height * 0.16)
    max_top = int(screen_height * 0.92)
    min_width = int(screen_width * 0.12)
    candidates = []

    for entry in entries:
        left, top, width, height = entry["bounds"]
        text = entry["text"].strip()
        if top < min_top or top > max_top:
            continue
        if width < min_width:
            continue
        if len(text) < 8:
            continue
        if text.lower() in {"google", "youtube", "images", "videos", "all"}:
            continue

        alpha_chars = sum(char.isalpha() for char in text)
        if alpha_chars < 4:
            continue

        candidates.append(entry)

    candidates.sort(key=lambda item: (item["bounds"][1], item["bounds"][0]))
    return candidates


def open_browser_result(command):
    info = _browser_only_info()
    if not info:
        return "The active window does not look like a browser right now."

    order_map = {
        "open first search result": 1,
        "open first result": 1,
        "click top result": 1,
        "open top result": 1,
        "open second search result": 2,
        "open second result": 2,
        "open third search result": 3,
        "open third result": 3,
    }

    normalized_command = command.strip()
    ordinal = order_map.get(normalized_command)
    if ordinal is None:
        match = None
        if normalized_command.endswith(" and summarize"):
            match = re.match(r"^open result (\d+)\s+and summarize$", normalized_command)
        else:
            match = re.match(r"^open result (\d+)$", normalized_command)
        if match:
            ordinal = max(1, int(match.group(1)))
    if ordinal is None:
        return "Tell me which visible result you want to open."

    candidates = _candidate_browser_results()
    if len(candidates) < ordinal:
        return f"I could not find a visible result number {ordinal} on this browser page."

    chosen = candidates[ordinal - 1]
    pyautogui.click(chosen["center"])
    return f"I opened result {ordinal}: {chosen['text']}."


def open_first_result_and_summarize(_command):
    info = _browser_only_info()
    if not info:
        return "The active window does not look like a browser right now."

    open_message = open_browser_result("open first result")
    if not open_message.lower().startswith("i opened result 1"):
        return open_message

    time.sleep(1.2)
    page_title = get_current_browser_page_title()
    section_summary = summarize_visible_browser_section()
    return f"{open_message} {page_title} {section_summary}"


def open_numbered_result_and_summarize(command):
    info = _browser_only_info()
    if not info:
        return "The active window does not look like a browser right now."

    normalized_command = command.strip()
    if normalized_command.endswith("in new tab"):
        return open_result_in_new_tab(normalized_command)
    if normalized_command.endswith("and copy title"):
        return open_result_and_copy_title(normalized_command)
    if not normalized_command.endswith("and summarize"):
        return open_browser_result(normalized_command)

    open_message = open_browser_result(command.replace(" and summarize", ""))
    if not open_message.lower().startswith("i opened result"):
        return open_message

    time.sleep(1.2)
    return f"{open_message} {get_current_browser_page_title()} {summarize_visible_browser_section()}"


def open_result_in_new_tab(command):
    info = _browser_only_info()
    if not info:
        return "The active window does not look like a browser right now."

    match = re.match(r"^open result (\d+) in new tab$", command.strip())
    if not match:
        return "Tell me which visible result you want to open in a new tab."

    ordinal = max(1, int(match.group(1)))
    candidates = _candidate_browser_results()
    if len(candidates) < ordinal:
        return f"I could not find a visible result number {ordinal} on this browser page."

    chosen = candidates[ordinal - 1]
    try:
        pyautogui.keyDown("ctrl")
        pyautogui.click(chosen["center"])
    finally:
        pyautogui.keyUp("ctrl")

    return f"I opened result {ordinal} in a new tab: {chosen['text']}."


def open_result_and_copy_title(command):
    info = _browser_only_info()
    if not info:
        return "The active window does not look like a browser right now."

    match = re.match(r"^open result (\d+) and copy title$", command.strip())
    if not match:
        return "Tell me which visible result you want me to open and copy the title for."

    ordinal = max(1, int(match.group(1)))
    open_message = open_browser_result(f"open result {ordinal}")
    if not open_message.lower().startswith("i opened result"):
        return open_message

    time.sleep(1.0)
    keyboard.send("alt+d")
    time.sleep(0.15)
    keyboard.send("ctrl+c")
    time.sleep(0.15)
    keyboard.send("esc")
    return f"{open_message} I copied the page title or address focus text to the clipboard."


def open_selected_link_in_new_tab():
    info = _browser_only_info()
    if not info:
        return "The active window does not look like a browser right now."

    try:
        pyautogui.keyDown("ctrl")
        pyautogui.click()
    finally:
        pyautogui.keyUp("ctrl")
    return "I tried opening the selected link in a new tab."


def summarize_browser_selection():
    info = _browser_only_info()
    if not info:
        return "The active window does not look like a browser right now."

    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        old_clipboard = None

    try:
        keyboard.send("ctrl+c")
        time.sleep(0.25)
        selected_text = (pyperclip.paste() or "").strip()
    except Exception:
        selected_text = ""

    if old_clipboard and selected_text == old_clipboard:
        selected_text = ""

    if not selected_text:
        return "I could not read any selected browser text right now."

    lines = [line.strip() for line in selected_text.splitlines() if line.strip()]
    preview = " | ".join(lines[:5]) if lines else selected_text[:300]
    return f"The current browser selection says: {preview}."


def summarize_code_editor():
    info = get_active_window_info()
    if not info or info["app_key"] not in EDITOR_APPS:
        return "The active window does not look like a code editor right now."

    file_name = _extract_editor_file_name(info["title"])
    screen_text = read_screen_text()
    parts = []

    if file_name:
        parts.append(f"You are editing {file_name}.")
    else:
        parts.append(f"You are in a code editor. The window title is {info['title']}.")

    if screen_text and "not installed" not in screen_text.lower():
        lines = [line.strip() for line in screen_text.splitlines() if line.strip()]
        preview = " | ".join(lines[:5])
        if preview:
            parts.append(f"Visible editor text includes: {preview}.")

    return " ".join(parts)


def summarize_current_folder():
    info = get_active_window_info()
    if not info:
        return "I could not detect the active window."

    if info["app_key"] in EXPLORER_APPS or "file explorer" in info["title"].lower():
        location = _extract_explorer_location(info["title"])
        if location:
            return f"The current File Explorer folder looks like {location}."
        return "You are in File Explorer, but I could not read the current folder clearly."

    return "The active window does not look like File Explorer right now."


def summarize_whatsapp_context():
    info = get_active_window_info()
    if not info:
        return "I could not detect the active window."

    title = info["title"].lower()
    if "whatsapp" not in title:
        return "The active window does not look like WhatsApp right now."

    screen_text = read_screen_text()
    if screen_text and "not installed" not in screen_text.lower():
        lines = [line.strip() for line in screen_text.splitlines() if line.strip()]
        preview = " | ".join(lines[:5])
        return f"You appear to be in WhatsApp. Visible text includes: {preview}."

    return f"You appear to be in WhatsApp. The current window title is {info['title']}."


def browser_new_tab():
    info = get_active_window_info()
    if not info or info["app_key"] not in BROWSER_APPS:
        return "The active window does not look like a browser right now."
    try:
        keyboard.send("ctrl+t")
        return _confirm_action("Opened a new browser tab", info)
    except Exception:
        return "I could not open a new browser tab right now."


def browser_close_tab():
    info = get_active_window_info()
    if not info or info["app_key"] not in BROWSER_APPS:
        return "The active window does not look like a browser right now."
    try:
        keyboard.send("ctrl+w")
        return _confirm_action("Closed the current browser tab", info)
    except Exception:
        return "I could not close the current browser tab right now."


def editor_save_current_file():
    info = get_active_window_info()
    if not info or info["app_key"] not in EDITOR_APPS:
        return "The active window does not look like a code editor right now."
    try:
        keyboard.send("ctrl+s")
        return _confirm_action("Saved the current file", info)
    except Exception:
        return "I could not save the current file right now."


def editor_run_current_file():
    info = get_active_window_info()
    if not info or info["app_key"] not in EDITOR_APPS:
        return "The active window does not look like a code editor right now."
    try:
        keyboard.send("ctrl+f5")
        return _confirm_action("Triggered run for the current file", info)
    except Exception:
        return "I could not run the current file right now."


def explorer_open_selected_item():
    info = get_active_window_info()
    if not info:
        return "I could not detect the active window."

    if not (info["app_key"] in EXPLORER_APPS or "file explorer" in info["title"].lower()):
        return "The active window does not look like File Explorer right now."
    try:
        keyboard.send("enter")
        return _confirm_action("Opened the selected item in File Explorer", info)
    except Exception:
        return "I could not open the selected item right now."
