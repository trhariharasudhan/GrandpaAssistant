from __future__ import annotations

from utils.config import get_setting


def get_pinned_commands() -> list[str]:
    return []


def is_quick_overlay_open() -> bool:
    return False


def list_pinned_commands() -> str:
    return "No pinned overlay commands."


def overlay_status_summary() -> str:
    overlay_enabled = get_setting("overlay.hotkey_enabled", True)
    overlay_hotkey = get_setting("overlay.hotkey", "ctrl+shift+space")
    open_state = "open" if is_quick_overlay_open() else "closed"
    pinned = get_pinned_commands()
    return (
        f"Quick command overlay hotkey is {'on' if overlay_enabled else 'off'}. "
        f"Overlay hotkey is {overlay_hotkey}. "
        f"Overlay is currently {open_state}. "
        f"Pinned command count is {len(pinned)}."
    )


def quick_overlay_status_summary() -> str:
    return overlay_status_summary()


def pinned_commands_summary() -> str:
    return list_pinned_commands()


def hotkey_status_summary() -> str:
    overlay_enabled = get_setting("overlay.hotkey_enabled", True)
    overlay_hotkey = get_setting("overlay.hotkey", "ctrl+shift+space")
    ocr_enabled = get_setting("ocr.region_hotkey_enabled", True)
    ocr_hotkey = get_setting("ocr.region_hotkey", "ctrl+shift+o")
    return (
        f"Quick overlay hotkey is {overlay_hotkey} and is {'on' if overlay_enabled else 'off'}. "
        f"OCR region hotkey is {ocr_hotkey} and is {'on' if ocr_enabled else 'off'}."
    )


def overlay_help_summary() -> str:
    return (
        "Overlay status can show quick overlay status, hotkey status, and pinned commands. "
        "Pin, unpin, move, open, close, and hotkey change commands remain separate action commands."
    )
