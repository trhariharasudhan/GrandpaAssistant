from voice.speak import speak
import re
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


# ---------------- GET VOLUME INTERFACE ----------------
def get_volume_interface():
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return volume
    except Exception:
        return None


# ---------------- SET VOLUME BY PERCENT ----------------
def set_volume_percentage(command):
    try:
        percent = int(re.search(r"\d+", command).group())
        set_volume_level(percent)
    except Exception:
        speak("Failed to set volume.")


def set_volume_level(percent, speak_feedback=True):
    try:
        volume = get_volume_interface()
        if not volume:
            speak("Volume control not available.")
            return

        percent = max(0, min(percent, 100))
        volume.SetMasterVolumeLevelScalar(percent / 100, None)

        if speak_feedback:
            speak(f"Volume set to {percent} percent.")
    except Exception:
        if speak_feedback:
            speak("Failed to set volume.")


# ---------------- HANDLE VOLUME COMMANDS ----------------
def handle_volume(command):
    cmd = command.lower()

    volume = get_volume_interface()
    if not volume:
        return False

    try:

        if "volume up" in cmd or "increase volume" in cmd:
            current = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(min(current + 0.1, 1.0), None)
            speak("Volume increased.")
            return True

        elif "volume down" in cmd or "decrease volume" in cmd:
            current = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(max(current - 0.1, 0.0), None)
            speak("Volume decreased.")
            return True


        if "volume mute" in cmd or "mute volume" in cmd:
            volume.SetMute(1, None)
            speak("Volume muted.")
            return True

        elif "mute" in cmd:
            volume.SetMute(1, None)
            speak("Volume muted.")
            return True

        elif "unmute" in cmd:
            volume.SetMute(0, None)
            speak("Volume unmuted.")
            return True

        elif "set volume" in cmd:
            set_volume_percentage(cmd)
            return True

    except Exception:
        speak("Volume control failed.")
        return True

    return False
