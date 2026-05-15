from __future__ import annotations

from automation.startup_module import startup_auto_launch_status
from utils.config import get_setting


def interface_mode_status_summary() -> str:
    interface_mode = str(get_setting("startup.interface_mode", "terminal") or "terminal").lower()
    terminal_input_mode = str(get_setting("startup.terminal_input_mode", "text") or "text").lower()
    return (
        f"Interface mode is {interface_mode}. "
        f"Terminal input mode is {terminal_input_mode}."
    )


def tray_mode_status_summary() -> str:
    tray_mode = get_setting("startup.tray_mode", False)
    return f"Tray startup is {'on' if tray_mode else 'off'}."


def desktop_backend_mode_summary() -> str:
    interface_line = interface_mode_status_summary()
    tray_line = tray_mode_status_summary()
    return f"Backend-only desktop mode is active. {interface_line} {tray_line}"


def launcher_readiness_status_summary() -> str:
    return (
        "Backend launch command remains python backend\\desktop_backend_entry.py. "
        f"{interface_mode_status_summary()} {tray_mode_status_summary()}"
    )


def startup_status_summary() -> str:
    return f"{startup_auto_launch_status()} {interface_mode_status_summary()} {tray_mode_status_summary()}"
