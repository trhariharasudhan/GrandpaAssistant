from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from .context import compact_text


logger = logging.getLogger(__name__)

STARTUP_FILE_NAME = "GrandpaAssistantStartup.cmd"
STARTUP_FOLDER_OVERRIDE_ENV = "GRANDPA_STARTUP_FOLDER"
REMINDER_SCHEDULER_ENABLED_ENV = "GRANDPA_REMINDER_SCHEDULER_ENABLED"
REMINDER_CHECK_INTERVAL_ENV = "GRANDPA_REMINDER_CHECK_INTERVAL_SECONDS"


def project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_entrypoint_path(root: Path | None = None) -> Path:
    return (root or project_root()) / "backend" / "main.py"


def default_python_executable() -> Path:
    return Path(sys.executable).resolve()


def startup_folder_path() -> Path:
    override = compact_text(os.getenv(STARTUP_FOLDER_OVERRIDE_ENV))
    if override:
        return Path(override).expanduser()
    appdata = compact_text(os.getenv("APPDATA"))
    if appdata:
        return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def startup_entry_path(*, startup_dir: Path | str | None = None) -> Path:
    return Path(startup_dir) / STARTUP_FILE_NAME if startup_dir is not None else startup_folder_path() / STARTUP_FILE_NAME


def validate_startup_target(
    *,
    python_executable: Path | str | None = None,
    entrypoint: Path | str | None = None,
) -> dict[str, Any]:
    python_path = Path(python_executable) if python_executable is not None else default_python_executable()
    entrypoint_path = Path(entrypoint) if entrypoint is not None else default_entrypoint_path()
    python_exists = python_path.exists()
    entrypoint_exists = entrypoint_path.exists()
    ok = python_exists and entrypoint_exists
    errors = []
    if not python_exists:
        errors.append("Python executable is missing: " + str(python_path))
    if not entrypoint_exists:
        errors.append("Startup entrypoint is missing: " + str(entrypoint_path))
    return {
        "ok": ok,
        "python_executable": str(python_path),
        "entrypoint": str(entrypoint_path),
        "errors": errors,
    }


def build_startup_script(
    *,
    python_executable: Path | str | None = None,
    entrypoint: Path | str | None = None,
    root: Path | str | None = None,
) -> str:
    root_path = Path(root) if root is not None else project_root()
    python_path = Path(python_executable) if python_executable is not None else default_python_executable()
    entrypoint_path = Path(entrypoint) if entrypoint is not None else default_entrypoint_path(root_path)
    return (
        "@echo off\n"
        "set GRANDPA_REMINDER_SCHEDULER_ENABLED=1\n"
        "if not defined GRANDPA_REMINDER_CHECK_INTERVAL_SECONDS set GRANDPA_REMINDER_CHECK_INTERVAL_SECONDS=30\n"
        f'cd /d "{root_path}"\n'
        f'start "" "{python_path}" "{entrypoint_path}" --text\n'
    )


def startup_status(*, startup_dir: Path | str | None = None, python_executable: Path | str | None = None, entrypoint: Path | str | None = None) -> dict[str, Any]:
    entry_path = startup_entry_path(startup_dir=startup_dir)
    validation = validate_startup_target(python_executable=python_executable, entrypoint=entrypoint)
    enabled = entry_path.exists()
    command_preview = build_startup_script(python_executable=python_executable, entrypoint=entrypoint)
    if enabled and validation["ok"]:
        message = "GrandpaAssistant Windows startup is enabled."
    elif enabled:
        message = "GrandpaAssistant Windows startup entry exists, but the target is not valid."
    else:
        message = "GrandpaAssistant Windows startup is disabled."
    return {
        "ok": True,
        "enabled": enabled,
        "startup_method": "windows_startup_folder_cmd",
        "startup_entry": str(entry_path),
        "startup_folder": str(entry_path.parent),
        "target_valid": bool(validation["ok"]),
        "python_executable": validation["python_executable"],
        "entrypoint": validation["entrypoint"],
        "command": command_preview,
        "errors": validation["errors"],
        "message": message,
    }


def enable_startup(*, startup_dir: Path | str | None = None, python_executable: Path | str | None = None, entrypoint: Path | str | None = None) -> dict[str, Any]:
    validation = validate_startup_target(python_executable=python_executable, entrypoint=entrypoint)
    entry_path = startup_entry_path(startup_dir=startup_dir)
    if not validation["ok"]:
        message = "I understood startup enable, but the startup target is not valid: " + "; ".join(validation["errors"])
        logger.warning("Windows startup enable failed: %s", message)
        return {"ok": False, "enabled": False, "startup_entry": str(entry_path), "message": message, "errors": validation["errors"]}

    script = build_startup_script(python_executable=python_executable, entrypoint=entrypoint)
    try:
        entry_path.parent.mkdir(parents=True, exist_ok=True)
        previous = entry_path.read_text(encoding="utf-8") if entry_path.exists() else ""
        if previous != script:
            entry_path.write_text(script, encoding="utf-8")
            action = "enabled"
        else:
            action = "already enabled"
    except Exception as error:
        message = "I understood startup enable, but writing the Startup folder entry failed: " + compact_text(error)
        logger.warning("Windows startup enable failed: %s", message)
        return {"ok": False, "enabled": False, "startup_entry": str(entry_path), "message": message, "errors": [compact_text(error)]}

    message = f"GrandpaAssistant Windows startup {action}. It will launch from the user Startup folder and enable the reminder scheduler."
    logger.info("Windows startup %s at %s", action, entry_path)
    return {"ok": True, "enabled": True, "startup_entry": str(entry_path), "message": message, "errors": []}


def disable_startup(*, startup_dir: Path | str | None = None) -> dict[str, Any]:
    entry_path = startup_entry_path(startup_dir=startup_dir)
    try:
        if entry_path.exists():
            entry_path.unlink()
            message = "GrandpaAssistant Windows startup disabled."
        else:
            message = "GrandpaAssistant Windows startup is already disabled."
    except Exception as error:
        message = "I understood startup disable, but removing the Startup folder entry failed: " + compact_text(error)
        logger.warning("Windows startup disable failed: %s", message)
        return {"ok": False, "enabled": entry_path.exists(), "startup_entry": str(entry_path), "message": message, "errors": [compact_text(error)]}
    logger.info("Windows startup disabled at %s", entry_path)
    return {"ok": True, "enabled": False, "startup_entry": str(entry_path), "message": message, "errors": []}


def startup_command_summary() -> str:
    status = startup_status()
    return (
        f"{status['message']} Method: {status['startup_method']}. "
        f"Startup entry: {status['startup_entry']}. Entrypoint: {status['entrypoint']}."
    )
