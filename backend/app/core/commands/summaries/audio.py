from __future__ import annotations

from utils.config import get_setting
from voice.listen import current_voice_mode


def sound_status_summary() -> str:
    sounds_enabled = get_setting("sounds.enabled", True)
    start_sound = get_setting("sounds.start", True)
    success_sound = get_setting("sounds.success", True)
    error_sound = get_setting("sounds.error", True)
    return (
        f"Assistant sounds are {'on' if sounds_enabled else 'off'}. "
        f"Start sound is {'on' if start_sound else 'off'}. "
        f"Success sound is {'on' if success_sound else 'off'}. "
        f"Error sound is {'on' if error_sound else 'off'}."
    )


def chime_status_summary() -> str:
    chime_enabled = get_setting("voice.desktop_chime_enabled", True)
    popup_enabled = get_setting("voice.desktop_popup_enabled", True)
    wake_word = get_setting("wake_word", "hey grandpa")
    return (
        f"Desktop voice chime is {'on' if chime_enabled else 'off'}. "
        f"Desktop voice popup is {'on' if popup_enabled else 'off'}. "
        f"Wake word is {wake_word}."
    )


def notification_sound_summary() -> str:
    sounds_enabled = get_setting("sounds.enabled", True)
    success_sound = get_setting("sounds.success", True)
    error_sound = get_setting("sounds.error", True)
    chime_enabled = get_setting("voice.desktop_chime_enabled", True)
    popup_timeout = get_setting("notifications.popup_timeout_seconds", 10)
    return (
        f"Notification-related sounds follow assistant sounds, which are {'on' if sounds_enabled else 'off'}. "
        f"Success sound is {'on' if success_sound else 'off'}. "
        f"Error sound is {'on' if error_sound else 'off'}. "
        f"Voice chime is {'on' if chime_enabled else 'off'}. "
        f"Popup timeout is {popup_timeout} seconds."
    )


def voice_audio_readiness_summary() -> str:
    mode = current_voice_mode()
    stt_backend = get_setting("voice.stt_backend", "auto")
    tts_backend = get_setting("voice.tts_backend", "auto")
    whisper_model = get_setting("voice.whisper_model", "base")
    wake_timeout = get_setting("voice.wake_listen_timeout", 5)
    phrase_limit = get_setting("voice.wake_phrase_time_limit", 4)
    follow_up_timeout = get_setting("voice.follow_up_listen_timeout", 3)
    chime_enabled = get_setting("voice.desktop_chime_enabled", True)
    return (
        f"Voice audio readiness: profile is {mode}. "
        f"Speech input backend is {stt_backend}. "
        f"Speech output backend is {tts_backend}. "
        f"Whisper model is {whisper_model}. "
        f"Wake listen timeout is {wake_timeout} seconds. "
        f"Wake phrase limit is {phrase_limit} seconds. "
        f"Follow up listen timeout is {follow_up_timeout} seconds. "
        f"Desktop voice chime is {'on' if chime_enabled else 'off'}."
    )


def audio_status_summary() -> str:
    return f"{sound_status_summary()} {chime_status_summary()} {voice_audio_readiness_summary()}"
