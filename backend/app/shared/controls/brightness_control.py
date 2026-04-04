from voice.speak import speak
import screen_brightness_control as sbc
import re


def set_brightness_level(percent, speak_feedback=True):
    try:
        percent = max(0, min(int(percent), 100))
        sbc.set_brightness(percent)
        if speak_feedback:
            speak(f"Brightness set to {percent} percent.")
        return True
    except Exception:
        if speak_feedback:
            speak("Failed to change brightness.")
        return False


def _current_brightness_percent():
    try:
        value = sbc.get_brightness(display=0)
        if isinstance(value, list):
            value = value[0]
        return int(value)
    except Exception:
        return None


def handle_brightness(command):
    cmd = command.lower()
    try:
        if any(
            phrase in cmd
            for phrase in [
                "brightness status",
                "current brightness",
                "what is brightness",
                "brightness level",
            ]
        ):
            current = _current_brightness_percent()
            if current is None:
                speak("I could not read the current brightness.")
            else:
                speak(f"Brightness is at {current} percent.")
            return True

        if any(phrase in cmd for phrase in ["brightness up", "increase brightness", "raise brightness"]):
            current = _current_brightness_percent()
            if current is None:
                speak("I could not read the current brightness.")
                return True
            sbc.set_brightness(min(current + 10, 100))
            speak("Brightness increased.")
            return True

        if any(phrase in cmd for phrase in ["brightness down", "decrease brightness", "lower brightness"]):
            current = _current_brightness_percent()
            if current is None:
                speak("I could not read the current brightness.")
                return True
            sbc.set_brightness(max(current - 10, 0))
            speak("Brightness decreased.")
            return True

        match = re.search(r"(?:set|change|keep|make)\s+(?:the\s+)?brightness(?:\s+to)?\s+(\d{1,3})", cmd)
        if not match:
            match = re.search(r"^brightness\s+(\d{1,3})$", cmd)
        if match:
            return set_brightness_level(int(match.group(1)))

    except Exception:
        speak("Failed to change brightness.")
        return True
    return False
