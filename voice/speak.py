import sys
import threading
import time

import pyttsx3
import win32com.client
from colorama import Fore, Style, init

init(autoreset=True)

_engine = None
_sapi_voice = None
_engine_lock = threading.Lock()
_response_mode = "hybrid"
_mirror_voice_replies = True

SVS_FLAGS_ASYNC = 1
SVS_FPURGE_BEFORE_SPEAK = 2


def _get_sapi_voice():
    global _sapi_voice

    if _sapi_voice is None:
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        voice.Rate = 1
        voice.Volume = 100
        _sapi_voice = voice

    return _sapi_voice


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


def set_response_mode(mode):
    global _response_mode
    if mode in {"text", "voice", "hybrid"}:
        _response_mode = mode


def speak(text):
    should_print = _response_mode in {"text", "hybrid"} or (
        _response_mode == "voice" and _mirror_voice_replies
    )

    if should_print:
        typing_effect(text)

    if _response_mode in {"voice", "hybrid"}:
        try:
            with _engine_lock:
                try:
                    voice = _get_sapi_voice()
                    voice.Speak("", SVS_FLAGS_ASYNC | SVS_FPURGE_BEFORE_SPEAK)
                    voice.Speak(text)
                except Exception:
                    engine = _get_engine()
                    engine.stop()
                    engine.say(text)
                    engine.runAndWait()
        except Exception as error:
            print("TTS Error:", error)


def stop_speaking():
    global _engine, _sapi_voice

    try:
        with _engine_lock:
            if _sapi_voice is not None:
                _sapi_voice.Speak("", SVS_FLAGS_ASYNC | SVS_FPURGE_BEFORE_SPEAK)

            if _engine is not None:
                _engine.stop()
    except Exception as error:
        print("TTS Stop Error:", error)
