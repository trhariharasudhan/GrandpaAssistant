import json
import os
import re
import subprocess
import time

from controls.brightness_control import set_brightness_level
from controls.volume_control import set_volume_level
from utils.config import APP_ALIASES

DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data",
    "routines.json",
)

PRESET_ROUTINES = {
    "work": {
        "volume": 35,
        "brightness": 65,
        "apps": ["chrome", "notepad"],
        "message": "Work mode started.",
    },
    "study": {
        "volume": 20,
        "brightness": 55,
        "apps": ["chrome", "calculator"],
        "message": "Study mode started.",
    },
    "movie": {
        "volume": 70,
        "brightness": 35,
        "apps": [],
        "message": "Movie mode started.",
    },
}


def _load_custom_routines():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, dict):
                return data
    except Exception:
        return {}

    return {}


def _save_custom_routines(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def _all_routines():
    routines = dict(PRESET_ROUTINES)
    routines.update(_load_custom_routines())
    return routines


def list_routines():
    names = [f"{name} mode" for name in _all_routines().keys()]
    return "Available modes are: " + ", ".join(names) + "."


def _open_alias(alias):
    exe = APP_ALIASES.get(alias)
    if not exe:
        return

    try:
        subprocess.Popen(["start", exe], shell=True)
        time.sleep(0.2)
    except Exception:
        return


def _extract_mode_name(command, prefix):
    value = command.replace(prefix, "", 1).strip()
    value = value.replace(" mode", "").strip()
    return value


def _extract_number(pattern, command):
    match = re.search(pattern, command)
    if not match:
        return None
    return int(match.group(1))


def _extract_apps(command):
    match = re.search(r"apps?\s+([a-z0-9,\s]+)", command)
    if not match:
        return []

    raw_apps = match.group(1)
    apps = []
    for app in raw_apps.split(","):
        cleaned = app.strip().lower()
        if cleaned:
            apps.append(cleaned)
    return apps


def create_custom_routine(command):
    mode_name = _extract_mode_name(command, "create mode")
    if not mode_name:
        return "Tell me the mode name to create."

    volume = _extract_number(r"volume\s+(\d+)", command)
    brightness = _extract_number(r"brightness\s+(\d+)", command)
    apps = _extract_apps(command)

    custom_routines = _load_custom_routines()
    custom_routines[mode_name] = {
        "volume": 30 if volume is None else max(0, min(volume, 100)),
        "brightness": 50 if brightness is None else max(0, min(brightness, 100)),
        "apps": apps,
        "message": f"{mode_name.title()} mode started.",
    }
    _save_custom_routines(custom_routines)

    return (
        f"Custom mode {mode_name} created with volume "
        f"{custom_routines[mode_name]['volume']} and brightness "
        f"{custom_routines[mode_name]['brightness']}."
    )


def delete_custom_routine(command):
    mode_name = _extract_mode_name(command, "delete mode")
    if not mode_name:
        return "Tell me the mode name to delete."

    custom_routines = _load_custom_routines()
    if mode_name not in custom_routines:
        return "That custom mode does not exist."

    custom_routines.pop(mode_name)
    _save_custom_routines(custom_routines)
    return f"Deleted custom mode: {mode_name}"


def list_custom_routines():
    custom_routines = _load_custom_routines()
    if not custom_routines:
        return "You have no custom modes right now."

    names = [f"{name} mode" for name in custom_routines.keys()]
    return "Your custom modes are: " + ", ".join(names) + "."


def run_routine(command):
    routines = _all_routines()

    for name, config in routines.items():
        if name in command:
            set_volume_level(config["volume"], speak_feedback=False)
            set_brightness_level(config["brightness"], speak_feedback=False)

            for alias in config.get("apps", []):
                _open_alias(alias)

            return (
                f"{config['message']} Volume set to {config['volume']} percent and "
                f"brightness set to {config['brightness']} percent."
            )

    return None
