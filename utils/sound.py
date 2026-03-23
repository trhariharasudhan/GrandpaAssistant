import os
from playsound import playsound

from utils.config import get_setting

SOUND_ALIASES = {
    "start": "start.wav",
    "success": "success.wav",
    "error": "error.wav",
}


def play_sound(filename):
    try:
        sound_key = filename.replace(".wav", "")
        if not get_setting("sounds.enabled", True):
            return
        if sound_key in SOUND_ALIASES and not get_setting(f"sounds.{sound_key}", True):
            return

        base_path = os.path.dirname(os.path.dirname(__file__))
        resolved_name = SOUND_ALIASES.get(filename, filename)
        sound_path = os.path.join(base_path, "sounds", resolved_name)

        if not os.path.exists(sound_path):
            print(f"Sound error: file not found - {resolved_name}")
            return

        playsound(sound_path)

    except Exception as e:
        print("Sound error:", e)
