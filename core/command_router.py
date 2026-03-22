import datetime
import os
import re
import subprocess
import threading
import time

from brain.ai_engine import ask_ollama, clear_memory
from brain.database import log_command
from brain.memory_engine import (
    get_memory,
    remove_memory_field,
    search_memory,
    set_memory,
    update_memory_field,
)
from brain.question_analyzer import is_personal_question
from core.intent_router import try_handle_intent

from modules.calendar_module import (
    handle_calendar_queries,
    handle_difference,
    handle_offsets,
    get_relative_base,
    extract_specific_date,
    generate_full_info,
    get_period,
)
from modules.app_scan_module import (
    scan_installed_apps,
    scan_store_apps,
    save_apps_to_cache,
)
import modules.app_scan_module as app_scan_module
from modules.briefing_module import build_due_reminder_alert
from modules.media_module import media_control, type_text_dynamic
from modules.system_module import (
    take_screenshot,
    get_battery_info,
    handle_wifi,
    handle_bluetooth,
    handle_airplane,
    tell_joke,
    open_explorer,
    close_app,
    minimize_app,
    maximize_app,
    restore_app,
    switch_to_app,
    sleep_system,
    lock_system,
    switch_user,
    sign_out,
    perform_sign_out,
    restart_system,
    perform_restart,
    shutdown_system,
    perform_shutdown,
)
from modules.web_module import wikipedia_search
from controls.brightness_control import handle_brightness
from controls.volume_control import handle_volume, set_volume_percentage
from utils.sound import play_sound
from utils.config import APP_ALIASES
from vision.hand_mouse_control import run_hand_mouse
from vision.screen_reader import read_screen_text
from vision.screen_reader import click_on_text
from voice.speak import speak

mouse_stop_event = None
mouse_stop_requested_by_command = False
pending_confirmation = None


def _handle_memory_edit_command(command):
    patterns = [
        (r"^(?:update|change)\s+my\s+(.+?)\s+to\s+(.+)$", "update"),
        (r"^set\s+my\s+(.+?)\s+to\s+(.+)$", "update"),
        (r"^add\s+my\s+(.+?)\s+as\s+(.+)$", "update"),
        (r"^remember\s+my\s+(.+?)\s+as\s+(.+)$", "update"),
        (r"^remove\s+my\s+(.+)$", "remove"),
        (r"^delete\s+my\s+(.+)$", "remove"),
        (r"^clear\s+my\s+(.+)$", "remove"),
    ]

    for pattern, action in patterns:
        match = re.match(pattern, command)
        if not match:
            continue

        if action == "update":
            field_name = match.group(1).strip()
            raw_value = match.group(2).strip()
            return update_memory_field(field_name, raw_value)[1]

        field_name = match.group(1).strip()
        return remove_memory_field(field_name)[1]

    return None


# ---------------- PROCESS COMMAND ----------------
def process_command(command, INSTALLED_APPS, input_mode="text"):
    global mouse_stop_event, mouse_stop_requested_by_command, pending_confirmation

    command = command.lower().strip()
    if command:
        log_command(command, source=input_mode)

    if pending_confirmation:
        if command in ["yes", "confirm", "ok", "okay", "do it"]:
            action = pending_confirmation["action"]
            pending_confirmation = None
            action()
            return

        if command in ["no", "cancel", "stop", "never mind"]:
            pending_confirmation = None
            speak("Cancelled.")
            return

    if "read screen" in command or "what is on screen" in command:
        speak("Scanning screen")

        text = read_screen_text()

        print("\n===== SCREEN TEXT =====\n")
        print(text)
        print("\n========================\n")

        speak("Screen content printed")
        return

    if command.startswith("open file"):
        target = command.replace("open file", "").strip()

        speak(f"Searching for {target}")

        found = click_on_text(target)

        if found:
            speak("Opening it")
        else:
            speak("I couldn't find it on screen")

        return

    intent_result = try_handle_intent(command)
    if intent_result["handled"]:
        speak(intent_result["reply"])
        return

    now_dt = datetime.datetime.now()

    if "start mouse" in command:
        if mouse_stop_event and not mouse_stop_event.is_set():
            speak("Hand mouse is already running.")
            return

        speak("Starting hand mouse mode.")
        mouse_stop_event = threading.Event()
        mouse_stop_requested_by_command = False

        def notify_mouse_stopped():
            global mouse_stop_event, mouse_stop_requested_by_command
            mouse_stop_event = None
            if mouse_stop_requested_by_command:
                mouse_stop_requested_by_command = False
                return

            print("\nHand mouse stopped.")
            if input_mode == "text":
                print("You: ", end="", flush=True)

        def silent_run():
            run_hand_mouse(mouse_stop_event, on_stop=notify_mouse_stopped)

        threading.Thread(target=silent_run, daemon=True).start()

        return

    if "stop mouse" in command:
        if mouse_stop_event:
            mouse_stop_requested_by_command = True
            mouse_stop_event.set()
            mouse_stop_event = None
            speak("Stopping hand mouse")
        else:
            speak("Mouse is not running")

        return

    if "rescan apps" in command:

        INSTALLED_APPS.clear()

        new_apps = scan_installed_apps()
        store_apps = scan_store_apps()

        INSTALLED_APPS.update(new_apps)
        INSTALLED_APPS.update(store_apps)

        save_apps_to_cache(INSTALLED_APPS)

        speak("Applications rescanned and cache updated.")
        return

    # ----- calendar queries -----
    if handle_calendar_queries(command, speak):
        return

    # ----- brightness -----
    if handle_brightness(command):
        return

    # ----- volume -----
    if "percent" in command and any(w in command for w in ["volume", "sound"]):
        set_volume_percentage(command)
        return

    if handle_volume(command):
        return

    # ----- network / misc utilities -----
    if handle_wifi(command):
        return

    if handle_bluetooth(command):
        return

    if handle_airplane(command):
        return

    if "battery" in command:
        battery_msg = get_battery_info()
        if battery_msg:
            speak(battery_msg)
        else:
            speak("Unable to get battery information.")
        return

    # ----- advanced date handling -----
    diff_answer = handle_difference(command)
    if diff_answer:
        speak(diff_answer)
        return

    offset_date = handle_offsets(command)
    if offset_date:
        speak(generate_full_info(offset_date))
        return

    date_obj = get_relative_base(command) or extract_specific_date(command)
    if date_obj:
        speak(generate_full_info(date_obj))
        return

    # ----- memory and personal info -----
    if "my name is" in command:
        name = command.replace("my name is", "").strip()
        set_memory("personal.identity.name", name)
        speak(f"Okay, I will remember that your name is {name}")
        return

    if any(p in command for p in ["what is my name", "who am i", "tell my name"]):
        name = get_memory("personal.identity.name")
        if name:
            speak(f"You are {name}")
        else:
            speak("I don't know your name yet.")
        return

    memory_edit_reply = _handle_memory_edit_command(command)
    if memory_edit_reply:
        speak(memory_edit_reply)
        return

    # -------- HYBRID BRAIN --------

    if is_personal_question(command):
        memory_answer = search_memory(command)

        if memory_answer:
            speak(memory_answer)
            return

    if "your name" in command:
        speak("My name is Grandpa. I am your personal assistant.")
        return

    if "clear memory" in command:
        pending_confirmation = {
            "message": "Do you want to clear conversation memory?",
            "action": lambda: (clear_memory(), speak("Conversation memory cleared.")),
        }
        speak(pending_confirmation["message"])
        return

    if "who created you" in command:
        speak("I was created by my Captain.")
        return

    if "how are you" in command:
        speak("I am doing great! Thank you for asking.")
        return

    if any(word in command for word in ["morning", "afternoon", "evening", "night"]):
        speak(get_period())
        return

    if "joke" in command:
        speak(tell_joke())
        return

    if command.startswith(("who is", "what is", "tell me about")):
        response = wikipedia_search(command)
        speak(response)
        return

    # ----- basic system controls -----
    if "open explorer" in command:
        open_explorer()
        return

    if "take screenshot" in command or "screenshot" in command:
        take_screenshot()
        return

    if command.startswith("close"):
        pending_confirmation = {
            "message": "Are you sure you want to close that application?",
            "action": lambda cmd=command: close_app(cmd),
        }
        speak(pending_confirmation["message"])
        return

    if command.startswith("minimize"):
        minimize_app(command)
        return

    if command.startswith("maximize"):
        maximize_app(command)
        return

    if command.startswith("restore"):
        restore_app(command)
        return

    if command.startswith("switch to"):
        switch_to_app(command)
        return

    if "sleep" in command:
        pending_confirmation = {
            "message": "Are you sure you want to put the system to sleep?",
            "action": lambda: sleep_system(),
        }
        speak(pending_confirmation["message"])
        return

    if "lock" in command:
        lock_system()
        return

    if "switch user" in command:
        switch_user()
        return

    if "sign out" in command or "logout" in command:
        pending_confirmation = {
            "message": "Are you sure you want to sign out?",
            "action": lambda: (speak("Signing out"), perform_sign_out()),
        }
        speak(pending_confirmation["message"])
        return

    if command.strip() == "restart":
        pending_confirmation = {
            "message": "Are you sure you want to restart?",
            "action": lambda: (speak("Restarting the system"), perform_restart()),
        }
        speak(pending_confirmation["message"])
        return

    if command.strip() in ["shutdown", "shut down"]:
        pending_confirmation = {
            "message": "Are you sure you want to shut down?",
            "action": lambda: (speak("Shutting down the system"), perform_shutdown()),
        }
        speak(pending_confirmation["message"])
        return

    if command.startswith("open"):

        app_requested = command.replace("open", "").strip().lower()

        # Check alias dictionary
        for alias, exe in APP_ALIASES.items():
            if app_requested == alias:

                speak(f"Opening {alias}")
                time.sleep(0.5)

                def open_app():
                    subprocess.Popen(["start", exe], shell=True)

                threading.Thread(target=open_app, daemon=True).start()
                return

        # Check scanned installed apps
        for app_name, path in INSTALLED_APPS.items():

            if app_requested in app_name.lower():

                speak(f"Opening {app_name}")
                time.sleep(0.5)

                def open_app():
                    try:
                        if "!" in path:
                            subprocess.Popen(
                                f"explorer shell:AppsFolder\\{path}", shell=True
                            )
                        else:
                            os.startfile(path)
                    except Exception as e:
                        print("Open error:", e)
                        speak("Unable to open application.")

                threading.Thread(target=open_app, daemon=True).start()
                return

        speak("Application not found.")
        return

    if command.startswith("type"):
        type_text_dynamic(command)
        return

    if command.startswith(("play", "pause", "next", "previous")):
        media_control(command)
        return

    # ----- Context Follow-up Handling (Pronoun Support) -----
    if app_scan_module.LAST_TOPIC and any(
        word in command for word in ["he", "she", "his", "her", "they", "him"]
    ):
        response = ask_ollama(
            f"The user is asking about {app_scan_module.LAST_TOPIC}. {command}"
        )
        speak(response)
        return

    # -------- GENERAL AI RESPONSE --------
    try:
        response = ask_ollama(command)
        if response:
            speak(response)
        else:
            speak("I did not get a proper response.")

    except Exception as e:
        print("Error:", e)

        play_sound("error.wav")
        speak("Something went wrong")
