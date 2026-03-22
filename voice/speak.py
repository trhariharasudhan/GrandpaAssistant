import sys
import threading
import time

import pyttsx3
from colorama import Fore, Style, init

init(autoreset=True)

_engine = None
_engine_lock = threading.Lock()


def _get_engine():
    global _engine

    if _engine is None:
        engine = pyttsx3.init("sapi5")
        voices = engine.getProperty("voices")
        engine.setProperty("voice", voices[0].id)
        engine.setProperty("rate", 170)
        engine.setProperty("volume", 1.0)
        _engine = engine

    return _engine


def typing_effect(text, delay=0.02):
    sys.stdout.write(Fore.GREEN + "Grandpa: " + Style.RESET_ALL)
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def speak(text):
    typing_effect(text)

    try:
        with _engine_lock:
            engine = _get_engine()
            engine.stop()
            engine.say(text)
            engine.runAndWait()
    except Exception as error:
        print("TTS Error:", error)


def stop_speaking():
    global _engine

    if _engine is None:
        return

    try:
        with _engine_lock:
            _engine.stop()
    except Exception as error:
        print("TTS Stop Error:", error)
