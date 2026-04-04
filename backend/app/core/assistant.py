import datetime
import os
import re
from difflib import SequenceMatcher
import sys
import threading
import time

from colorama import Fore, Style, init

from brain.database import get_recent_commands
from api.web_api import start_web_api
from core.command_router import process_command
from core.odin_ui import launch_odin_ui
from core.quick_overlay import (
    get_pinned_commands,
    hide_quick_overlay,
    register_overlay_hotkey,
    show_quick_overlay,
    unregister_overlay_hotkey,
)
from core.tray_manager import set_tray_exit_callback, set_tray_open_callbacks, start_tray, stop_tray
from modules.app_scan_module import get_all_apps
from modules.briefing_module import build_daily_brief, build_due_reminder_alert
from modules.dictation_module import handle_dictation_text, is_dictation_active, stop_dictation
from modules.event_module import get_event_data
from modules.notification_module import (
    run_startup_daily_automations,
    show_startup_brief_popup,
    show_startup_recap_popup,
    show_startup_status_popup,
    show_startup_agenda_popup,
    show_startup_health_popup,
    show_startup_weather_popup,
    show_startup_notifications,
    start_notification_monitor,
)
from modules.profile_module import build_proactive_nudge
from modules.messaging_automation_module import restore_scheduled_jobs
from modules.desktop_launch_module import launch_react_for_tray, open_react_browser_ui, open_react_desktop_ui
from modules.startup_module import refresh_startup_auto_launch
from modules.google_contacts_module import start_google_contacts_auto_refresh
from modules.task_module import get_task_data
from startup_diagnostics import collect_startup_diagnostics, format_startup_diagnostics_report
from utils.config import get_setting
from utils.sound import play_sound
from vision.hand_mouse_control import run_hand_mouse
from vision.screen_reader import register_region_hotkey, unregister_region_hotkey
from voice.listen import (
    continuous_conversation_enabled,
    follow_up_keep_alive_seconds,
    is_follow_up_keepalive_phrase,
    is_interrupt_phrase,
    is_wake_only_phrase,
    listen,
    sanitize_follow_up_command,
    should_run_direct_fallback,
    strip_wake_word as shared_strip_wake_word,
    wake_word_detected as shared_wake_word_detected,
)
from voice.speak import set_response_mode, speak, stop_speaking

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

try:
    from absl import logging
except ImportError:
    logging = None
else:
    logging.set_verbosity(logging.ERROR)

init(autoreset=True)

INSTALLED_APPS = {}
WAKE_WORD = get_setting("wake_word", "hey grandpa")
INITIAL_TIMEOUT = get_setting("initial_timeout", 15)
ACTIVE_TIMEOUT = get_setting("active_timeout", 60)
POST_WAKE_PAUSE = get_setting("voice.post_wake_pause_seconds", 0.35)
EMPTY_LISTEN_BACKOFF = get_setting("voice.empty_listen_backoff_seconds", 0.2)
WAKE_MATCH_THRESHOLD = get_setting("voice.wake_match_threshold", 0.68)
WAKE_RETRY_WINDOW = get_setting("voice.wake_retry_window_seconds", 6)

stop_event = threading.Event()
hand_mouse_thread = None
STATUS_LINE_WIDTH = 96


def _build_compact_startup_messages():
    data = get_task_data()
    pending_count = sum(1 for task in data.get("tasks", []) if not task.get("completed"))
    overdue_count = 0
    upcoming_count = 0
    now = datetime.datetime.now()
    today = now.date()
    time_of_day = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"

    for reminder in data.get("reminders", []):
        due_at = reminder.get("due_at")
        due_date = reminder.get("due_date")
        due_datetime = None
        if due_at:
            try:
                due_datetime = datetime.datetime.fromisoformat(due_at)
            except ValueError:
                due_datetime = None
        if due_datetime is None and due_date:
            try:
                due_datetime = datetime.datetime.combine(
                    datetime.date.fromisoformat(due_date),
                    datetime.time(hour=9, minute=0),
                )
            except ValueError:
                due_datetime = None
        if due_datetime is None:
            continue
        if due_datetime < now:
            overdue_count += 1
        elif due_datetime.date() == today:
            upcoming_count += 1

    summary = (
        f"Good {time_of_day}. "
        f"You have {pending_count} pending tasks, {overdue_count} overdue reminders, and {upcoming_count} reminders due today."
    )
    return [
        "Hello Grandchild!",
        summary,
    ]


def _overlay_suggestions():
    today = datetime.date.today()
    now = datetime.datetime.now()
    data = get_task_data()
    events = get_event_data().get("events", [])

    pending_task_count = sum(1 for task in data.get("tasks", []) if not task.get("completed"))
    due_today_count = 0
    overdue_count = 0

    for reminder in data.get("reminders", []):
        due_at = reminder.get("due_at")
        due_date = reminder.get("due_date")
        due_datetime = None

        if due_at:
            try:
                due_datetime = datetime.datetime.fromisoformat(due_at)
            except ValueError:
                due_datetime = None

        if due_datetime is None and due_date:
            try:
                due_datetime = datetime.datetime.combine(
                    datetime.date.fromisoformat(due_date),
                    datetime.time(hour=9, minute=0),
                )
            except ValueError:
                due_datetime = None

        if due_datetime is None:
            continue

        if due_datetime < now:
            overdue_count += 1
        elif due_datetime.date() == today:
            due_today_count += 1

    today_event_count = sum(1 for event in events if event.get("date") == today.isoformat())

    suggestions = {
        f"Planning ({today_event_count + due_today_count + overdue_count + pending_task_count})": [
            (f"Agenda Today ({today_event_count} events)", "today agenda"),
            (f"Due Today ({due_today_count})", "what is due today"),
            (f"Overdue ({overdue_count})", "show overdue items"),
            (f"Pending Tasks ({pending_task_count})", "latest task"),
            ("Latest Reminder", "latest reminder"),
        ],
        "Contacts (4)": [
            ("Call My Father", "call my father"),
            ("Copy Jeevan Phone", "copy jeevan phone"),
            ("Open My Portfolio", "open my portfolio"),
            ("Mail My Mother About Today Plan", "mail my mother about today plan"),
        ],
        "Browser (22)": [
            ("Open Result 2 In New Tab", "open result 2 in new tab"),
            ("Copy Selected Browser Text", "copy selected browser text"),
            ("Search Selected Text On Google", "search selected text on google"),
            ("Search Selected Text On YouTube", "search selected text on youtube"),
            ("Summarize Selected Text With AI", "summarize selected text with ai"),
            ("Explain Selected Text", "explain selected text"),
            ("Read Selected Text Aloud", "read selected text aloud"),
            ("Save Selected Text As Note", "save selected text as note"),
            ("Remind Me About Selected Text Tomorrow At 8 PM", "remind me about selected text tomorrow at 8 pm"),
            ("Search Selected Text And Summarize", "search selected text and summarize"),
            ("Summarize Selected Text And Save Note", "summarize selected text and save note"),
            ("Explain Selected Text And Save Note", "explain selected text and save note"),
            ("Summarize Selected Text And Read Aloud", "summarize selected text and read aloud"),
            ("Search Selected Text And Read Summary", "search selected text and read summary"),
            ("Save Selected Text As Task", "save selected text as task"),
            ("Create Event From Selected Text Tomorrow At 6 PM", "create event from selected text tomorrow at 6 pm"),
            ("Send Selected Text To Jeevan", "send selected text to jeevan"),
            ("Mail Selected Text To My Mother", "mail selected text to my mother"),
            ("Translate Selected Text To Tamil", "translate selected text to tamil"),
            ("Extract Action Items From Selected Text", "extract action items from selected text"),
            ("Save Action Items From Selected Text", "extract action items from selected text and save note"),
            ("Translate Selected Text To English", "translate selected text to english"),
        ],
        "System (5)": [
            ("Weather", "weather"),
            ("Dashboard", "dashboard"),
            ("Show Settings", "show settings"),
            ("System Status", "system status"),
            ("Export Summary", "export productivity summary"),
        ],
        "Actions (8)": [
            ("Complete Latest Task", "complete latest task"),
            ("Latest Event", "latest event"),
            ("Delete Latest Event", "delete latest event"),
            ("Upcoming Events", "upcoming events"),
            ("Show Weather Popup", "show weather popup"),
            ("Run Morning Routine", "run morning routine"),
            ("Run Night Routine", "run night routine"),
            ("Message And Remind My Father", "message and remind my father"),
        ],
        "OCR (2)": [
            ("Copy Selected Area Text", "copy selected area text"),
            ("Read Selected Area", "read selected area"),
        ],
    }
    pinned = get_pinned_commands()
    if pinned:
        suggestions = {
            f"Pinned ({len(pinned)})": [(item.title(), item) for item in pinned],
            **suggestions,
        }
    return suggestions


def _overlay_context_items():
    data = get_task_data()
    today = datetime.date.today()
    events = list(get_event_data().get("events", []))

    pending_tasks = [task for task in data.get("tasks", []) if not task.get("completed")]
    pending_tasks.sort(key=lambda task: task.get("created_at", ""), reverse=True)

    reminders = list(data.get("reminders", []))
    reminders.sort(key=lambda reminder: reminder.get("created_at", ""), reverse=True)

    today_events = [event for event in events if event.get("date") == today.isoformat()]
    upcoming_events = []
    for event in events:
        event_date = event.get("date")
        if not event_date:
            continue
        try:
            parsed_date = datetime.date.fromisoformat(event_date)
        except ValueError:
            continue
        if parsed_date >= today:
            upcoming_events.append(event)

    upcoming_events.sort(key=lambda event: (event.get("date") or "9999-12-31", event.get("time") or "23:59"))

    context_items = []

    if pending_tasks:
        latest_task_title = pending_tasks[0].get("title", "Untitled task")
        context_items.append((f"Latest Task: {latest_task_title}", "latest task"))
        context_items.append(("Complete Latest Task", "complete latest task"))
    else:
        context_items.append(("No Pending Tasks", "show tasks"))

    if reminders:
        latest_reminder_title = reminders[0].get("title", "Untitled reminder")
        context_items.append((f"Latest Reminder: {latest_reminder_title}", "latest reminder"))
        context_items.append(("What Is Due Today", "what is due today"))
        context_items.append(("Run Morning Routine", "run morning routine"))
    else:
        context_items.append(("No Active Reminders", "show reminders"))

    if today_events:
        first_today_event = today_events[0].get("title", "Untitled event")
        context_items.append((f"Today's Event: {first_today_event}", "today events"))
    else:
        context_items.append(("No Events Today", "today events"))

    if upcoming_events:
        next_event = upcoming_events[0]
        next_event_title = next_event.get("title", "Untitled event")
        context_items.append((f"Next Event: {next_event_title}", "upcoming events"))
        context_items.append(("Delete Latest Event", "delete latest event"))
        context_items.append(("Run Night Routine", "run night routine"))
    else:
        context_items.append(("No Upcoming Events", "upcoming events"))

    return context_items


def exit_assistant():
    hide_quick_overlay()
    unregister_overlay_hotkey()
    unregister_region_hotkey()
    stop_tray()
    stop_event.set()
    os._exit(0)


def _handle_ocr_hotkey_result(result):
    if not result:
        return

    if result.get("error"):
        message = result["error"]
        print(f"\nOCR Hotkey: {message}")
        speak(message)
        return

    text = result.get("text", "Readable text was not clearly detected on the screen.")
    print("\n===== OCR HOTKEY AREA TEXT =====\n")
    print(text)
    print("\n================================\n")
    speak("OCR hotkey area content printed")


def _handle_overlay_command(command_text):
    print(f"\nOverlay command: {command_text}")
    process_command(command_text.lower().strip(), INSTALLED_APPS, input_mode="text")
    play_sound("success")


def _open_overlay():
    recent_commands = get_recent_commands()
    return show_quick_overlay(
        _handle_overlay_command,
        suggestions=_overlay_suggestions(),
        recent_commands=recent_commands,
        recent_actions=recent_commands[:4],
        context_items=_overlay_context_items(),
    )


def glowing_cursor():
    while True:
        sys.stdout.write("\rUser: *")
        sys.stdout.flush()
        time.sleep(0.5)
        sys.stdout.write("\rUser:  ")
        sys.stdout.flush()
        time.sleep(0.5)


def _clear_status_line(newline=False):
    sys.stdout.write("\r" + " " * STATUS_LINE_WIDTH + "\r")
    if newline:
        sys.stdout.write("\n")
    sys.stdout.flush()


def _wait_for_thread(thread, poll_interval=0.1):
    while thread.is_alive():
        thread.join(timeout=poll_interval)


def _normalize_phrase(text):
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


def _wake_word_detected(command, wake_word):
    return shared_wake_word_detected(command, wake_word)


def _strip_wake_word(command, wake_word):
    return shared_strip_wake_word(command, wake_word)


def _looks_like_direct_command(command):
    direct_prefixes = [
        "what ",
        "who ",
        "tell me ",
        "open ",
        "close ",
        "read ",
        "find ",
        "click ",
        "weather",
        "forecast",
        "dashboard",
        "status ",
        "show ",
        "list ",
        "add ",
        "delete ",
        "start ",
        "stop ",
        "take ",
        "summarize ",
        "background mode",
        "mute ",
        "unmute ",
        "enable ",
        "disable ",
        "set ",
        "update ",
    ]
    return any(command.startswith(prefix) for prefix in direct_prefixes)


def _detect_runtime_mode_switch(command, current_mode):
    normalized = _normalize_phrase(command)
    if not normalized:
        return None

    to_voice = {
        "switch to voice mode",
        "change to voice mode",
        "go to voice mode",
        "voice input mode",
    }
    to_text = {
        "switch to text mode",
        "change to text mode",
        "go to text mode",
        "text input mode",
    }
    to_ui = {
        "switch to ui mode",
        "change to ui mode",
        "go to ui mode",
    }
    to_menu = {
        "change mode",
        "switch mode",
        "mode menu",
        "mode selection",
        "back to mode selection",
        "back to mode menu",
        "choose mode",
        "input mode menu",
    }

    if normalized in to_menu:
        return "menu"
    if current_mode != "voice" and normalized in to_voice:
        return "voice"
    if current_mode != "text" and normalized in to_text:
        return "text"
    if current_mode != "ui" and normalized in to_ui:
        return "ui"
    return None


def _prompt_for_input_mode():
    mode_map = {
        "1": "voice",
        "2": "text",
        "3": "ui",
    }

    while True:
        try:
            print("\nChoose to enter input mode (1 - Voice / 2 - Text / 3 - UI): ", end="")
            selected = input().strip()
        except KeyboardInterrupt:
            print("\nExiting Grandpa Assistant...")
            speak("Goodbye Captain!")
            stop_event.set()
            return None

        mode = mode_map.get(selected)
        if mode:
            return mode

        print("Invalid mode selected.")
        play_sound("error")
        speak("Invalid mode selected.")


def _run_selected_mode_loop(start_mode):
    mode = start_mode

    while True:
        if mode == "menu":
            mode = _prompt_for_input_mode()
            if not mode:
                return
            continue

        if mode == "voice":
            set_response_mode("voice")
            play_sound("start")
            next_mode = voice_mode()
        elif mode == "text":
            set_response_mode("text")
            play_sound("start")
            speak("Text mode activated.")
            print()
            next_mode = text_mode()
        elif mode == "ui":
            set_response_mode("text")
            play_sound("start")
            speak("UI activated.")
            launch_odin_ui(INSTALLED_APPS)
            return
        else:
            mode = "menu"
            continue

        if next_mode in {"voice", "text", "ui", "menu"}:
            mode = next_mode
            continue
        return


def _process_voice_command(command, current_timeout):
    mode_switch = _detect_runtime_mode_switch(command, current_mode="voice")
    if mode_switch:
        if mode_switch == "menu":
            speak("Opening mode selection.")
        elif mode_switch == "text":
            speak("Switching to text mode.")
        elif mode_switch == "ui":
            speak("Switching to UI mode.")
        else:
            speak("Voice mode already active.")
        return {"exit": False, "timeout": ACTIVE_TIMEOUT, "switch_mode": mode_switch}

    if command == "exit assistant":
        stop_dictation()
        speak("Goodbye Captain!")
        return {"exit": True, "timeout": current_timeout}

    _clear_status_line(newline=True)
    print(f"User: {command}")

    if command == "stop speaking":
        stop_speaking()
        return {"exit": False, "timeout": current_timeout}

    if is_dictation_active():
        if command in [
            "stop dictation",
            "stop detection",
            "stop typing mode",
            "exit dictation",
        ]:
            stop_dictation()
            speak("Dictation mode stopped.")
            return {"exit": False, "timeout": ACTIVE_TIMEOUT}

        typed = handle_dictation_text(command)
        if typed:
            play_sound("success")
            return {"exit": False, "timeout": ACTIVE_TIMEOUT}

    process_command(command, INSTALLED_APPS, input_mode="voice")
    play_sound("success")
    print()
    return {"exit": False, "timeout": ACTIVE_TIMEOUT}


def main(start_in_tray=False, start_in_ui=False, forced_input_mode=None):
    global INSTALLED_APPS
    global WAKE_WORD, INITIAL_TIMEOUT, ACTIVE_TIMEOUT, POST_WAKE_PAUSE, EMPTY_LISTEN_BACKOFF
    global WAKE_MATCH_THRESHOLD, WAKE_RETRY_WINDOW

    set_tray_exit_callback(exit_assistant)
    set_tray_open_callbacks(
        open_react_browser=lambda: open_react_browser_ui(),
        open_react_desktop=lambda: open_react_desktop_ui(),
    )
    WAKE_WORD = get_setting("wake_word", "hey grandpa")
    INITIAL_TIMEOUT = get_setting("initial_timeout", 15)
    ACTIVE_TIMEOUT = get_setting("active_timeout", 60)
    POST_WAKE_PAUSE = get_setting("voice.post_wake_pause_seconds", 0.35)
    EMPTY_LISTEN_BACKOFF = get_setting("voice.empty_listen_backoff_seconds", 0.2)
    WAKE_MATCH_THRESHOLD = get_setting("voice.wake_match_threshold", 0.68)
    WAKE_RETRY_WINDOW = get_setting("voice.wake_retry_window_seconds", 6)
    interface_mode = str(get_setting("startup.interface_mode", "terminal") or "terminal").strip().lower()
    if interface_mode not in {"terminal", "ui"}:
        interface_mode = "terminal"
    terminal_input_mode = str(get_setting("startup.terminal_input_mode", "text") or "text").strip().lower()
    if terminal_input_mode not in {"voice", "text"}:
        terminal_input_mode = "text"
    terminal_only_mode = interface_mode == "terminal" and not start_in_ui
    show_startup_doctor = get_setting("startup.print_diagnostics_on_boot", True)
    show_ready_checks = get_setting("startup.print_ready_diagnostics_on_boot", False)

    INSTALLED_APPS = get_all_apps(refresh=True)
    startup_diagnostics = collect_startup_diagnostics(use_cache=False, allow_create_dirs=True)
    start_web_api(INSTALLED_APPS)
    refresh_startup_auto_launch()

    if show_startup_doctor:
        print("\n========= STARTUP DOCTOR =========")
        for line in format_startup_diagnostics_report(
            startup_diagnostics,
            include_ready=show_ready_checks,
        ):
            print(line)
        print("==================================\n")

    startup_messages = _build_compact_startup_messages()
    urgent_alert = build_due_reminder_alert()
    if urgent_alert != "No urgent reminders right now.":
        startup_messages.append(urgent_alert)

    if start_in_ui:
        show_startup_notifications()
        show_startup_brief_popup()
        show_startup_agenda_popup()
        show_startup_health_popup()
        show_startup_weather_popup()
        show_startup_status_popup()
        show_startup_recap_popup()
        run_startup_daily_automations()
        start_notification_monitor()
        restore_scheduled_jobs()
        if get_setting("google_contacts.auto_refresh_enabled", True):
            start_google_contacts_auto_refresh(get_setting("google_contacts.auto_refresh_hours", 24))
        if get_setting("ocr.region_hotkey_enabled", True):
            register_region_hotkey(
                _handle_ocr_hotkey_result,
                get_setting("ocr.region_hotkey", "ctrl+shift+o"),
            )
        if get_setting("overlay.hotkey_enabled", True):
            register_overlay_hotkey(
                _handle_overlay_command,
                get_setting("overlay.hotkey", "ctrl+shift+space"),
                suggestions_provider=_overlay_suggestions,
                recent_provider=get_recent_commands,
                recent_actions_provider=lambda: get_recent_commands(limit=4),
                context_provider=_overlay_context_items,
            )
        set_response_mode("text")
        launch_odin_ui(INSTALLED_APPS, startup_messages=startup_messages)
        return

    if get_setting("startup.show_installed_apps_on_boot", False):
        print("\n========= INSTALLED APPLICATIONS =========")
        print("Total apps found:", len(INSTALLED_APPS))

    for startup_message in startup_messages:
        speak(startup_message)
    if not terminal_only_mode:
        show_startup_notifications()
        show_startup_brief_popup()
        show_startup_agenda_popup()
        show_startup_health_popup()
        show_startup_weather_popup()
        show_startup_status_popup()
        show_startup_recap_popup()
    run_startup_daily_automations()
    if not terminal_only_mode:
        start_notification_monitor()
    restore_scheduled_jobs()
    if get_setting("google_contacts.auto_refresh_enabled", True):
        start_google_contacts_auto_refresh(get_setting("google_contacts.auto_refresh_hours", 24))
    if not terminal_only_mode and get_setting("ocr.region_hotkey_enabled", True):
        register_region_hotkey(
            _handle_ocr_hotkey_result,
            get_setting("ocr.region_hotkey", "ctrl+shift+o"),
        )
    if not terminal_only_mode and get_setting("overlay.hotkey_enabled", True):
        register_overlay_hotkey(
            _handle_overlay_command,
            get_setting("overlay.hotkey", "ctrl+shift+space"),
            suggestions_provider=_overlay_suggestions,
            recent_provider=get_recent_commands,
            recent_actions_provider=lambda: get_recent_commands(limit=4),
            context_provider=_overlay_context_items,
        )
    play_sound("start")

    if get_setting("startup.tray_mode", False):
        start_in_tray = True

    if start_in_tray:
        success, message = start_tray(on_quit=exit_assistant)
        if message:
            print(message)
        if success:
            launch_react_for_tray()
            set_response_mode("voice")
            speak("Background tray mode activated.")
            voice_mode()
            return

    selected_mode = str(forced_input_mode or "").strip().lower()
    if selected_mode not in {"voice", "text"}:
        selected_mode = "menu"
    _run_selected_mode_loop(selected_mode)


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
    wake_retry_until = 0
    last_processed_command = ""
    last_processed_at = 0.0
    last_wake_ack_at = 0.0

    def _is_duplicate_recent(command):
        normalized = _normalize_phrase(command)
        if not normalized or not last_processed_command or not last_processed_at:
            return False
        try:
            window_seconds = max(0.5, float(get_setting("voice.duplicate_command_window_seconds", 4.0) or 4.0))
        except Exception:
            window_seconds = 4.0
        return normalized == last_processed_command and (time.time() - last_processed_at) <= window_seconds

    def _mark_processed(command):
        nonlocal last_processed_command, last_processed_at
        last_processed_command = _normalize_phrase(command)
        last_processed_at = time.time()

    def _should_ack_wake():
        nonlocal last_wake_ack_at
        try:
            cooldown = max(0.0, float(get_setting("voice.wake_ack_cooldown_seconds", 2.5) or 2.5))
        except Exception:
            cooldown = 2.5
        now = time.time()
        if cooldown and last_wake_ack_at and (now - last_wake_ack_at) < cooldown:
            return False
        last_wake_ack_at = now
        return True

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
                    _clear_status_line()

                anim_thread = threading.Thread(target=animate_wait, daemon=True)
                anim_thread.start()

                try:
                    command = listen(for_wake_word=True)
                    if not command:
                        time.sleep(EMPTY_LISTEN_BACKOFF)
                        continue
                finally:
                    stop_flag["stop"] = True
                    _wait_for_thread(anim_thread)

                command = command.lower().strip()

                if is_interrupt_phrase(command):
                    stop_speaking()
                    active_mode = True
                    last_active_time = time.time()
                    current_timeout = ACTIVE_TIMEOUT
                    continue

                if _wake_word_detected(command, WAKE_WORD):
                    trailing_command = _strip_wake_word(command, WAKE_WORD)
                    play_sound("start")
                    wake_retry_until = time.time() + WAKE_RETRY_WINDOW
                    if trailing_command and not is_wake_only_phrase(command, WAKE_WORD):
                        if _is_duplicate_recent(trailing_command):
                            continue
                        last_active_time = time.time()
                        _mark_processed(trailing_command)
                        result = _process_voice_command(trailing_command, ACTIVE_TIMEOUT)
                        if result["exit"]:
                            return None
                        next_mode = result.get("switch_mode")
                        if next_mode:
                            return next_mode
                        if continuous_conversation_enabled():
                            active_mode = True
                            current_timeout = result["timeout"]
                        else:
                            active_mode = False
                            current_timeout = INITIAL_TIMEOUT
                    else:
                        _clear_status_line(newline=True)
                        if _should_ack_wake():
                            speak("Yes Captain?")
                        time.sleep(POST_WAKE_PAUSE)
                        active_mode = True
                        last_active_time = time.time()
                        current_timeout = INITIAL_TIMEOUT

                elif wake_retry_until and time.time() <= wake_retry_until and should_run_direct_fallback(command):
                    if _is_duplicate_recent(command):
                        continue
                    play_sound("start")
                    last_active_time = time.time()
                    _mark_processed(command)
                    result = _process_voice_command(command, ACTIVE_TIMEOUT)
                    if result["exit"]:
                        return None
                    next_mode = result.get("switch_mode")
                    if next_mode:
                        return next_mode
                    if continuous_conversation_enabled():
                        active_mode = True
                        current_timeout = result["timeout"]
                    else:
                        active_mode = False
                        current_timeout = INITIAL_TIMEOUT

                elif should_run_direct_fallback(command):
                    # Practical fallback when wake word recognition is weak.
                    if _is_duplicate_recent(command):
                        continue
                    play_sound("start")
                    last_active_time = time.time()
                    _mark_processed(command)
                    result = _process_voice_command(command, ACTIVE_TIMEOUT)
                    if result["exit"]:
                        return None
                    next_mode = result.get("switch_mode")
                    if next_mode:
                        return next_mode
                    if continuous_conversation_enabled():
                        active_mode = True
                        current_timeout = result["timeout"]
                    else:
                        active_mode = False
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
                command_container["cmd"] = listen(for_follow_up=True)
                stop_flag["stop"] = True

            timer_thread = threading.Thread(target=countdown_timer, daemon=True)
            listen_thread = threading.Thread(target=listen_command, daemon=True)

            timer_thread.start()
            listen_thread.start()

            _wait_for_thread(listen_thread)
            stop_flag["stop"] = True
            _wait_for_thread(timer_thread)

            command = command_container["cmd"]

            if not is_dictation_active() and time.time() - last_active_time > current_timeout:
                active_mode = False
                _clear_status_line()
                print("Going back to sleep mode...\n")
                continue

            if not command:
                time.sleep(EMPTY_LISTEN_BACKOFF)
                continue

            command = sanitize_follow_up_command(command)
            if not command:
                time.sleep(EMPTY_LISTEN_BACKOFF)
                continue
            if is_follow_up_keepalive_phrase(command):
                last_active_time = time.time()
                current_timeout = max(current_timeout, follow_up_keep_alive_seconds())
                continue
            if is_interrupt_phrase(command):
                stop_speaking()
                last_active_time = time.time()
                current_timeout = ACTIVE_TIMEOUT
                continue
            if _is_duplicate_recent(command):
                last_active_time = time.time()
                current_timeout = ACTIVE_TIMEOUT
                continue
            last_active_time = time.time()
            _mark_processed(command)

            result = _process_voice_command(command, current_timeout)
            if continuous_conversation_enabled():
                current_timeout = result["timeout"]
            else:
                active_mode = False
                current_timeout = INITIAL_TIMEOUT
            if result["exit"]:
                return None
            next_mode = result.get("switch_mode")
            if next_mode:
                return next_mode

    except KeyboardInterrupt:
        print()
        stop_dictation()
        stop_tray()
        speak("Goodbye Captain!")
        return None


def text_mode():
    while True:
        try:
            print(Fore.CYAN + "User: " + Style.RESET_ALL, end="", flush=True)
            command = input().strip().lower()

            if not command:
                continue

            mode_switch = _detect_runtime_mode_switch(command, current_mode="text")
            if mode_switch:
                if mode_switch == "menu":
                    speak("Opening mode selection.")
                elif mode_switch == "voice":
                    speak("Switching to voice mode.")
                elif mode_switch == "ui":
                    speak("Switching to UI mode.")
                else:
                    speak("Text mode already active.")
                    print()
                    continue
                return mode_switch

            if command in ["exit", "quit"]:
                speak("Goodbye Captain!")
                stop_dictation()
                stop_tray()
                return None

            process_command(command, INSTALLED_APPS, input_mode="text")
            play_sound("success")
            print()

        except KeyboardInterrupt:
            print()
            speak("Goodbye Captain!")
            stop_dictation()
            stop_tray()
            return None
