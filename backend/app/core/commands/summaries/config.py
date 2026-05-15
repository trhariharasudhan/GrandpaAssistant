from __future__ import annotations

from utils.config import get_setting

from .audio import sound_status_summary, voice_audio_readiness_summary
from .interface import interface_mode_status_summary, launcher_readiness_status_summary, tray_mode_status_summary
from .notification import notification_status_summary, popup_alert_status_summary
from .overlay import hotkey_status_summary


def feature_toggle_summary() -> str:
    offline_mode = get_setting("assistant.offline_mode_enabled", False)
    developer_mode = get_setting("assistant.developer_mode_enabled", False)
    focus_mode = get_setting("assistant.focus_mode_enabled", False)
    chatgpt_mode_full = get_setting("assistant.chatgpt_mode_full", False)
    compact_voice_replies = get_setting("assistant.compact_voice_replies", True)
    continuous_voice = get_setting("voice.continuous_conversation_enabled", True)
    wake_fallback = get_setting("voice.wake_direct_fallback_enabled", True)
    overlay_enabled = get_setting("overlay.hotkey_enabled", True)
    return (
        f"Offline mode is {'on' if offline_mode else 'off'}. "
        f"Developer mode is {'on' if developer_mode else 'off'}. "
        f"Focus mode is {'on' if focus_mode else 'off'}. "
        f"ChatGPT mode full is {'on' if chatgpt_mode_full else 'off'}. "
        f"Compact voice replies are {'on' if compact_voice_replies else 'off'}. "
        f"Continuous conversation is {'on' if continuous_voice else 'off'}. "
        f"Wake direct fallback is {'on' if wake_fallback else 'off'}. "
        f"Quick overlay is {'on' if overlay_enabled else 'off'}."
    )


def environment_config_readiness_summary() -> str:
    return (
        "Environment config readiness: backend-only Windows assistant config is readable. "
        f"{launcher_readiness_status_summary()} {voice_audio_readiness_summary()}"
    )


def settings_status_summary() -> str:
    wake_word = get_setting("wake_word", "hey grandpa")
    persona_mode = get_setting("assistant.persona", "friendly")
    initial_timeout = get_setting("initial_timeout", 15)
    active_timeout = get_setting("active_timeout", 60)
    return (
        f"Settings are readable. Wake word is {wake_word}. "
        f"Persona mode is {persona_mode}. "
        f"Initial timeout is {initial_timeout} seconds. "
        f"Active timeout is {active_timeout} seconds."
    )


def config_status_summary() -> str:
    return f"{settings_status_summary()} {interface_mode_status_summary()} {feature_toggle_summary()}"


def assistant_settings_summary() -> str:
    return (
        f"Current settings: {settings_status_summary()} "
        f"{interface_mode_status_summary()} "
        f"{tray_mode_status_summary()} "
        f"{sound_status_summary()} "
        f"{notification_status_summary()} "
        f"{popup_alert_status_summary()} "
        f"{hotkey_status_summary()} "
        f"{feature_toggle_summary()}"
    )
