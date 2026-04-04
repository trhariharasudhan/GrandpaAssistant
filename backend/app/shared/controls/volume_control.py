from voice.speak import speak
import re
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import pyautogui


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
        percent = int(re.search(r"\d{1,3}", command).group())
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


def get_volume_percent():
    volume = get_volume_interface()
    if not volume:
        return None
    try:
        return int(round(volume.GetMasterVolumeLevelScalar() * 100))
    except Exception:
        return None


def _fallback_press(key_name, repeats=1):
    try:
        for _ in range(max(1, int(repeats))):
            pyautogui.press(key_name)
        return True
    except Exception:
        return False


def _fallback_set_volume(percent):
    target = max(0, min(int(percent), 100))
    # Approximate 0-100 with 50 media key steps on most Windows systems.
    if not _fallback_press("volumedown", repeats=50):
        return False
    steps_up = int(round(target / 2))
    if steps_up > 0 and not _fallback_press("volumeup", repeats=steps_up):
        return False
    return True


# ---------------- HANDLE VOLUME COMMANDS ----------------
def handle_volume(command):
    cmd = command.lower()
    volume_related = any(
        phrase in cmd
        for phrase in [
            "volume",
            "sound",
            "mute",
            "unmute",
        ]
    )

    volume = get_volume_interface()
    if not volume:
        if volume_related:
            match = re.search(r"(?:set|change|keep|make)\s+(?:the\s+)?(?:volume|sound)(?:\s+to)?\s+(\d{1,3})", cmd)
            if not match:
                match = re.search(r"^(?:volume|sound)\s+(\d{1,3})$", cmd)
            if match and _fallback_set_volume(int(match.group(1))):
                speak(f"Volume set to {max(0, min(int(match.group(1)), 100))} percent.")
                return True
            if any(phrase in cmd for phrase in ["volume up", "increase volume", "raise volume", "increase sound"]):
                if _fallback_press("volumeup", repeats=4):
                    speak("Volume increased.")
                    return True
            if any(phrase in cmd for phrase in ["volume down", "decrease volume", "lower volume", "decrease sound"]):
                if _fallback_press("volumedown", repeats=4):
                    speak("Volume decreased.")
                    return True
            if "unmute" in cmd and _fallback_press("volumeup", repeats=1):
                speak("Volume unmuted.")
                return True
            if "mute" in cmd and _fallback_press("volumemute", repeats=1):
                speak("Volume mute toggle sent.")
                return True
            if "set volume" in cmd or "set sound" in cmd:
                speak("I could not set volume right now.")
                return True
            speak("Volume control not available right now.")
            return True
        return False

    try:
        if any(
            phrase in cmd
            for phrase in [
                "volume status",
                "current volume",
                "what is volume",
                "sound level",
            ]
        ):
            current = get_volume_percent()
            if current is None:
                speak("I could not read the current volume.")
            else:
                speak(f"Volume is at {current} percent.")
            return True

        if any(phrase in cmd for phrase in ["volume up", "increase volume", "raise volume", "increase sound"]):
            current = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(min(current + 0.1, 1.0), None)
            speak("Volume increased.")
            return True

        if any(phrase in cmd for phrase in ["volume down", "decrease volume", "lower volume", "decrease sound"]):
            current = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(max(current - 0.1, 0.0), None)
            speak("Volume decreased.")
            return True

        if "unmute" in cmd:
            volume.SetMute(0, None)
            speak("Volume unmuted.")
            return True

        if "volume mute" in cmd or "mute volume" in cmd or "mute sound" in cmd:
            volume.SetMute(1, None)
            speak("Volume muted.")
            return True

        if "mute" in cmd:
            volume.SetMute(1, None)
            speak("Volume muted.")
            return True

        match = re.search(r"(?:set|change|keep|make)\s+(?:the\s+)?(?:volume|sound)(?:\s+to)?\s+(\d{1,3})", cmd)
        if not match:
            match = re.search(r"^(?:volume|sound)\s+(\d{1,3})$", cmd)
        if match:
            set_volume_level(int(match.group(1)))
            return True

        if "set volume" in cmd or "set sound" in cmd:
            set_volume_percentage(cmd)
            return True

    except Exception:
        speak("Volume control failed.")
        return True

    return False
