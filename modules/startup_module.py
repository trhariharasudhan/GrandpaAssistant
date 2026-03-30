import os

from utils.config import get_setting, update_setting


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STARTUP_DIR = os.path.join(
    os.environ.get("APPDATA", ""),
    "Microsoft",
    "Windows",
    "Start Menu",
    "Programs",
    "Startup",
)
STARTUP_SCRIPT_PATH = os.path.join(STARTUP_DIR, "GrandpaAssistantStartup.cmd")


def _launcher_executable():
    pythonw_path = os.path.join(BASE_DIR, ".venv", "Scripts", "pythonw.exe")
    python_path = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
    if os.path.exists(pythonw_path):
        return pythonw_path
    if os.path.exists(python_path):
        return python_path
    return "python"


def _startup_args():
    if get_setting("startup.tray_mode", False):
        return "--tray"
    return ""


def _startup_script_contents():
    launcher = _launcher_executable()
    args = _startup_args()
    args_part = f" {args}" if args else ""
    return (
        "@echo off\n"
        f'cd /d "{BASE_DIR}"\n'
        f'start "" "{launcher}" "{os.path.join(BASE_DIR, "main.py")}"{args_part}\n'
    )


def startup_auto_launch_status():
    enabled = get_setting("startup.auto_launch_enabled", False)
    file_exists = os.path.exists(STARTUP_SCRIPT_PATH)
    launch_mode = "tray" if get_setting("startup.tray_mode", False) else "ui"
    if enabled and file_exists:
        return f"Assistant startup launch is on. Launch mode is {launch_mode}."
    if enabled and not file_exists:
        return "Assistant startup launch is marked on, but the startup file is missing."
    return "Assistant startup launch is off."


def enable_startup_auto_launch():
    os.makedirs(STARTUP_DIR, exist_ok=True)
    with open(STARTUP_SCRIPT_PATH, "w", encoding="utf-8") as file:
        file.write(_startup_script_contents())
    update_setting("startup.auto_launch_enabled", True)
    launch_mode = "tray" if get_setting("startup.tray_mode", False) else "ui"
    return f"Assistant startup launch enabled. It will open in {launch_mode} mode when Windows starts."


def disable_startup_auto_launch():
    if os.path.exists(STARTUP_SCRIPT_PATH):
        os.remove(STARTUP_SCRIPT_PATH)
    update_setting("startup.auto_launch_enabled", False)
    return "Assistant startup launch disabled."


def refresh_startup_auto_launch():
    if not get_setting("startup.auto_launch_enabled", False):
        return
    os.makedirs(STARTUP_DIR, exist_ok=True)
    with open(STARTUP_SCRIPT_PATH, "w", encoding="utf-8") as file:
        file.write(_startup_script_contents())
