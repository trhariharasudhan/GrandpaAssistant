import pygetwindow as gw
import keyboard
import time
from voice.speak import speak


def type_text_dynamic(command):
    text = command.replace("type", "", 1).strip()
    if text:
        keyboard.write(text, delay=0.05)
        speak("Text typed successfully.")
    else:
        speak("No text detected to type.")


def media_control(command):
    cmd = command.lower()

    # Try to focus Spotify window first
    try:
        spotify_win = gw.getWindowsWithTitle("Spotify")[0]
        spotify_win.activate()
        time.sleep(0.2)  # give focus to Spotify
    except IndexError:
        pass  # Spotify not open, media keys still work system-wide

    if "play" in cmd or "pause" in cmd:
        keyboard.send("play/pause media")
        speak("Play/Pause toggled.")
    elif "next" in cmd:
        keyboard.send("next track")
        speak("Next track played.")
    elif "previous" in cmd:
        keyboard.send("previous track")
        speak("Previous track played.")
