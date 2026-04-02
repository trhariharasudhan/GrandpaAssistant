import re
from difflib import SequenceMatcher

import speech_recognition as sr

from brain.memory_engine import get_memory
from utils.config import get_setting, update_setting

recognizer = sr.Recognizer()
_last_calibration_mode = None
_last_calibration_at = 0.0

VOICE_PROFILES = {
    "normal": {
        "ambient_duration": 0.35,
        "listen_timeout": 3,
        "phrase_time_limit": 5,
        "pause_threshold": 0.9,
        "non_speaking_duration": 0.35,
        "dynamic_energy_threshold": True,
        "energy_threshold": 180,
        "dynamic_energy_adjustment_ratio": 1.2,
        "recalibrate_interval": 20,
    },
    "sensitive": {
        "ambient_duration": 0.25,
        "listen_timeout": 4,
        "phrase_time_limit": 6,
        "pause_threshold": 1.1,
        "non_speaking_duration": 0.5,
        "dynamic_energy_threshold": True,
        "energy_threshold": 110,
        "dynamic_energy_adjustment_ratio": 1.08,
        "recalibrate_interval": 30,
    },
    "ultra_sensitive": {
        "ambient_duration": 0.2,
        "listen_timeout": 5,
        "phrase_time_limit": 7,
        "pause_threshold": 1.15,
        "non_speaking_duration": 0.55,
        "dynamic_energy_threshold": True,
        "energy_threshold": 90,
        "dynamic_energy_adjustment_ratio": 1.02,
        "recalibrate_interval": 45,
    },
    "noise_cancel": {
        "ambient_duration": 0.45,
        "listen_timeout": 3,
        "phrase_time_limit": 4,
        "pause_threshold": 0.65,
        "non_speaking_duration": 0.25,
        "dynamic_energy_threshold": True,
        "energy_threshold": 320,
        "dynamic_energy_adjustment_ratio": 1.6,
        "recalibrate_interval": 20,
    },
}

OFFLINE_DIRECT_ALIASES = {
    "time": "what is the time now",
    "time now": "what is the time now",
    "date": "what is the date",
    "date today": "what is the date",
    "today date": "what is the date",
    "agenda": "today agenda",
    "agenda today": "today agenda",
    "today agenda": "today agenda",
    "weather": "weather",
    "weather now": "weather",
    "settings": "show settings",
    "status": "system status",
    "offline help": "offline help",
    "notes": "list notes",
    "tasks": "show tasks",
    "reminders": "show reminders",
}

INTERRUPT_PHRASES = {
    "stop",
    "stop speaking",
    "wait",
    "cancel",
    "quiet",
    "be quiet",
    "pause",
    "listen",
}


def _postprocess_command(command):
    cleaned = " ".join(str(command or "").strip().lower().split())
    if not cleaned:
        return None

    # Voice input often includes the wake phrase even when we're already
    # listening for direct commands inside the UI.
    cleaned = re.sub(r"^(?:hey\s+grandpa|hello\s+grandpa|hi\s+grandpa)\b[\s,]*", "", cleaned)
    cleaned = re.sub(r"^(?:grandpa|odin)\b[\s,]*", "", cleaned)

    cleaned = re.sub(r"^(?:please|could you|can you)\s+", "", cleaned)
    cleaned = " ".join(cleaned.split())
    if get_setting("assistant.offline_mode_enabled", False):
        cleaned = OFFLINE_DIRECT_ALIASES.get(cleaned, cleaned)
    return cleaned or None


def normalize_phrase(text):
    return " ".join(re.sub(r"[^\w\s]", " ", str(text or "").lower()).split())


def wake_word_detected(command, wake_word=None):
    normalized_command = normalize_phrase(command)
    normalized_wake_word = normalize_phrase(wake_word or get_setting("wake_word", "hey grandpa"))
    wake_threshold = get_setting("voice.wake_match_threshold", 0.68)
    wake_aliases = {
        normalized_wake_word,
        "hi grandpa",
        "hello grandpa",
        "hey grand pa",
        "hay grandpa",
        "a grandpa",
        "hey grampa",
        "hi grampa",
    }

    if not normalized_command or not normalized_wake_word:
        return False

    for alias in wake_aliases:
        if alias and alias in normalized_command:
            return True

    command_words = normalized_command.split()
    wake_words = normalized_wake_word.split()
    wake_len = len(wake_words)

    if wake_len == 0 or len(command_words) < wake_len:
        return False

    for index in range(len(command_words) - wake_len + 1):
        window = " ".join(command_words[index:index + wake_len])
        if any(
            SequenceMatcher(None, window, alias).ratio() >= wake_threshold
            for alias in wake_aliases
            if alias
        ):
            return True

    return any(
        SequenceMatcher(None, normalized_command, alias).ratio() >= wake_threshold
        for alias in wake_aliases
        if alias
    )


def strip_wake_word(command, wake_word=None):
    normalized_command = normalize_phrase(command)
    normalized_wake_word = normalize_phrase(wake_word or get_setting("wake_word", "hey grandpa"))
    aliases = [
        normalized_wake_word,
        "hi grandpa",
        "hello grandpa",
        "hey grand pa",
        "hay grandpa",
        "hey grampa",
        "hi grampa",
    ]

    if not normalized_command or not normalized_wake_word:
        return ""

    for alias in aliases:
        if alias and normalized_command.startswith(alias):
            return normalized_command[len(alias):].strip()

    return ""


def looks_like_direct_command(command):
    cleaned = normalize_phrase(command)
    direct_prefixes = [
        "what ",
        "who ",
        "tell me ",
        "open ",
        "close ",
        "read ",
        "find ",
        "click ",
        "weather",
        "forecast",
        "dashboard",
        "status ",
        "show ",
        "list ",
        "add ",
        "delete ",
        "start ",
        "stop ",
        "take ",
        "summarize ",
        "background mode",
        "mute ",
        "unmute ",
        "enable ",
        "disable ",
        "set ",
        "update ",
        "plan ",
        "call ",
        "search ",
    ]
    return any(cleaned.startswith(prefix) for prefix in direct_prefixes)


def is_interrupt_phrase(command):
    return normalize_phrase(command) in INTERRUPT_PHRASES


def _active_voice_settings():
    mode = get_setting("voice.mode", "normal")
    base = dict(VOICE_PROFILES.get(mode, VOICE_PROFILES["normal"]))

    return {
        "mode": mode,
        "ambient_duration": get_setting("voice.ambient_duration", base["ambient_duration"]),
        "listen_timeout": get_setting("voice.listen_timeout", base["listen_timeout"]),
        "phrase_time_limit": get_setting("voice.phrase_time_limit", base["phrase_time_limit"]),
        "pause_threshold": get_setting("voice.pause_threshold", base["pause_threshold"]),
        "non_speaking_duration": get_setting(
            "voice.non_speaking_duration", base["non_speaking_duration"]
        ),
        "dynamic_energy_threshold": get_setting(
            "voice.dynamic_energy_threshold", base["dynamic_energy_threshold"]
        ),
        "energy_threshold": get_setting("voice.energy_threshold", base["energy_threshold"]),
        "dynamic_energy_adjustment_ratio": get_setting(
            "voice.dynamic_energy_adjustment_ratio",
            base["dynamic_energy_adjustment_ratio"],
        ),
        "recalibrate_interval": get_setting(
            "voice.recalibrate_interval", base["recalibrate_interval"]
        ),
        "min_command_chars": get_setting("voice.min_command_chars", 3),
        "post_wake_pause_seconds": get_setting("voice.post_wake_pause_seconds", 0.35),
        "empty_listen_backoff_seconds": get_setting("voice.empty_listen_backoff_seconds", 0.2),
        "wake_listen_timeout": get_setting("voice.wake_listen_timeout", 5),
        "wake_phrase_time_limit": get_setting("voice.wake_phrase_time_limit", 4),
        "wake_match_threshold": get_setting("voice.wake_match_threshold", 0.68),
        "wake_retry_window_seconds": get_setting("voice.wake_retry_window_seconds", 6),
        "follow_up_timeout_seconds": get_setting("voice.follow_up_timeout_seconds", 12),
        "wake_direct_fallback_enabled": get_setting("voice.wake_direct_fallback_enabled", True),
        "desktop_popup_enabled": get_setting("voice.desktop_popup_enabled", True),
        "desktop_chime_enabled": get_setting("voice.desktop_chime_enabled", True),
    }


def apply_voice_profile(profile_name):
    profile_name = profile_name.strip().lower().replace(" ", "_")
    if profile_name not in VOICE_PROFILES:
        return False

    profile = VOICE_PROFILES[profile_name]
    update_setting("voice.mode", profile_name)
    for key, value in profile.items():
        update_setting(f"voice.{key}", value)
    return True


def current_voice_mode():
    return get_setting("voice.mode", "normal")


def voice_status_summary():
    settings = _active_voice_settings()
    offline_mode = get_setting("assistant.offline_mode_enabled", False)
    return (
        f"Voice profile is {settings['mode']}. "
        f"Listen timeout is {settings['listen_timeout']} seconds. "
        f"Phrase limit is {settings['phrase_time_limit']} seconds. "
        f"Wake threshold is {settings['wake_match_threshold']}. "
        f"Follow up window is {settings['follow_up_timeout_seconds']} seconds. "
        f"Offline mode is {'on' if offline_mode else 'off'}."
    )


def _should_recalibrate(settings):
    import time

    global _last_calibration_mode, _last_calibration_at

    interval = settings["recalibrate_interval"]
    now = time.time()
    if _last_calibration_mode != settings["mode"]:
        return True
    return (now - _last_calibration_at) >= interval


def _mark_calibrated(settings):
    import time

    global _last_calibration_mode, _last_calibration_at

    _last_calibration_mode = settings["mode"]
    _last_calibration_at = time.time()


def listen(for_wake_word=False):
    settings = _active_voice_settings()

    recognizer.dynamic_energy_threshold = settings["dynamic_energy_threshold"]
    recognizer.energy_threshold = settings["energy_threshold"]
    recognizer.dynamic_energy_adjustment_ratio = settings[
        "dynamic_energy_adjustment_ratio"
    ]
    recognizer.pause_threshold = settings["pause_threshold"]
    recognizer.non_speaking_duration = settings["non_speaking_duration"]

    with sr.Microphone() as source:
        try:
            # Avoid recalibrating on every loop; otherwise quick speech can be
            # learned as ambient noise and the wake word gets missed.
            if _should_recalibrate(settings):
                recognizer.adjust_for_ambient_noise(
                    source, duration=settings["ambient_duration"]
                )
                _mark_calibrated(settings)

            audio = recognizer.listen(
                source,
                timeout=(
                    settings["wake_listen_timeout"]
                    if for_wake_word
                    else settings["listen_timeout"]
                ),
                phrase_time_limit=(
                    settings["wake_phrase_time_limit"]
                    if for_wake_word
                    else settings["phrase_time_limit"]
                ),
            )

            preferred_language = get_memory("personal.assistant.preferred_response_language") or "en-US"
            command = recognizer.recognize_google(audio, language=preferred_language)
            command = _postprocess_command(command)
            if not command:
                return None
            if len(command) < settings["min_command_chars"]:
                return None
            return command

        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception:
            return None
