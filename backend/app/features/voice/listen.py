import importlib
import os
import re
import tempfile
import threading
from difflib import SequenceMatcher

import speech_recognition as sr

from brain.memory_engine import get_memory
from utils.config import get_setting, update_setting
from voice.speak import tts_backend_payload


recognizer = sr.Recognizer()
_last_calibration_mode = None
_last_calibration_at = 0.0
_whisper_module = None
_whisper_model = None
_whisper_model_name = ""
_whisper_model_error = ""
_last_stt_backend_used = ""
_last_stt_error = ""
_whisper_lock = threading.Lock()

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

SAFE_SINGLE_WORD_DIRECT_COMMANDS = {
    "time",
    "date",
    "weather",
    "forecast",
    "agenda",
    "status",
    "settings",
    "notes",
    "tasks",
    "reminders",
    "mute",
    "unmute",
    "wifi",
    "bluetooth",
    "camera",
    "microphone",
    "dashboard",
}

INTERRUPT_PHRASES = {
    "stop",
    "stop speaking",
    "stop now",
    "stop it",
    "wait",
    "wait a second",
    "hold on",
    "hold",
    "cancel",
    "cancel it",
    "quiet",
    "be quiet",
    "pause",
    "pause now",
    "enough",
    "listen",
}

_WAKE_ALIASES = (
    "hi grandpa",
    "hello grandpa",
    "hey grand pa",
    "hay grandpa",
    "a grandpa",
    "hey grampa",
    "hi grampa",
    "ok grandpa",
    "okay grandpa",
)

_FOLLOW_UP_FILLER_WORDS = {
    "hmm",
    "hmmm",
    "huh",
    "um",
    "uh",
    "mmm",
    "ah",
    "okay",
    "ok",
    "ya",
    "yeah",
    "yep",
    "grandpa",
}

_WAKE_TRAILING_FILLER_WORDS = {
    "please",
    "listen",
    "listening",
    "there",
    "ready",
    "hello",
    "hi",
    "hey",
    "can",
    "you",
    "hear",
    "me",
    "are",
}

_FOLLOW_UP_KEEP_ALIVE_PHRASES = {
    "continue",
    "go on",
    "keep going",
    "tell me more",
    "next",
    "what next",
    "carry on",
}

_GOOGLE_LANGUAGE_ALIASES = {
    "english": "en-US",
    "en": "en-US",
    "en-us": "en-US",
    "tamil": "ta-IN",
    "ta": "ta-IN",
    "ta-in": "ta-IN",
    "hindi": "hi-IN",
    "hi": "hi-IN",
    "hi-in": "hi-IN",
}

_WHISPER_LANGUAGE_ALIASES = {
    "english": "en",
    "en": "en",
    "en-us": "en",
    "tamil": "ta",
    "ta": "ta",
    "ta-in": "ta",
    "hindi": "hi",
    "hi": "hi",
    "hi-in": "hi",
    "auto": "auto",
}


def _postprocess_command(command):
    cleaned = " ".join(str(command or "").strip().lower().split())
    if not cleaned:
        return None

    cleaned = re.sub(r"^(?:hey\s+grandpa|hello\s+grandpa|hi\s+grandpa)\b[\s,]*", "", cleaned)
    cleaned = re.sub(r"^(?:grandpa|odin)\b[\s,]*", "", cleaned)
    cleaned = re.sub(r"^(?:please|could you|can you)\s+", "", cleaned)
    cleaned = " ".join(cleaned.split())
    if cleaned in _FOLLOW_UP_FILLER_WORDS:
        return None
    if get_setting("assistant.offline_mode_enabled", False):
        cleaned = OFFLINE_DIRECT_ALIASES.get(cleaned, cleaned)
    return cleaned or None


def normalize_phrase(text):
    return " ".join(re.sub(r"[^\w\s]", " ", str(text or "").lower()).split())


def _wake_aliases(wake_word=None):
    normalized_wake_word = normalize_phrase(wake_word or get_setting("wake_word", "hey grandpa"))
    return {
        alias
        for alias in {normalized_wake_word, *(normalize_phrase(item) for item in _WAKE_ALIASES)}
        if alias
    }


def _wake_window_matches(window_words, alias_words, threshold):
    if not window_words or not alias_words or len(window_words) != len(alias_words):
        return False

    if window_words == alias_words:
        return True

    first_word_score = SequenceMatcher(None, window_words[0], alias_words[0]).ratio()
    if first_word_score < max(0.72, threshold):
        return False

    if len(alias_words) > 1:
        second_word_score = SequenceMatcher(None, window_words[1], alias_words[1]).ratio()
        if second_word_score < max(0.58, threshold - 0.08):
            return False

    window = " ".join(window_words)
    alias = " ".join(alias_words)
    return SequenceMatcher(None, window, alias).ratio() >= threshold


def wake_word_detected(command, wake_word=None):
    normalized_command = normalize_phrase(command)
    wake_threshold = get_setting("voice.wake_match_threshold", 0.68)
    wake_aliases = _wake_aliases(wake_word)
    requires_prefix = bool(get_setting("voice.wake_requires_prefix", True))
    max_prefix_words = max(0, int(get_setting("voice.wake_max_prefix_words", 1) or 1))

    if not normalized_command or not wake_aliases:
        return False

    command_words = normalized_command.split()
    for alias in wake_aliases:
        alias_words = alias.split()
        alias_len = len(alias_words)
        if alias_len == 0 or len(command_words) < alias_len:
            continue
        for index in range(len(command_words) - alias_len + 1):
            if requires_prefix and index > max_prefix_words:
                break
            window_words = command_words[index:index + alias_len]
            if _wake_window_matches(window_words, alias_words, wake_threshold):
                return True

    return any(
        len(command_words) <= (len(alias.split()) + max_prefix_words + 2)
        and SequenceMatcher(None, normalized_command, alias).ratio() >= wake_threshold
        for alias in wake_aliases
    )


def strip_wake_word(command, wake_word=None):
    normalized_command = normalize_phrase(command)
    aliases = _wake_aliases(wake_word)
    wake_threshold = get_setting("voice.wake_match_threshold", 0.68)
    requires_prefix = bool(get_setting("voice.wake_requires_prefix", True))
    max_prefix_words = max(0, int(get_setting("voice.wake_max_prefix_words", 1) or 1))

    if not normalized_command or not aliases:
        return ""

    command_words = normalized_command.split()
    for alias in aliases:
        alias_words = alias.split()
        alias_len = len(alias_words)
        if alias_len == 0 or len(command_words) < alias_len:
            continue
        for index in range(len(command_words) - alias_len + 1):
            if requires_prefix and index > max_prefix_words:
                break
            window_words = command_words[index:index + alias_len]
            if _wake_window_matches(window_words, alias_words, wake_threshold):
                return " ".join(command_words[index + alias_len:]).strip()

    return ""


def is_wake_only_phrase(command, wake_word=None):
    trailing = strip_wake_word(command, wake_word)
    if not trailing:
        return True
    trailing_words = normalize_phrase(trailing).split()
    return len(trailing_words) <= 4 and all(word in _WAKE_TRAILING_FILLER_WORDS for word in trailing_words)


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


def should_run_direct_fallback(command):
    cleaned = normalize_phrase(command)
    if not cleaned or not looks_like_direct_command(cleaned):
        return False

    if cleaned in SAFE_SINGLE_WORD_DIRECT_COMMANDS:
        return True

    try:
        min_chars = max(4, int(get_setting("voice.direct_fallback_min_chars", 7)))
    except Exception:
        min_chars = 7

    try:
        min_words = max(1, int(get_setting("voice.direct_fallback_min_words", 2)))
    except Exception:
        min_words = 2

    return len(cleaned) >= min_chars and len(cleaned.split()) >= min_words


def is_interrupt_phrase(command):
    return normalize_phrase(command) in INTERRUPT_PHRASES


def sanitize_follow_up_command(command):
    cleaned = normalize_phrase(command)
    if not cleaned:
        return ""
    parts = [word for word in cleaned.split() if word not in _FOLLOW_UP_FILLER_WORDS]
    return " ".join(parts).strip()


def is_follow_up_keepalive_phrase(command):
    return normalize_phrase(command) in _FOLLOW_UP_KEEP_ALIVE_PHRASES


def continuous_conversation_enabled():
    return bool(get_setting("voice.continuous_conversation_enabled", True))


def follow_up_keep_alive_seconds():
    try:
        return max(3.0, float(get_setting("voice.follow_up_keep_alive_seconds", 12) or 12))
    except Exception:
        return 12.0


def current_stt_backend():
    backend = str(get_setting("voice.stt_backend", "auto") or "auto").strip().lower()
    return backend if backend in {"auto", "google", "whisper"} else "auto"


def _preferred_recognition_language():
    value = get_memory("personal.assistant.preferred_response_language") or "en-US"
    cleaned = str(value or "").strip()
    return cleaned or "en-US"


def _normalized_google_language(preferred_language=None):
    preferred = str(preferred_language or _preferred_recognition_language()).strip()
    if not preferred:
        return "en-US"
    return _GOOGLE_LANGUAGE_ALIASES.get(preferred.lower(), preferred)


def _configured_whisper_language():
    value = str(get_setting("voice.whisper_language", "auto") or "auto").strip().lower()
    return value or "auto"


def _resolved_whisper_language(preferred_language=None):
    configured = _configured_whisper_language()
    if configured != "auto":
        return _WHISPER_LANGUAGE_ALIASES.get(configured, configured)
    preferred = str(preferred_language or _preferred_recognition_language()).strip().lower()
    if not preferred:
        return None
    return _WHISPER_LANGUAGE_ALIASES.get(preferred, preferred.split("-")[0])


def _get_whisper_module():
    global _whisper_module
    if _whisper_module is None:
        _whisper_module = importlib.import_module("whisper")
    return _whisper_module


def _get_whisper_model(model_name):
    global _whisper_model, _whisper_model_name, _whisper_model_error
    with _whisper_lock:
        if _whisper_model is not None and _whisper_model_name == model_name:
            return _whisper_model
        try:
            whisper_module = _get_whisper_module()
            _whisper_model = whisper_module.load_model(model_name)
            _whisper_model_name = model_name
            _whisper_model_error = ""
            return _whisper_model
        except Exception as error:
            _whisper_model = None
            _whisper_model_name = ""
            _whisper_model_error = str(error)
            raise


def _recognition_backend_order(settings):
    backend = str(settings.get("stt_backend") or "auto").strip().lower()
    if backend == "whisper":
        return ["whisper", "google"]
    if backend == "google":
        return ["google", "whisper"]
    if get_setting("assistant.offline_mode_enabled", False):
        return ["whisper", "google"]
    return ["google", "whisper"]


def _active_voice_settings():
    mode = get_setting("voice.mode", "normal")
    base = dict(VOICE_PROFILES.get(mode, VOICE_PROFILES["normal"]))

    return {
        "mode": mode,
        "ambient_duration": get_setting("voice.ambient_duration", base["ambient_duration"]),
        "listen_timeout": get_setting("voice.listen_timeout", base["listen_timeout"]),
        "follow_up_listen_timeout": get_setting("voice.follow_up_listen_timeout", 3),
        "phrase_time_limit": get_setting("voice.phrase_time_limit", base["phrase_time_limit"]),
        "follow_up_phrase_time_limit": get_setting("voice.follow_up_phrase_time_limit", 5),
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
        "wake_requires_prefix": bool(get_setting("voice.wake_requires_prefix", True)),
        "wake_max_prefix_words": get_setting("voice.wake_max_prefix_words", 1),
        "wake_retry_window_seconds": get_setting("voice.wake_retry_window_seconds", 6),
        "follow_up_timeout_seconds": get_setting("voice.follow_up_timeout_seconds", 12),
        "continuous_conversation_enabled": bool(get_setting("voice.continuous_conversation_enabled", True)),
        "follow_up_keep_alive_seconds": get_setting("voice.follow_up_keep_alive_seconds", 12),
        "wake_direct_fallback_enabled": get_setting("voice.wake_direct_fallback_enabled", True),
        "direct_fallback_min_chars": get_setting("voice.direct_fallback_min_chars", 7),
        "direct_fallback_min_words": get_setting("voice.direct_fallback_min_words", 2),
        "duplicate_command_window_seconds": get_setting("voice.duplicate_command_window_seconds", 4.0),
        "wake_ack_cooldown_seconds": get_setting("voice.wake_ack_cooldown_seconds", 2.5),
        "error_recovery_backoff_seconds": get_setting("voice.error_recovery_backoff_seconds", 0.8),
        "interrupt_follow_up_seconds": get_setting("voice.interrupt_follow_up_seconds", 5),
        "desktop_popup_enabled": get_setting("voice.desktop_popup_enabled", True),
        "desktop_chime_enabled": get_setting("voice.desktop_chime_enabled", True),
        "stt_backend": current_stt_backend(),
        "whisper_model": get_setting("voice.whisper_model", "base"),
        "whisper_language": _configured_whisper_language(),
        "whisper_fp16": bool(get_setting("voice.whisper_fp16", False)),
        "whisper_condition_on_previous_text": bool(
            get_setting("voice.whisper_condition_on_previous_text", False)
        ),
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


def set_stt_backend(backend_name):
    normalized = str(backend_name or "").strip().lower()
    if normalized not in {"auto", "google", "whisper"}:
        return False
    update_setting("voice.stt_backend", normalized)
    return True


def current_voice_mode():
    return get_setting("voice.mode", "normal")


def stt_backend_payload():
    preferred_language = _preferred_recognition_language()
    settings = _active_voice_settings()
    order = _recognition_backend_order(settings)
    resolved_backend = order[0] if order else settings["stt_backend"]
    return {
        "configured_backend": settings["stt_backend"],
        "resolved_backend": resolved_backend,
        "fallback_order": order,
        "whisper_model": settings["whisper_model"],
        "whisper_language": _resolved_whisper_language(preferred_language=preferred_language) or "auto",
        "preferred_language": _normalized_google_language(preferred_language),
        "last_backend_used": _last_stt_backend_used or resolved_backend,
        "last_error": _last_stt_error,
        "whisper_load_error": _whisper_model_error,
    }


def stt_backend_status_summary():
    payload = stt_backend_payload()
    fallback_order = ", ".join(payload["fallback_order"])
    return (
        f"Speech input backend is set to {payload['configured_backend']}. "
        f"Current priority is {payload['resolved_backend']}. "
        f"Fallback order is {fallback_order}. "
        f"Whisper model is {payload['whisper_model']}. "
        f"Whisper language is {payload['whisper_language']}. "
        f"Preferred recognition language is {payload['preferred_language']}."
    )


def voice_status_summary():
    settings = _active_voice_settings()
    offline_mode = get_setting("assistant.offline_mode_enabled", False)
    stt_payload = stt_backend_payload()
    tts_payload = tts_backend_payload()
    return (
        f"Voice profile is {settings['mode']}. "
        f"Speech input backend is {stt_payload['configured_backend']} with {stt_payload['resolved_backend']} priority. "
        f"Speech output backend is {tts_payload['configured_backend']} with {tts_payload['resolved_backend']} priority. "
        f"Listen timeout is {settings['listen_timeout']} seconds. "
        f"Follow-up listen timeout is {settings['follow_up_listen_timeout']} seconds. "
        f"Phrase limit is {settings['phrase_time_limit']} seconds. "
        f"Follow-up phrase limit is {settings['follow_up_phrase_time_limit']} seconds. "
        f"Wake threshold is {settings['wake_match_threshold']}. "
        f"Strict wake detection is {'on' if settings['wake_requires_prefix'] else 'off'}. "
        f"Follow up window is {settings['follow_up_timeout_seconds']} seconds. "
        f"Continuous conversation is {'on' if settings['continuous_conversation_enabled'] else 'off'}. "
        f"Duplicate command guard is {settings['duplicate_command_window_seconds']} seconds. "
        f"Wake reply cooldown is {settings['wake_ack_cooldown_seconds']} seconds. "
        f"Whisper model is {settings['whisper_model']}. "
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


def _transcribe_with_google(audio, preferred_language):
    return recognizer.recognize_google(audio, language=_normalized_google_language(preferred_language))


def _transcribe_with_whisper(audio, settings, preferred_language):
    model = _get_whisper_model(settings["whisper_model"])
    whisper_language = _resolved_whisper_language(preferred_language=preferred_language)
    wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as handle:
            handle.write(wav_bytes)
            temp_path = handle.name

        result = model.transcribe(
            temp_path,
            language=whisper_language,
            fp16=bool(settings["whisper_fp16"]),
            condition_on_previous_text=bool(settings["whisper_condition_on_previous_text"]),
            task="transcribe",
        )
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    text = str((result or {}).get("text") or "").strip()
    if not text:
        raise ValueError("Whisper returned an empty transcription.")
    return text


def listen(for_wake_word=False, for_follow_up=False):
    global _last_stt_backend_used, _last_stt_error
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
            if _should_recalibrate(settings):
                recognizer.adjust_for_ambient_noise(
                    source, duration=settings["ambient_duration"]
                )
                _mark_calibrated(settings)

            listen_timeout = (
                settings["wake_listen_timeout"]
                if for_wake_word
                else (settings["follow_up_listen_timeout"] if for_follow_up else settings["listen_timeout"])
            )
            phrase_limit = (
                settings["wake_phrase_time_limit"]
                if for_wake_word
                else (
                    settings["follow_up_phrase_time_limit"]
                    if for_follow_up
                    else settings["phrase_time_limit"]
                )
            )

            audio = recognizer.listen(
                source,
                timeout=listen_timeout,
                phrase_time_limit=phrase_limit,
            )

            preferred_language = _preferred_recognition_language()
            backend_errors = []

            for backend_name in _recognition_backend_order(settings):
                try:
                    if backend_name == "whisper":
                        command = _transcribe_with_whisper(audio, settings, preferred_language)
                    else:
                        command = _transcribe_with_google(audio, preferred_language)

                    command = _postprocess_command(command)
                    _last_stt_backend_used = backend_name

                    if not command or len(command) < settings["min_command_chars"]:
                        _last_stt_error = ""
                        return None

                    _last_stt_error = ""
                    return command
                except sr.UnknownValueError:
                    backend_errors.append(f"{backend_name}: speech not understood")
                except Exception as error:
                    backend_errors.append(f"{backend_name}: {error}")

            _last_stt_error = " | ".join(backend_errors[:2])
            return None

        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception:
            return None
