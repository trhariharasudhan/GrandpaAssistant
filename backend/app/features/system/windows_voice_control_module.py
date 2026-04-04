import os
import re
import subprocess
import time

import psutil
import pyautogui
import pygetwindow as gw


SETTINGS_PAGE_MAP = {
    "settings": ("ms-settings:", "Settings Home"),
    "settings home": ("ms-settings:", "Settings Home"),
    "home": ("ms-settings:", "Settings Home"),
    "system": ("ms-settings:system", "System settings"),
    "system settings": ("ms-settings:system", "System settings"),
    "display": ("ms-settings:display", "Display settings"),
    "display settings": ("ms-settings:display", "Display settings"),
    "sound": ("ms-settings:sound", "Sound settings"),
    "sound settings": ("ms-settings:sound", "Sound settings"),
    "volume settings": ("ms-settings:sound", "Sound settings"),
    "bluetooth": ("ms-settings:bluetooth", "Bluetooth settings"),
    "bluetooth settings": ("ms-settings:bluetooth", "Bluetooth settings"),
    "bluetooth and devices": ("ms-settings:bluetooth", "Bluetooth and devices"),
    "bluetooth & devices": ("ms-settings:bluetooth", "Bluetooth and devices"),
    "network settings": ("ms-settings:network", "Network and internet"),
    "network and internet": ("ms-settings:network", "Network and internet"),
    "network & internet": ("ms-settings:network", "Network and internet"),
    "wifi": ("ms-settings:network-wifi", "Wi-Fi settings"),
    "wifi settings": ("ms-settings:network-wifi", "Wi-Fi settings"),
    "battery": ("ms-settings:batterysaver", "Battery settings"),
    "battery settings": ("ms-settings:batterysaver", "Battery settings"),
    "storage": ("ms-settings:storagesense", "Storage settings"),
    "storage settings": ("ms-settings:storagesense", "Storage settings"),
    "windows update": ("ms-settings:windowsupdate", "Windows Update"),
    "update settings": ("ms-settings:windowsupdate", "Windows Update"),
    "apps": ("ms-settings:appsfeatures", "Apps settings"),
    "apps settings": ("ms-settings:appsfeatures", "Apps settings"),
    "installed apps": ("ms-settings:appsfeatures", "Installed apps"),
    "startup apps settings": ("ms-settings:startupapps", "Startup apps settings"),
    "default apps settings": ("ms-settings:defaultapps", "Default apps settings"),
    "personalization": ("ms-settings:personalization", "Personalization settings"),
    "personalization settings": ("ms-settings:personalization", "Personalization settings"),
    "theme settings": ("ms-settings:themes", "Theme settings"),
    "taskbar settings": ("ms-settings:taskbar", "Taskbar settings"),
    "accounts": ("ms-settings:yourinfo", "Accounts settings"),
    "accounts settings": ("ms-settings:yourinfo", "Accounts settings"),
    "time and language": ("ms-settings:timeandlanguage", "Time and language"),
    "time & language": ("ms-settings:timeandlanguage", "Time and language"),
    "time settings": ("ms-settings:dateandtime", "Date and time settings"),
    "keyboard settings": ("ms-settings:keyboard", "Keyboard settings"),
    "mouse settings": ("ms-settings:mousetouchpad", "Mouse settings"),
    "mouse pointer and touch": ("ms-settings:mousetouchpad", "Mouse pointer and touch"),
    "touchpad settings": ("ms-settings:devices-touchpad", "Touchpad settings"),
    "gaming": ("ms-settings:gaming", "Gaming settings"),
    "gaming settings": ("ms-settings:gaming", "Gaming settings"),
    "accessibility": ("ms-settings:easeofaccess", "Accessibility settings"),
    "accessibility settings": ("ms-settings:easeofaccess", "Accessibility settings"),
    "voice access settings": ("ms-settings:easeofaccess-speechrecognition", "Voice access settings"),
    "speech settings": ("ms-settings:speech", "Speech settings"),
    "notifications": ("ms-settings:notifications", "Notifications settings"),
    "notifications settings": ("ms-settings:notifications", "Notifications settings"),
    "focus assist settings": ("ms-settings:quiethours", "Focus assist settings"),
    "privacy and security": ("ms-settings:privacy", "Privacy and security"),
    "privacy & security": ("ms-settings:privacy", "Privacy and security"),
    "privacy settings": ("ms-settings:privacy", "Privacy and security"),
    "camera privacy settings": ("ms-settings:privacy-webcam", "Camera privacy settings"),
    "microphone privacy settings": ("ms-settings:privacy-microphone", "Microphone privacy settings"),
    "cloud storage": ("ms-settings:storage", "Storage settings"),
}

DEFAULT_APP_COMMANDS = {
    "settings": ["cmd.exe", "/c", "start", "ms-settings:"],
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "chrome": ["cmd.exe", "/c", "start", "chrome"],
    "microsoft edge": ["cmd.exe", "/c", "start", "msedge"],
    "paint": ["mspaint.exe"],
    "task manager": ["taskmgr.exe"],
    "control panel": ["control.exe"],
    "command prompt": ["cmd.exe"],
    "terminal": ["cmd.exe", "/c", "start", "wt"],
    "windows terminal": ["cmd.exe", "/c", "start", "wt"],
    "file explorer": ["explorer.exe"],
    "explorer": ["explorer.exe"],
    "snipping tool": ["cmd.exe", "/c", "start", "ms-screenclip:"],
    "camera": ["cmd.exe", "/c", "start", "microsoft.windows.camera:"],
    "photos": ["cmd.exe", "/c", "start", "ms-photos:"],
    "media player": ["cmd.exe", "/c", "start", "mswindowsmusic:"],
    "clock": ["cmd.exe", "/c", "start", "ms-clock:"],
    "sticky notes": ["cmd.exe", "/c", "start", "ms-sticky-notes:"],
    "microsoft store": ["cmd.exe", "/c", "start", "ms-windows-store:"],
    "store": ["cmd.exe", "/c", "start", "ms-windows-store:"],
    "maps": ["cmd.exe", "/c", "start", "bingmaps:"],
    "sound recorder": ["cmd.exe", "/c", "start", "ms-callrecording:"],
    "phone link": ["cmd.exe", "/c", "start", "ms-phone:"],
    "voice recorder": ["cmd.exe", "/c", "start", "ms-callrecording:"],
}

DESKTOP_KEY_ACTIONS = {
    "press enter": ("enter", "Pressed Enter."),
    "press tab": ("tab", "Pressed Tab."),
    "press escape": ("esc", "Pressed Escape."),
    "press backspace": ("backspace", "Pressed Backspace."),
    "press delete": ("delete", "Pressed Delete."),
    "press up": ("up", "Pressed Up."),
    "press down": ("down", "Pressed Down."),
    "press left": ("left", "Pressed Left."),
    "press right": ("right", "Pressed Right."),
    "page down": ("pagedown", "Pressed Page Down."),
    "page up": ("pageup", "Pressed Page Up."),
}

HOTKEY_ACTIONS = {
    "open quick settings": (("win", "a"), "Opened Quick Settings."),
    "open action center": (("win", "a"), "Opened Quick Settings."),
    "open notification center": (("win", "n"), "Opened Notification Center."),
    "open search": (("win", "s"), "Opened Windows Search."),
    "open run box": (("win", "r"), "Opened the Run dialog."),
    "open file search": (("ctrl", "l"), "Focused the current location/search bar."),
    "new browser tab": (("ctrl", "t"), "Opened a new tab."),
    "close current tab": (("ctrl", "w"), "Closed the current tab."),
    "switch window": (("alt", "tab"), "Switched the active window."),
    "show desktop": (("win", "d"), "Toggled desktop view."),
    "open start menu": (("win",), "Opened the Start menu."),
    "click start button": (("win",), "Opened the Start menu."),
    "press start button": (("win",), "Opened the Start menu."),
    "open start button": (("win",), "Opened the Start menu."),
    "close start menu": (("esc",), "Closed the Start menu."),
    "focus taskbar": (("win", "t"), "Focused the taskbar."),
    "show taskbar": (("win", "t"), "Focused the taskbar."),
    "open task view": (("win", "tab"), "Opened Task View."),
    "open widgets": (("win", "w"), "Opened Widgets."),
    "open system tray": (("win", "b"), "Focused the system tray."),
    "copy that": (("ctrl", "c"), "Copied the current selection."),
    "paste that": (("ctrl", "v"), "Pasted from the clipboard."),
    "select all": (("ctrl", "a"), "Selected everything in the current area."),
    "undo that": (("ctrl", "z"), "Undid the last action."),
    "redo that": (("ctrl", "y"), "Redid the last action."),
    "save this": (("ctrl", "s"), "Tried to save the current item."),
    "close this window": (("alt", "f4"), "Tried to close the current window."),
    "next field": (("tab",), "Moved to the next field."),
    "previous field": (("shift", "tab"), "Moved to the previous field."),
}


def _run_start_command(command_parts):
    try:
        subprocess.Popen(command_parts, shell=False)
        return True
    except Exception:
        return False


def _open_ms_settings(uri):
    try:
        os.system(f'start "" "{uri}"')
        return True
    except Exception:
        return False


def open_windows_settings_page(command):
    normalized = " ".join((command or "").lower().strip().split())
    prefixes = ["open ", "show ", "go to "]
    target = None
    for prefix in prefixes:
        if normalized.startswith(prefix):
            target = normalized.replace(prefix, "", 1).strip()
            break

    if not target:
        return None

    cleaned_target = (
        target.replace("&", "and")
        .replace(" page", "")
        .replace(" tab", "")
        .replace(" section", "")
        .strip()
    )
    cleaned_target = " ".join(cleaned_target.split())

    candidate_targets = [cleaned_target]
    if cleaned_target.startswith("settings "):
        candidate_targets.append(cleaned_target.replace("settings ", "", 1).strip())
    if not cleaned_target.endswith("settings"):
        candidate_targets.append(f"{cleaned_target} settings")

    resolved = None
    for candidate in candidate_targets:
        if candidate in SETTINGS_PAGE_MAP:
            resolved = SETTINGS_PAGE_MAP[candidate]
            break

    if resolved:
        uri, label = resolved
        if _open_ms_settings(uri):
            return f"Opening {label}."
        return f"I could not open {label} right now."

    return None


def open_default_windows_app(command):
    normalized = " ".join((command or "").lower().strip().split())
    target = None
    for prefix in ["open ", "start ", "launch "]:
        if normalized.startswith(prefix):
            target = normalized.replace(prefix, "", 1).strip()
            break
    if target in DEFAULT_APP_COMMANDS:
        if _run_start_command(DEFAULT_APP_COMMANDS[target]):
            return f"Opening {target}."
        return f"I could not open {target} right now."

    return None


def _voice_access_processes():
    names = []
    for process in psutil.process_iter(["name"]):
        try:
            name = (process.info.get("name") or "").lower()
        except Exception:
            continue
        if "voiceaccess" in name or "voice access" in name:
            names.append(process)
    return names


def handle_voice_access_control(command):
    normalized = " ".join((command or "").lower().strip().split())

    if normalized in ["voice access status", "what is voice access status"]:
        return (
            "Voice Access is running."
            if _voice_access_processes()
            else "Voice Access is not running right now."
        )

    if normalized in ["start voice access", "open voice access", "enable voice access"]:
        if _voice_access_processes():
            return "Voice Access is already running."
        if _run_start_command(["cmd.exe", "/c", "start", "ms-settings:easeofaccess-speechrecognition"]):
            return "Opening Voice Access settings."
        return "I could not start Voice Access right now."

    if normalized in ["stop voice access", "disable voice access"]:
        stopped = False
        for process in _voice_access_processes():
            try:
                process.kill()
                stopped = True
            except Exception:
                continue
        if stopped:
            return "Stopped Voice Access."
        return "Voice Access is not running right now."

    return None


def _apply_projection_mode(mode):
    mode_positions = {
        "pc_screen_only": 0,
        "duplicate": 1,
        "extend": 2,
        "second_screen_only": 3,
    }
    index = mode_positions.get(mode)
    if index is None:
        return False

    try:
        pyautogui.hotkey("win", "p")
        time.sleep(0.45)
        for _ in range(4):
            pyautogui.press("up")
            time.sleep(0.04)
        for _ in range(index):
            pyautogui.press("down")
            time.sleep(0.04)
        pyautogui.press("enter")
        return True
    except Exception:
        return False


def handle_desktop_action(command):
    normalized = " ".join((command or "").lower().strip().split())

    projection_intents = {
        "duplicate": [
            "duplicate screen",
            "duplicate display",
            "duplicate mode",
            "set display duplicate",
            "display mode duplicate",
            "project duplicate",
            "switch to duplicate",
        ],
        "extend": [
            "extend screen",
            "extend display",
            "extend mode",
            "set display extend",
            "display mode extend",
            "project extend",
            "switch to extend",
        ],
        "second_screen_only": [
            "second screen only",
            "projector only",
            "external display only",
            "switch to second screen only",
            "display mode second screen",
        ],
        "pc_screen_only": [
            "pc screen only",
            "laptop screen only",
            "main screen only",
            "switch to pc screen only",
            "display mode pc screen",
        ],
    }
    for mode, phrases in projection_intents.items():
        if any(phrase in normalized for phrase in phrases):
            if _apply_projection_mode(mode):
                pretty = {
                    "duplicate": "duplicate",
                    "extend": "extend",
                    "second_screen_only": "second screen only",
                    "pc_screen_only": "PC screen only",
                }.get(mode, mode)
                return f"Switched display mode to {pretty}."
            return "I could not change display mode right now."

    taskbar_slot_match = re.match(r"^(?:open|launch|start)\s+(?:taskbar\s+)?app\s+([1-9])$", normalized)
    if taskbar_slot_match:
        slot = taskbar_slot_match.group(1)
        try:
            pyautogui.hotkey("win", slot)
            return f"Opened taskbar app slot {slot}."
        except Exception:
            return f"I could not open taskbar app slot {slot} right now."

    if normalized in ["open hidden icons", "show hidden icons", "open tray overflow"]:
        try:
            pyautogui.hotkey("win", "b")
            time.sleep(0.2)
            pyautogui.press("enter")
            return "Opened hidden icons from the taskbar."
        except Exception:
            return "I could not open hidden icons right now."

    if normalized in ["next taskbar app", "taskbar next app"]:
        try:
            pyautogui.hotkey("win", "t")
            time.sleep(0.15)
            pyautogui.press("right")
            pyautogui.press("enter")
            return "Switched to the next taskbar app."
        except Exception:
            return "I could not switch to the next taskbar app right now."

    if normalized in ["previous taskbar app", "taskbar previous app"]:
        try:
            pyautogui.hotkey("win", "t")
            time.sleep(0.15)
            pyautogui.press("left")
            pyautogui.press("enter")
            return "Switched to the previous taskbar app."
        except Exception:
            return "I could not switch to the previous taskbar app right now."

    combo_match = re.match(r"^press ((?:ctrl|control|alt|shift|win|windows)(?: [a-z0-9]+)+)$", normalized)
    if combo_match:
        raw_combo = combo_match.group(1)
        key_tokens = raw_combo.split()
        normalized_keys = []
        for token in key_tokens:
            normalized_keys.append(
                {
                    "control": "ctrl",
                    "windows": "win",
                }.get(token, token)
            )
        try:
            pyautogui.hotkey(*normalized_keys)
            return f"Pressed {' + '.join(normalized_keys)}."
        except Exception:
            return f"I could not press {' + '.join(normalized_keys)} right now."

    if normalized in DESKTOP_KEY_ACTIONS:
        key, reply = DESKTOP_KEY_ACTIONS[normalized]
        pyautogui.press(key)
        return reply

    if normalized in HOTKEY_ACTIONS:
        keys, reply = HOTKEY_ACTIONS[normalized]
        pyautogui.hotkey(*keys)
        return reply

    if normalized in ["scroll down", "scroll lower"]:
        pyautogui.scroll(-700)
        return "Scrolled down."

    if normalized in ["scroll up", "scroll higher"]:
        pyautogui.scroll(700)
        return "Scrolled up."

    if normalized in ["scroll left"]:
        pyautogui.hscroll(-500)
        return "Scrolled left."

    if normalized in ["scroll right"]:
        pyautogui.hscroll(500)
        return "Scrolled right."

    if normalized.startswith("press "):
        key_name = normalized.replace("press ", "", 1).strip()
        key_name = {
            "space": "space",
            "spacebar": "space",
            "escape": "esc",
        }.get(key_name, key_name)
        try:
            pyautogui.press(key_name)
            return f"Pressed {key_name}."
        except Exception:
            return f"I could not press {key_name} right now."

    if normalized.startswith("type "):
        text = command[5:].strip()
        if not text:
            return "Tell me what you want me to type."
        pyautogui.write(text, interval=0.02)
        return f"Typed {text}."

    if normalized.startswith("search in start for "):
        text = command.lower().split("search in start for ", 1)[1].strip()
        if not text:
            return "Tell me what you want me to search in Start."
        pyautogui.press("win")
        time.sleep(0.6)
        pyautogui.write(text, interval=0.03)
        time.sleep(0.2)
        pyautogui.press("enter")
        return f"Searched Start for {text}."

    if normalized.startswith("search for "):
        text = command.lower().split("search for ", 1)[1].strip()
        if not text:
            return "Tell me what you want me to search."
        pyautogui.hotkey("win", "s")
        time.sleep(0.6)
        pyautogui.write(text, interval=0.03)
        return f"Opened Windows Search for {text}."

    return None


def handle_settings_page_action(command):
    normalized = " ".join((command or "").lower().strip().split())

    go_match = re.match(
        r"^(?:open|show)\s+settings(?:\s+home)?\s+(?:and\s+)?(?:go to|open)\s+(.+)$",
        normalized,
    )
    if go_match:
        target = go_match.group(1).strip()
        if not target:
            return "Tell me which Settings section you want."
        open_reply = open_windows_settings_page(f"open {target}")
        return open_reply or "I could not open that Settings section right now."

    search_match = re.match(r"^(?:open|show|go to) (.+?) and search (?:for )?(.+)$", normalized)
    if search_match:
        target = search_match.group(1).strip()
        search_text = search_match.group(2).strip()
        open_reply = open_windows_settings_page(f"open {target}")
        if not open_reply:
            return None
        if not search_text:
            return f"{open_reply} Tell me what to search."
        time.sleep(1.6)
        try:
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.25)
            pyautogui.write(search_text, interval=0.03)
            time.sleep(0.2)
            pyautogui.press("enter")
            return f"{open_reply} Then I searched for {search_text}."
        except Exception:
            return f"{open_reply} I could not type the search text right now."

    scroll_match = re.match(r"^(?:open|show|go to) (.+?) and scroll (down|up)$", normalized)
    if scroll_match:
        target = scroll_match.group(1)
        direction = scroll_match.group(2)
        open_reply = open_windows_settings_page(f"open {target}")
        if not open_reply:
            return None
        time.sleep(1.8)
        pyautogui.scroll(-700 if direction == "down" else 700)
        return f"{open_reply} Then I scrolled {direction}."

    click_match = re.match(r"^(?:open|show|go to) (.+?) and click (.+)$", normalized)
    if click_match:
        target = click_match.group(1)
        click_target = click_match.group(2).strip()
        open_reply = open_windows_settings_page(f"open {target}")
        if not open_reply:
            return None
        time.sleep(2.0)
        try:
            from vision.screen_reader import click_on_text

            found = click_on_text(click_target)
        except Exception:
            found = False
        if found:
            return f"{open_reply} Then I clicked {click_target}."
        return f"{open_reply} I could not find {click_target} to click."

    find_match = re.match(r"^(?:open|show|go to) (.+?) and find (.+)$", normalized)
    if find_match:
        target = find_match.group(1)
        find_target = find_match.group(2).strip()
        open_reply = open_windows_settings_page(f"open {target}")
        if not open_reply:
            return None
        time.sleep(2.0)
        try:
            from vision.screen_reader import find_text_details

            details = find_text_details(find_target)
        except Exception:
            details = None
        if details:
            x, y = details["center"]
            return f"{open_reply} I found {details['text']} near position {x}, {y}."
        return f"{open_reply} I could not find {find_target} on that page."

    return None


def get_active_window_summary():
    try:
        active_window = gw.getActiveWindow()
    except Exception:
        active_window = None

    if not active_window:
        return "I could not detect the active window right now."

    title = (active_window.title or "").strip() or "Unknown window"
    return f"Active window is {title}."


def run_windows_voice_macro(command):
    normalized = " ".join((command or "").lower().strip().split())

    if normalized in ["work mode", "start work mode"]:
        launched = []
        for name in ["visual studio code", "windows terminal", "chrome"]:
            if name == "visual studio code":
                os.system('start "" "code"')
                launched.append("Visual Studio Code")
            else:
                reply = open_default_windows_app(f"open {name}")
                if reply and reply.startswith("Opening"):
                    launched.append(name.title())
        return "Work mode started: " + " | ".join(launched) if launched else "I could not start work mode right now."

    if normalized in ["study mode", "start study mode"]:
        launched = []
        for name in ["chrome", "notepad", "calculator"]:
            reply = open_default_windows_app(f"open {name}") if name != "chrome" else None
            if name == "chrome":
                os.system('start "" "chrome"')
                launched.append("Chrome")
            elif reply and reply.startswith("Opening"):
                launched.append(name.title())
        return "Study mode started: " + " | ".join(launched) if launched else "I could not start study mode right now."

    if normalized in ["quiet mode", "focus mode", "start quiet mode"]:
        pyautogui.hotkey("win", "a")
        return "Opened Quick Settings for quiet mode adjustments."

    return None
