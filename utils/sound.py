import os

try:
    import winsound
except ImportError:
    winsound = None

try:
    from playsound import playsound
except ImportError:
    playsound = None

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

        if playsound is not None:
            playsound(sound_path)
            return

        if winsound is not None:
            winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return

        print("Sound error: no supported sound backend is available.")

    except Exception as e:
        print("Sound error:", e)
