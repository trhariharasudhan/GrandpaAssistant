import speech_recognition as sr

from utils.config import get_setting, update_setting

recognizer = sr.Recognizer()

VOICE_PROFILES = {
    "normal": {
        "ambient_duration": 0.8,
        "listen_timeout": 2,
        "phrase_time_limit": 4,
        "pause_threshold": 0.8,
        "non_speaking_duration": 0.35,
        "dynamic_energy_threshold": True,
        "energy_threshold": 220,
        "dynamic_energy_adjustment_ratio": 1.3,
    },
    "sensitive": {
        "ambient_duration": 1.0,
        "listen_timeout": 3,
        "phrase_time_limit": 5,
        "pause_threshold": 1.0,
        "non_speaking_duration": 0.45,
        "dynamic_energy_threshold": True,
        "energy_threshold": 160,
        "dynamic_energy_adjustment_ratio": 1.15,
    },
    "noise_cancel": {
        "ambient_duration": 1.2,
        "listen_timeout": 2,
        "phrase_time_limit": 4,
        "pause_threshold": 0.65,
        "non_speaking_duration": 0.25,
        "dynamic_energy_threshold": True,
        "energy_threshold": 320,
        "dynamic_energy_adjustment_ratio": 1.6,
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
            recognizer.adjust_for_ambient_noise(
                source, duration=settings["ambient_duration"]
            )

            audio = recognizer.listen(
                source,
                timeout=settings["listen_timeout"],
                phrase_time_limit=settings["phrase_time_limit"],
            )

            command = recognizer.recognize_google(audio)
            return command.lower()

        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception:
            return None
