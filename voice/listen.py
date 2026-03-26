import speech_recognition as sr

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


def listen():
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
                timeout=settings["listen_timeout"],
                phrase_time_limit=settings["phrase_time_limit"],
            )

            command = recognizer.recognize_google(audio)
            command = command.lower().strip()
            if len(command) < settings["min_command_chars"]:
                return None
            return command

        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception:
            return None
