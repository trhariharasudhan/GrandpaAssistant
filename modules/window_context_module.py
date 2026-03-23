import pygetwindow as gw

from vision.screen_reader import read_screen_text


BROWSER_APPS = {"chrome", "msedge", "microsoft edge", "firefox", "brave", "opera"}
EDITOR_APPS = {"visual studio code", "vscode", "antigravity"}
EXPLORER_APPS = {"file explorer", "explorer"}


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
