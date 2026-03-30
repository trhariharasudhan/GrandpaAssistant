import os
import subprocess
import webbrowser

from utils.config import get_setting


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
FRONTEND_BROWSER_SCRIPT = os.path.join(BASE_DIR, "start_react_frontend.cmd")
FRONTEND_DESKTOP_SCRIPT = os.path.join(BASE_DIR, "start_react_electron.cmd")
FRONTEND_URL = "http://127.0.0.1:4173"


def _launch_script(script_path):
    if not os.path.exists(script_path):
        return False, "The React launcher script is missing."

    try:
        subprocess.Popen(
            ["cmd.exe", "/c", script_path],
            cwd=BASE_DIR,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        return True, "Launcher started."
    except Exception:
        return False, "I could not start the React launcher right now."


def open_react_browser_ui():
    return _launch_script(FRONTEND_BROWSER_SCRIPT)


def open_react_desktop_ui():
    return _launch_script(FRONTEND_DESKTOP_SCRIPT)


def open_react_browser_url_only():
    try:
        webbrowser.open(FRONTEND_URL)
        return True, "Opened the React UI in your browser."
    except Exception:
        return False, "I could not open the React UI in the browser."


def tray_react_status():
    enabled = get_setting("startup.react_ui_on_tray_enabled", False)
    mode = get_setting("startup.react_ui_on_tray_mode", "browser")
    return f"Tray React launch is {'on' if enabled else 'off'}. Mode is {mode}."


def launch_react_for_tray():
    if not get_setting("startup.react_ui_on_tray_enabled", False):
        return False, "Tray React launch is off."

    mode = get_setting("startup.react_ui_on_tray_mode", "browser")
    if mode == "desktop":
        return open_react_desktop_ui()
    return open_react_browser_ui()
