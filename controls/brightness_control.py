from voice.speak import speak
import screen_brightness_control as sbc


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


def handle_brightness(command):
    cmd = command.lower()
    try:
        if "brightness up" in cmd:
            sbc.set_brightness(sbc.get_brightness(display=0)[0] + 10)
            speak("Brightness increased.")
            return True
        elif "brightness down" in cmd:
            sbc.set_brightness(max(sbc.get_brightness(display=0)[0] - 10, 0))
            speak("Brightness decreased.")
            return True
    except Exception:
        speak("Failed to change brightness.")
    return False
