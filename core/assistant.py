import os
import sys
import threading
import time

from colorama import Fore, Style, init

from core.command_router import process_command
from modules.app_scan_module import categorize_apps, get_all_apps, scan_store_apps
from modules.briefing_module import build_daily_brief, build_due_reminder_alert
from utils.sound import play_sound
from vision.hand_mouse_control import run_hand_mouse
from voice.listen import listen
from voice.speak import speak, stop_speaking

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

try:
    from absl import logging
except ImportError:
    logging = None
else:
    logging.set_verbosity(logging.ERROR)

init(autoreset=True)

INSTALLED_APPS = {}
WAKE_WORD = "hey grandpa"
INITIAL_TIMEOUT = 15
ACTIVE_TIMEOUT = 60

stop_event = threading.Event()
hand_mouse_thread = None


def glowing_cursor():
    while True:
        sys.stdout.write("\rYou: *")
        sys.stdout.flush()
        time.sleep(0.5)
        sys.stdout.write("\rYou:  ")
        sys.stdout.flush()
        time.sleep(0.5)


def main():
    global INSTALLED_APPS

    INSTALLED_APPS = get_all_apps()
    INSTALLED_APPS.update(scan_store_apps())
    categorized = categorize_apps(INSTALLED_APPS)

    print("\n========= INSTALLED APPLICATIONS =========")
    print("Total apps found:", len(INSTALLED_APPS))

    for category, apps in categorized.items():
        if apps:
            print(f"\n--- {category} ({len(apps)}) ---")
            for app in apps:
                print("  *", app)

    speak("Hello Grandchild!")
    speak(build_daily_brief())
    urgent_alert = build_due_reminder_alert()
    if urgent_alert != "No urgent reminders right now.":
        speak(urgent_alert)

    try:
        print("\nChoose to enter input mode (1 - Voice / 2 - Text): ", end="")
        mode = input().strip()
    except KeyboardInterrupt:
        print("\nExiting Grandpa Assistant...")
        speak("Goodbye Captain!")
        stop_event.set()
        return

    if mode == "1":
        voice_mode()
    elif mode == "2":
        play_sound("start.wav")
        speak("Text mode activated.")
        print()
        text_mode()
    else:
        print("Invalid mode selected.")
        speak("Invalid mode selected.")


def start_hand_mouse():
    global hand_mouse_thread

    if hand_mouse_thread and hand_mouse_thread.is_alive():
        speak("Hand mouse already running")
        return

    stop_event.clear()
    hand_mouse_thread = threading.Thread(
        target=run_hand_mouse, args=(stop_event,), daemon=True
    )
    hand_mouse_thread.start()
    speak("Starting hand mouse mode")


def stop_hand_mouse():
    stop_event.set()
    speak("Stopping hand mouse")


def voice_mode():
    speak("Voice mode with wake word activated.")
    time.sleep(0.3)
    print()

    current_timeout = INITIAL_TIMEOUT
    active_mode = False
    last_active_time = 0

    try:
        while True:
            if not active_mode:
                stop_flag = {"stop": False}

                def animate_wait():
                    dots = 0
                    while not stop_flag["stop"]:
                        dots = (dots % 3) + 1
                        sys.stdout.write("\rWaiting for wake word" + "." * dots + "   ")
                        sys.stdout.flush()
                        time.sleep(0.4)
                    sys.stdout.write("\r" + " " * 60 + "\r")
                    sys.stdout.flush()

                anim_thread = threading.Thread(target=animate_wait, daemon=True)
                anim_thread.start()

                try:
                    command = listen()
                    if not command:
                        continue
                finally:
                    stop_flag["stop"] = True
                    anim_thread.join()

                command = command.lower().strip()

                if WAKE_WORD in command:
                    speak("Yes Captain?")
                    time.sleep(0.5)
                    active_mode = True
                    last_active_time = time.time()
                    current_timeout = INITIAL_TIMEOUT

                continue

            stop_flag = {"stop": False}
            command_container = {"cmd": None}

            def countdown_timer():
                while not stop_flag["stop"]:
                    elapsed = time.time() - last_active_time
                    remaining = max(0, int(current_timeout - elapsed))
                    sys.stdout.write(f"\rListening for command... ({remaining}s)   ")
                    sys.stdout.flush()

                    if remaining <= 0:
                        break

                    time.sleep(1)

            def listen_command():
                command_container["cmd"] = listen()
                stop_flag["stop"] = True

            timer_thread = threading.Thread(target=countdown_timer, daemon=True)
            listen_thread = threading.Thread(target=listen_command, daemon=True)

            timer_thread.start()
            listen_thread.start()

            listen_thread.join()
            stop_flag["stop"] = True
            timer_thread.join()

            command = command_container["cmd"]

            if time.time() - last_active_time > current_timeout:
                active_mode = False
                sys.stdout.write("\r" + " " * 60 + "\r")
                print("Going back to sleep mode...\n")
                continue

            if not command:
                continue

            command = command.lower().strip()
            last_active_time = time.time()

            if command == "exit assistant":
                speak("Goodbye Captain!")
                break

            sys.stdout.write("\r" + " " * 60 + "\r")
            print(f"You said: {command}")

            if command == "stop speaking":
                stop_speaking()
                continue

            process_command(command, INSTALLED_APPS, input_mode="voice")
            current_timeout = ACTIVE_TIMEOUT
            print()

    except KeyboardInterrupt:
        print()
        speak("Goodbye Captain!")


def text_mode():
    while True:
        try:
            print(Fore.CYAN + "You: " + Style.RESET_ALL, end="", flush=True)
            command = input().strip().lower()

            if not command:
                continue

            if command in ["exit", "quit"]:
                speak("Goodbye Captain!")
                break

            process_command(command, INSTALLED_APPS, input_mode="text")
            play_sound("start.wav")
            print()

        except KeyboardInterrupt:
            print()
            speak("Goodbye Captain!")
            break
