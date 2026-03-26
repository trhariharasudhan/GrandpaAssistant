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
from core.tray_manager import start_tray, stop_tray

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
from modules.dictation_module import start_dictation, stop_dictation
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
from utils.config import APP_ALIASES, get_setting, update_setting
from vision.hand_mouse_control import run_hand_mouse
from vision.screen_reader import (
    capture_selected_region,
    click_on_text,
    click_on_text_in_region,
    find_text_details,
    find_text_details_in_region,
    is_text_visible,
    read_named_screen_region,
    read_screen_text,
    read_selected_area_text,
)
from voice.listen import apply_voice_profile, current_voice_mode
from voice.speak import (
    append_streaming_reply,
    end_streaming_reply,
    speak,
    start_streaming_reply,
)

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


def _handle_config_command(command):
    wake_word_match = re.match(r"^(?:set|change|update)\s+wake word\s+to\s+(.+)$", command)
    if wake_word_match:
        new_wake_word = wake_word_match.group(1).strip().strip("\"'")
        if not new_wake_word:
            return "Tell me the new wake word."
        update_setting("wake_word", new_wake_word)
        return f"Wake word updated to {new_wake_word}. Restart the assistant to use the new wake word."

    initial_timeout_match = re.match(
        r"^(?:set|change|update)\s+initial timeout\s+to\s+(\d+)$", command
    )
    if initial_timeout_match:
        timeout_value = int(initial_timeout_match.group(1))
        update_setting("initial_timeout", timeout_value)
        return f"Initial timeout updated to {timeout_value} seconds."

    active_timeout_match = re.match(
        r"^(?:set|change|update)\s+active timeout\s+to\s+(\d+)$", command
    )
    if active_timeout_match:
        timeout_value = int(active_timeout_match.group(1))
        update_setting("active_timeout", timeout_value)
        return f"Active timeout updated to {timeout_value} seconds."

    wake_pause_match = re.match(
        r"^(?:set|change|update)\s+post wake pause\s+to\s+(\d+(?:\.\d+)?)$", command
    )
    if wake_pause_match:
        pause_value = max(0.1, float(wake_pause_match.group(1)))
        update_setting("voice.post_wake_pause_seconds", pause_value)
        return f"Post wake pause updated to {pause_value} seconds."

    backoff_match = re.match(
        r"^(?:set|change|update)\s+empty listen backoff\s+to\s+(\d+(?:\.\d+)?)$", command
    )
    if backoff_match:
        backoff_value = max(0.0, float(backoff_match.group(1)))
        update_setting("voice.empty_listen_backoff_seconds", backoff_value)
        return f"Empty listen backoff updated to {backoff_value} seconds."

    wake_timeout_match = re.match(
        r"^(?:set|change|update)\s+wake listen timeout\s+to\s+(\d+(?:\.\d+)?)$", command
    )
    if wake_timeout_match:
        timeout_value = max(1.0, float(wake_timeout_match.group(1)))
        update_setting("voice.wake_listen_timeout", timeout_value)
        return f"Wake listen timeout updated to {timeout_value} seconds."

    wake_phrase_match = re.match(
        r"^(?:set|change|update)\s+wake phrase time limit\s+to\s+(\d+(?:\.\d+)?)$", command
    )
    if wake_phrase_match:
        phrase_value = max(1.0, float(wake_phrase_match.group(1)))
        update_setting("voice.wake_phrase_time_limit", phrase_value)
        return f"Wake phrase time limit updated to {phrase_value} seconds."

    wake_threshold_match = re.match(
        r"^(?:set|change|update)\s+wake match threshold\s+to\s+(0(?:\.\d+)?|1(?:\.0+)?)$", command
    )
    if wake_threshold_match:
        threshold_value = min(1.0, max(0.4, float(wake_threshold_match.group(1))))
        update_setting("voice.wake_match_threshold", threshold_value)
        return f"Wake match threshold updated to {threshold_value}."

    wake_retry_match = re.match(
        r"^(?:set|change|update)\s+wake retry window\s+to\s+(\d+(?:\.\d+)?)$", command
    )
    if wake_retry_match:
        retry_value = max(1.0, float(wake_retry_match.group(1)))
        update_setting("voice.wake_retry_window_seconds", retry_value)
        return f"Wake retry window updated to {retry_value} seconds."

    browser_delay_match = re.match(
        r"^(?:set|change|update)\s+browser load delay\s+to\s+(\d+)$", command
    )
    if browser_delay_match:
        delay_value = max(1, int(browser_delay_match.group(1)))
        update_setting("browser.page_load_delay_seconds", delay_value)
        return f"Browser load delay updated to {delay_value} seconds."

    whatsapp_delay_match = re.match(
        r"^(?:set|change|update)\s+whatsapp load delay\s+to\s+(\d+)$", command
    )
    if whatsapp_delay_match:
        delay_value = max(1, int(whatsapp_delay_match.group(1)))
        update_setting("browser.whatsapp_load_delay_seconds", delay_value)
        return f"WhatsApp load delay updated to {delay_value} seconds."

    gmail_delay_match = re.match(
        r"^(?:set|change|update)\s+gmail load delay\s+to\s+(\d+)$", command
    )
    if gmail_delay_match:
        delay_value = max(1, int(gmail_delay_match.group(1)))
        update_setting("browser.gmail_load_delay_seconds", delay_value)
        return f"Gmail load delay updated to {delay_value} seconds."

    popup_timeout_match = re.match(
        r"^(?:set|change|update)\s+popup timeout\s+to\s+(\d+)$", command
    )
    if popup_timeout_match:
        timeout_value = max(3, int(popup_timeout_match.group(1)))
        update_setting("notifications.popup_timeout_seconds", timeout_value)
        return f"Popup timeout updated to {timeout_value} seconds."

    popup_cooldown_match = re.match(
        r"^(?:set|change|update)\s+popup cooldown\s+to\s+(\d+)$", command
    )
    if popup_cooldown_match:
        cooldown_value = max(0, int(popup_cooldown_match.group(1)))
        update_setting("notifications.popup_cooldown_seconds", cooldown_value)
        return f"Popup cooldown updated to {cooldown_value} seconds."

    if command in ["show settings", "show config", "settings"]:
        wake_word = get_setting("wake_word", "hey grandpa")
        tray_mode = get_setting("startup.tray_mode", False)
        voice_mode = current_voice_mode()
        persona_mode = get_setting("assistant.persona", "friendly")
        sounds_enabled = get_setting("sounds.enabled", True)
        start_sound = get_setting("sounds.start", True)
        success_sound = get_setting("sounds.success", True)
        error_sound = get_setting("sounds.error", True)
        initial_timeout = get_setting("initial_timeout", 15)
        active_timeout = get_setting("active_timeout", 60)
        post_wake_pause = get_setting("voice.post_wake_pause_seconds", 0.35)
        empty_backoff = get_setting("voice.empty_listen_backoff_seconds", 0.2)
        wake_listen_timeout = get_setting("voice.wake_listen_timeout", 5)
        wake_phrase_limit = get_setting("voice.wake_phrase_time_limit", 4)
        wake_match_threshold = get_setting("voice.wake_match_threshold", 0.68)
        wake_retry_window = get_setting("voice.wake_retry_window_seconds", 6)
        browser_delay = get_setting("browser.page_load_delay_seconds", 3)
        whatsapp_delay = get_setting("browser.whatsapp_load_delay_seconds", 8)
        gmail_delay = get_setting("browser.gmail_load_delay_seconds", 8)
        reminder_monitor = get_setting("notifications.reminder_monitor_enabled", True)
        reminder_interval = get_setting("notifications.reminder_check_interval_minutes", 15)
        event_monitor = get_setting("notifications.event_monitor_enabled", True)
        event_interval = get_setting("notifications.event_check_interval_minutes", 15)
        popup_timeout = get_setting("notifications.popup_timeout_seconds", 10)
        popup_cooldown = get_setting("notifications.popup_cooldown_seconds", 180)
        return (
            f"Current settings: wake word is {wake_word}. "
            f"Voice mode is {voice_mode}. "
            f"Persona mode is {persona_mode}. "
            f"Initial timeout is {initial_timeout} seconds. "
            f"Active timeout is {active_timeout} seconds. "
            f"Post wake pause is {post_wake_pause} seconds. "
            f"Empty listen backoff is {empty_backoff} seconds. "
            f"Wake listen timeout is {wake_listen_timeout} seconds. "
            f"Wake phrase time limit is {wake_phrase_limit} seconds. "
            f"Wake match threshold is {wake_match_threshold}. "
            f"Wake retry window is {wake_retry_window} seconds. "
            f"Browser load delay is {browser_delay} seconds. "
            f"WhatsApp load delay is {whatsapp_delay} seconds. "
            f"Gmail load delay is {gmail_delay} seconds. "
            f"Tray startup is {'on' if tray_mode else 'off'}. "
            f"Reminder monitor is {'on' if reminder_monitor else 'off'}. "
            f"Reminder interval is {reminder_interval} minutes. "
            f"Event monitor is {'on' if event_monitor else 'off'}. "
            f"Event interval is {event_interval} minutes. "
            f"Popup timeout is {popup_timeout} seconds. "
            f"Popup cooldown is {popup_cooldown} seconds. "
            f"Sounds are {'on' if sounds_enabled else 'off'}. "
            f"Start sound is {'on' if start_sound else 'off'}. "
            f"Success sound is {'on' if success_sound else 'off'}. "
            f"Error sound is {'on' if error_sound else 'off'}."
        )

    if command in ["mute sounds", "turn off sounds", "disable sounds"]:
        update_setting("sounds.enabled", False)
        return "Assistant sounds turned off."

    if command in ["unmute sounds", "turn on sounds", "enable sounds"]:
        update_setting("sounds.enabled", True)
        return "Assistant sounds turned on."

    if command in ["turn off start sound", "disable start sound"]:
        update_setting("sounds.start", False)
        return "Start sound turned off."

    if command in ["turn on start sound", "enable start sound"]:
        update_setting("sounds.start", True)
        return "Start sound turned on."

    if command in ["turn off success sound", "disable success sound"]:
        update_setting("sounds.success", False)
        return "Success sound turned off."

    if command in ["turn on success sound", "enable success sound"]:
        update_setting("sounds.success", True)
        return "Success sound turned on."

    if command in ["turn off error sound", "disable error sound"]:
        update_setting("sounds.error", False)
        return "Error sound turned off."

    if command in ["turn on error sound", "enable error sound"]:
        update_setting("sounds.error", True)
        return "Error sound turned on."

    if command in ["enable tray startup", "turn on tray startup"]:
        update_setting("startup.tray_mode", True)
        return "Tray startup enabled."

    if command in ["disable tray startup", "turn off tray startup"]:
        update_setting("startup.tray_mode", False)
        return "Tray startup disabled."

    if command in ["friendly mode", "set persona to friendly", "change persona to friendly"]:
        update_setting("assistant.persona", "friendly")
        return "Persona mode changed to Friendly."

    if command in ["professional mode", "set persona to professional", "change persona to professional"]:
        update_setting("assistant.persona", "professional")
        return "Persona mode changed to Professional."

    if command in ["funny mode", "set persona to funny", "change persona to funny"]:
        update_setting("assistant.persona", "funny")
        return "Persona mode changed to Funny."

    if command in ["enable reminder monitor", "turn on reminder monitor", "enable notification monitor"]:
        update_setting("notifications.reminder_monitor_enabled", True)
        return "Reminder monitor enabled."

    if command in ["disable reminder monitor", "turn off reminder monitor", "disable notification monitor"]:
        update_setting("notifications.reminder_monitor_enabled", False)
        return "Reminder monitor disabled."

    if command in ["enable event monitor", "turn on event monitor", "enable calendar monitor"]:
        update_setting("notifications.event_monitor_enabled", True)
        return "Event monitor enabled."

    if command in ["disable event monitor", "turn off event monitor", "disable calendar monitor"]:
        update_setting("notifications.event_monitor_enabled", False)
        return "Event monitor disabled."

    interval_match = re.match(
        r"^(?:set|change|update)\s+reminder popup interval\s+to\s+(\d+)$", command
    )
    if interval_match:
        interval_value = max(1, int(interval_match.group(1)))
        update_setting("notifications.reminder_check_interval_minutes", interval_value)
        return f"Reminder popup interval updated to {interval_value} minutes."

    event_interval_match = re.match(
        r"^(?:set|change|update)\s+event popup interval\s+to\s+(\d+)$", command
    )
    if event_interval_match:
        interval_value = max(1, int(event_interval_match.group(1)))
        update_setting("notifications.event_check_interval_minutes", interval_value)
        return f"Event popup interval updated to {interval_value} minutes."

    if command in [
        "enable noise cancel mode",
        "turn on noise cancel mode",
        "set voice mode to noise cancel",
    ]:
        apply_voice_profile("noise_cancel")
        return "Voice mode changed to noise cancel. Restart the assistant for the cleanest result."

    if command in [
        "enable sensitive voice mode",
        "turn on sensitive voice mode",
        "set voice mode to sensitive",
        "soft voice mode",
    ]:
        apply_voice_profile("sensitive")
        return "Voice mode changed to sensitive. Soft voice detection should improve."

    if command in [
        "enable ultra sensitive voice mode",
        "turn on ultra sensitive voice mode",
        "set voice mode to ultra sensitive",
        "set voice mode to ultra_sensitive",
        "very soft voice mode",
    ]:
        apply_voice_profile("ultra_sensitive")
        return (
            "Voice mode changed to ultra sensitive. "
            "This should catch softer speech, but it may also react to room noise."
        )

    if command in [
        "set voice mode to normal",
        "enable normal voice mode",
        "turn on normal voice mode",
    ]:
        apply_voice_profile("normal")
        return "Voice mode changed to normal."

    return None


# ---------------- PROCESS COMMAND ----------------
def process_command(command, INSTALLED_APPS, input_mode="text"):
    global mouse_stop_event, mouse_stop_requested_by_command, pending_confirmation

    command = command.lower().strip()
    if command:
        log_command(command, source=input_mode)

    config_reply = _handle_config_command(command)
    if config_reply:
        speak(config_reply)
        return

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

    if command in [
        "read selected area",
        "scan selected area",
        "read selected region",
    ]:
        speak(
            "Move your mouse to the first corner now. I will capture the second corner in three seconds."
        )
        result = read_selected_area_text()

        if isinstance(result, dict):
            print("\n===== SELECTED AREA TEXT =====\n")
            print(result["text"])
            print("\n==============================\n")
            speak("Selected area content printed")
        else:
            speak(result)
        return

    if command.startswith("find in selected area "):
        target = command.replace("find in selected area", "", 1).strip()
        if not target:
            speak("Tell me what you want me to find in the selected area.")
            return

        speak(
            "Move your mouse to the first corner now. I will capture the second corner in three seconds."
        )
        region = capture_selected_region()
        if isinstance(region, dict) and region.get("cancelled"):
            speak("Selected area capture cancelled.")
            return
        if not region:
            speak("Selected area was too small. Try again.")
            return

        details = find_text_details_in_region(target, region)
        if details:
            x, y = details["center"]
            speak(f"I found {details['text']} in the selected area near position {x}, {y}.")
        else:
            speak(f"I could not find {target} in the selected area.")
        return

    if command.startswith("click in selected area "):
        target = command.replace("click in selected area", "", 1).strip()
        if not target:
            speak("Tell me what you want me to click in the selected area.")
            return

        speak(
            "Move your mouse to the first corner now. I will capture the second corner in three seconds."
        )
        region = capture_selected_region()
        if isinstance(region, dict) and region.get("cancelled"):
            speak("Selected area capture cancelled.")
            return
        if not region:
            speak("Selected area was too small. Try again.")
            return

        details = click_on_text_in_region(target, region)
        if details:
            speak(f"I clicked {details['text']} in the selected area.")
        else:
            speak(f"I could not find {target} in the selected area to click.")
        return

    named_region_commands = {
        "read top left area": "top left",
        "read top right area": "top right",
        "read bottom left area": "bottom left",
        "read bottom right area": "bottom right",
        "read center area": "center",
        "scan top left area": "top left",
        "scan top right area": "top right",
        "scan bottom left area": "bottom left",
        "scan bottom right area": "bottom right",
        "scan center area": "center",
    }
    if command in named_region_commands:
        region_name = named_region_commands[command]
        speak(f"Scanning the {region_name} area")
        text = read_named_screen_region(region_name)
        print(f"\n===== {region_name.upper()} AREA TEXT =====\n")
        print(text)
        print("\n========================\n")
        speak(f"{region_name} area content printed")
        return

    if "read screen" in command or "what is on screen" in command:
        speak("Scanning screen")

        text = read_screen_text()

        print("\n===== SCREEN TEXT =====\n")
        print(text)
        print("\n========================\n")

        speak("Screen content printed")
        return

    if command in [
        "start dictation",
        "start detection",
        "start typing mode",
        "voice typing mode",
    ]:
        start_dictation()
        speak("Dictation mode started. Speak your text, and say stop dictation to exit.")
        return

    if command in [
        "stop dictation",
        "stop detection",
        "stop typing mode",
        "exit dictation",
    ]:
        stop_dictation()
        speak("Dictation mode stopped.")
        return

    if command.startswith("find "):
        target = command.replace("find", "", 1).strip()
        if not target:
            speak("Tell me what you want me to find on the screen.")
            return

        details = find_text_details(target)
        if details:
            x, y = details["center"]
            speak(
                f"I found {details['text']} on the screen near position {x}, {y}."
            )
        else:
            speak(f"I could not find {target} on the screen.")
        return

    if command.startswith("click "):
        target = command.replace("click", "", 1).strip()
        if not target:
            speak("Tell me what you want me to click.")
            return

        found = click_on_text(target)
        if found:
            speak(f"I clicked {target}.")
        else:
            speak(f"I could not find {target} to click.")
        return

    if command.startswith("is ") and command.endswith(" visible"):
        target = command[3:-8].strip()
        if not target:
            speak("Tell me what you want me to check.")
            return

        if is_text_visible(target):
            speak(f"Yes, {target} is visible on the screen.")
        else:
            speak(f"No, I could not see {target} on the screen.")
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

    if command in ["background mode", "start background mode", "minimize to tray", "tray mode"]:
        success, message = start_tray()
        speak(message if message else "Tray mode updated.")
        return

    if command in ["exit tray mode", "stop background mode", "restore assistant", "open assistant window"]:
        stopped = stop_tray()
        if stopped:
            speak("Grandpa Assistant restored from the system tray.")
        else:
            speak("Tray mode is not active right now.")
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
        stream_output = input_mode == "text"
        if stream_output:
            start_streaming_reply()
        try:
            response = ask_ollama(
                f"The user is asking about {app_scan_module.LAST_TOPIC}. {command}",
                stream_callback=append_streaming_reply if stream_output else None,
            )
        finally:
            if stream_output:
                end_streaming_reply()
        speak(response, already_printed=stream_output)
        return

    # -------- GENERAL AI RESPONSE --------
    try:
        stream_output = input_mode == "text"
        if stream_output:
            start_streaming_reply()
        try:
            response = ask_ollama(
                command,
                stream_callback=append_streaming_reply if stream_output else None,
            )
        finally:
            if stream_output:
                end_streaming_reply()
        if response:
            speak(response, already_printed=stream_output)
        else:
            speak("I did not get a proper response.")

    except Exception as e:
        print("Error:", e)

        play_sound("error.wav")
        speak("Something went wrong")
