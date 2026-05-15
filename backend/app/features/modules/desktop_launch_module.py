"""Compatibility shim. Do not remove until imports are migrated."""

_DISABLED_MESSAGE = "Desktop UI is not part of this backend-only build."


def open_desktop_ui(*args, **kwargs):
    return False, _DISABLED_MESSAGE


def open_backend_ui(*args, **kwargs):
    return False, _DISABLED_MESSAGE


def open_desktop_shell(*args, **kwargs):
    return False, _DISABLED_MESSAGE


def launch_desktop_ui_for_tray(*args, **kwargs):
    return False, _DISABLED_MESSAGE


__all__ = [
    "open_desktop_ui",
    "open_backend_ui",
    "open_desktop_shell",
    "launch_desktop_ui_for_tray",
]
