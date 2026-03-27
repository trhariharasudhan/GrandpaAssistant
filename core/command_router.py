import datetime
import os
import re
import subprocess
import threading
import time
import webbrowser

import keyboard
from brain.ai_engine import ask_ollama, clear_memory
from brain.database import get_recent_commands, log_command
from core.followup_memory import get_best_followup_text, set_last_result
from brain.memory_engine import (
    get_memory,
    get_named_contact_field,
    get_portal_link,
    remove_named_contact_field,
    remove_memory_field,
    search_memory,
    set_memory,
    update_named_contact_field,
    update_memory_field,
)
import pyperclip
from brain.question_analyzer import is_personal_question
from core.intent_router import try_handle_intent
from core.quick_overlay import (
    get_pinned_commands,
    hide_quick_overlay,
    is_quick_overlay_open,
    list_pinned_commands,
    move_pinned_command,
    pin_overlay_command,
    show_quick_overlay,
    unpin_overlay_command,
)
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
from modules.notes_module import add_note
from modules.task_module import add_reminder
from modules.google_contacts_module import (
    import_google_contact_to_memory,
    list_contact_aliases,
    list_google_contacts,
    merge_google_contacts_into_memory,
    remove_contact_alias,
    set_contact_alias,
    sync_google_contacts,
)
from modules.messaging_automation_module import quick_email_shortcut, quick_whatsapp_message
from controls.brightness_control import handle_brightness
from controls.volume_control import handle_volume, set_volume_percentage
from utils.sound import play_sound
from utils.config import APP_ALIASES, get_setting, update_setting
from vision.hand_mouse_control import run_hand_mouse
from vision.screen_reader import (
    capture_selected_region,
    click_on_text,
    click_on_text_in_region,
    copy_named_screen_region_text,
    copy_screen_text,
    copy_selected_area_text,
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


def _try_auto_confirm_phone_call():
    def worker():
        try:
            time.sleep(2.0)
            for _ in range(3):
                keyboard.press_and_release("enter")
                time.sleep(0.7)
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()


def _normalize_voice_friendly_command(command):
    normalized = " ".join((command or "").lower().strip().split())
    if not normalized:
        return normalized

    normalized = normalized.replace("whats app", "whatsapp")
    normalized = normalized.replace("google mail", "gmail")

    exact_aliases = {
        "what are my settings": "show settings",
        "show me settings": "show settings",
        "open settings": "show settings",
        "what's due today": "what is due today",
        "show due today": "what is due today",
        "what's overdue": "show overdue items",
        "open overlay": "open quick overlay",
        "show overlay": "open quick overlay",
        "close overlay": "hide quick overlay",
        "hide overlay": "hide quick overlay",
        "open quick command": "open quick overlay",
        "close quick command": "hide quick overlay",
        "start morning routine": "run morning routine",
        "start night routine": "run night routine",
        "sync contacts": "sync google contacts",
        "refresh contacts": "refresh google contacts",
        "list contacts": "list google contacts",
        "merge contacts to memory": "merge google contacts to memory",
        "import contacts to memory": "merge google contacts to memory",
        "read this selected text": "read selected text aloud",
        "read selected text": "read selected text aloud",
        "translate this selected text to tamil": "translate selected text to tamil",
        "translate this selected text to english": "translate selected text to english",
        "extract action items": "extract action items from selected text",
        "save that as note": "save it as note",
        "save this as note": "save it as note",
        "make that a reminder": "make it a reminder",
        "send that to my father": "send it to my father",
        "mail that to my mother": "mail it to my mother",
    }
    if normalized in exact_aliases:
        return exact_aliases[normalized]

    prefix_aliases = [
        ("show me ", ""),
        ("open up ", "open "),
        ("call to ", "call "),
        ("text ", "message "),
        ("message to ", "message "),
        ("mail to ", "mail "),
        ("email to ", "mail "),
        ("send message to ", "message "),
        ("send whatsapp to ", "message "),
        ("send whatsapp message to ", "send whatsapp message to "),
    ]
    for prefix, replacement in prefix_aliases:
        if normalized.startswith(prefix):
            normalized = replacement + normalized[len(prefix):]

    normalized = re.sub(r"^what(?:'s| is)\s+the\s+time(?:\s+now)?$", "what is the time now", normalized)
    normalized = re.sub(r"^what(?:'s| is)\s+the\s+date$", "what is the date", normalized)
    normalized = re.sub(r"^what(?:'s| is)\s+my\s+agenda$", "today agenda", normalized)
    normalized = re.sub(r"^show\s+me\s+my\s+agenda$", "today agenda", normalized)

    return normalized


def _handle_memory_edit_command(command):
    named_contact_remove = re.match(
        r"^(?:remove|delete|clear)\s+(.+?)\s+(email|mail|phone|mobile|number|whatsapp)$",
        command,
    )
    if named_contact_remove:
        contact_name = named_contact_remove.group(1).strip()
        field_name = named_contact_remove.group(2).strip()
        if _normalize_contact_target(contact_name):
            return remove_named_contact_field(contact_name, field_name)[1]

    generic_named_contact_update = re.match(
        r"^(?:set|update|change)\s+(.+?)\s+(email|mail|phone|mobile|number|whatsapp)\s+to\s+(.+)$",
        command,
    )
    if generic_named_contact_update:
        contact_name = generic_named_contact_update.group(1).strip()
        field_name = generic_named_contact_update.group(2).strip()
        raw_value = generic_named_contact_update.group(3).strip()
        if _normalize_contact_target(contact_name):
            return update_named_contact_field(contact_name, field_name, raw_value)[1]

    named_contact_update = re.match(
        r"^(?:set|update|change)\s+contact\s+(.+?)\s+(email|mail|phone|mobile|number|whatsapp)\s+to\s+(.+)$",
        command,
    )
    if named_contact_update:
        contact_name = named_contact_update.group(1).strip()
        field_name = named_contact_update.group(2).strip()
        raw_value = named_contact_update.group(3).strip()
        return update_named_contact_field(contact_name, field_name, raw_value)[1]

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


def _normalize_contact_target(contact_name):
    normalized = " ".join(contact_name.lower().split())
    return normalized not in {"my", "me", "mine"}


def _copy_to_clipboard(value):
    try:
        pyperclip.copy(value)
        return True
    except Exception:
        return False


def _handle_followup_command(command):
    context_text = get_best_followup_text()
    if not context_text:
        return None

    if command in ["save it as note", "save that as note", "make it a note"]:
        return add_note(f"add note {context_text[:1200]}")

    if command in ["save it as task", "make it a task"]:
        from modules.task_module import add_task

        cleaned = " ".join(context_text.split())
        if len(cleaned) > 180:
            cleaned = cleaned[:180].rsplit(" ", 1)[0] + " ..."
        return add_task(f"add task review {cleaned}")

    reminder_match = re.match(
        r"^(?:make|set)\s+it\s+(?:a\s+)?reminder(?:\s+for\s+(.+))?$",
        command,
    )
    if reminder_match:
        schedule = (reminder_match.group(1) or "").strip()
        cleaned = " ".join(context_text.split())
        if len(cleaned) > 140:
            cleaned = cleaned[:140].rsplit(" ", 1)[0] + " ..."
        reminder_command = f"remind me to review {cleaned}"
        if schedule:
            reminder_command = f"{reminder_command} {schedule}"
        return add_reminder(reminder_command)

    send_match = re.match(r"^(?:send|message)\s+it\s+to\s+(.+)$", command)
    if send_match:
        target = send_match.group(1).strip()
        cleaned = " ".join(context_text.split())
        return quick_whatsapp_message(f"message {target} saying {cleaned[:900]}")

    mail_match = re.match(r"^(?:mail|email)\s+it\s+to\s+(.+)$", command)
    if mail_match:
        target = mail_match.group(1).strip()
        cleaned = " ".join(context_text.split())
        return quick_email_shortcut(f"mail {target} {cleaned[:900]}")

    translate_match = re.match(r"^translate\s+it\s+to\s+(.+)$", command)
    if translate_match:
        target_language = " ".join(translate_match.group(1).split()).title()
        reply = ask_ollama(
            f"Translate this text into {target_language}.\n\nText:\n{context_text[:4000]}",
            compact=False,
        )
        return f"Translated to {target_language}: {reply}"

    if command in ["extract action items from it", "extract tasks from it"]:
        reply = ask_ollama(
            "Extract the action items from this text in plain short lines.\n\n"
            f"Text:\n{context_text[:4000]}",
            compact=False,
        )
        return f"Action items: {reply}"

    return None


def _handle_contact_action_command(command):
    copy_match = re.match(r"^copy\s+(.+?)\s+(phone|number|email|mail)$", command)
    if copy_match:
        target = copy_match.group(1).strip()
        field = copy_match.group(2).strip()
        value, reply = get_named_contact_field(target, field)
        if not value:
            return reply
        if _copy_to_clipboard(str(value)):
            return f"{reply} I copied it to the clipboard."
        return reply

    call_match = re.match(r"^call\s+(.+)$", command)
    if call_match:
        target = call_match.group(1).strip()
        value, reply = get_named_contact_field(target, "phone")
        if not value:
            return reply
        copied = _copy_to_clipboard(str(value))
        try:
            webbrowser.open(f"tel:{value}")
            _try_auto_confirm_phone_call()
            return (
                f"{reply} I opened the dial action and also tried to auto-confirm the call."
                + (" I copied the number to the clipboard too." if copied else "")
            )
        except Exception:
            if copied:
                return f"{reply} I copied the number to the clipboard so you can call now."
            return reply

    if command in ["open my portfolio", "open portfolio", "open my github", "open github", "open my linkedin", "open linkedin"]:
        url = get_portal_link(command.replace("open ", "", 1))
        if not url:
            return "I could not find that saved link in memory."
        try:
            webbrowser.open(url, new=2)
            return f"Opening {url}."
        except Exception:
            return "I could not open that saved link right now."

    return None


def _handle_contact_lookup_command(command):
    if command in [
        "sync google contacts",
        "refresh google contacts",
        "sync my google contacts",
        "refresh my google contacts",
    ]:
        return sync_google_contacts()[1]

    if command in ["list google contacts", "show google contacts", "show synced contacts"]:
        return list_google_contacts()

    if command in [
        "merge google contacts to memory",
        "merge contacts to memory",
        "import google contacts to memory",
    ]:
        return merge_google_contacts_into_memory()[1]

    import_contact_match = re.match(
        r"^(?:merge|import)\s+google contact\s+(.+?)\s+to\s+memory$",
        command,
    )
    if import_contact_match:
        return import_google_contact_to_memory(import_contact_match.group(1).strip())[1]

    if command in ["list contact aliases", "show contact aliases"]:
        return list_contact_aliases()

    set_alias_match = re.match(
        r"^(?:set|save|remember)\s+contact alias\s+(.+?)\s+to\s+(.+)$",
        command,
    )
    if set_alias_match:
        return set_contact_alias(set_alias_match.group(1).strip(), set_alias_match.group(2).strip())[1]

    means_match = re.match(r"^(.+?)\s+means\s+(.+)$", command)
    if means_match:
        return set_contact_alias(means_match.group(1).strip(), means_match.group(2).strip())[1]

    remove_alias_match = re.match(
        r"^(?:remove|delete|clear)\s+contact alias\s+(.+)$",
        command,
    )
    if remove_alias_match:
        return remove_contact_alias(remove_alias_match.group(1).strip())[1]

    match = re.match(
        r"^what is\s+(.+?)\s+(email|mail|phone|mobile|number|whatsapp)$",
        command,
    )
    if not match:
        return None

    contact_name = match.group(1).strip()
    field_name = match.group(2).strip()
    _, reply = get_named_contact_field(contact_name, field_name)
    return reply


def _handle_config_command(command):
    if command in ["enable google contacts auto refresh", "enable contact auto refresh"]:
        update_setting("google_contacts.auto_refresh_enabled", True)
        return "Google Contacts auto refresh enabled."

    if command in ["disable google contacts auto refresh", "disable contact auto refresh"]:
        update_setting("google_contacts.auto_refresh_enabled", False)
        return "Google Contacts auto refresh disabled."

    google_refresh_match = re.match(
        r"^(?:set|change|update)\s+google contacts auto refresh(?: interval)?\s+to\s+(\d+)$",
        command,
    )
    if google_refresh_match:
        hours = max(1, int(google_refresh_match.group(1)))
        update_setting("google_contacts.auto_refresh_hours", hours)
        return f"Google Contacts auto refresh interval updated to {hours} hours."

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

    whatsapp_retry_count_match = re.match(
        r"^(?:set|change|update)\s+whatsapp retry count\s+to\s+(\d+)$", command
    )
    if whatsapp_retry_count_match:
        retry_value = max(1, int(whatsapp_retry_count_match.group(1)))
        update_setting("browser.whatsapp_search_retry_count", retry_value)
        return f"WhatsApp retry count updated to {retry_value}."

    whatsapp_retry_delay_match = re.match(
        r"^(?:set|change|update)\s+whatsapp retry delay\s+to\s+(\d+(?:\.\d+)?)$", command
    )
    if whatsapp_retry_delay_match:
        retry_delay = max(0.4, float(whatsapp_retry_delay_match.group(1)))
        update_setting("browser.whatsapp_search_retry_delay_seconds", retry_delay)
        return f"WhatsApp retry delay updated to {retry_delay} seconds."

    whatsapp_send_press_match = re.match(
        r"^(?:set|change|update)\s+whatsapp send press count\s+to\s+(\d+)$", command
    )
    if whatsapp_send_press_match:
        press_value = max(1, int(whatsapp_send_press_match.group(1)))
        update_setting("browser.whatsapp_send_press_count", press_value)
        return f"WhatsApp send press count updated to {press_value}."

    whatsapp_send_delay_match = re.match(
        r"^(?:set|change|update)\s+whatsapp send confirm delay\s+to\s+(\d+(?:\.\d+)?)$", command
    )
    if whatsapp_send_delay_match:
        delay_value = max(0.2, float(whatsapp_send_delay_match.group(1)))
        update_setting("browser.whatsapp_send_confirm_delay_seconds", delay_value)
        return f"WhatsApp send confirm delay updated to {delay_value} seconds."

    if command in ["enable whatsapp success popup", "turn on whatsapp success popup"]:
        update_setting("browser.whatsapp_success_popup_enabled", True)
        return "WhatsApp success popup enabled."

    if command in ["disable whatsapp success popup", "turn off whatsapp success popup"]:
        update_setting("browser.whatsapp_success_popup_enabled", False)
        return "WhatsApp success popup disabled."

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

    health_interval_match = re.match(
        r"^(?:set|change|update)\s+health popup interval\s+to\s+(\d+)$", command
    )
    if health_interval_match:
        interval_value = max(5, int(health_interval_match.group(1)))
        update_setting("notifications.health_popup_interval_minutes", interval_value)
        return f"Health popup interval updated to {interval_value} minutes."

    weather_interval_match = re.match(
        r"^(?:set|change|update)\s+weather popup interval\s+to\s+(\d+)$", command
    )
    if weather_interval_match:
        interval_value = max(15, int(weather_interval_match.group(1)))
        update_setting("notifications.weather_popup_interval_minutes", interval_value)
        return f"Weather popup interval updated to {interval_value} minutes."

    status_interval_match = re.match(
        r"^(?:set|change|update)\s+status popup interval\s+to\s+(\d+)$", command
    )
    if status_interval_match:
        interval_value = max(15, int(status_interval_match.group(1)))
        update_setting("notifications.status_popup_interval_minutes", interval_value)
        return f"Status popup interval updated to {interval_value} minutes."

    brief_interval_match = re.match(
        r"^(?:set|change|update)\s+brief popup interval\s+to\s+(\d+)$", command
    )
    if brief_interval_match:
        interval_value = max(30, int(brief_interval_match.group(1)))
        update_setting("notifications.brief_popup_interval_minutes", interval_value)
        return f"Brief popup interval updated to {interval_value} minutes."

    agenda_interval_match = re.match(
        r"^(?:set|change|update)\s+agenda popup interval\s+to\s+(\d+)$", command
    )
    if agenda_interval_match:
        interval_value = max(5, int(agenda_interval_match.group(1)))
        update_setting("notifications.agenda_popup_interval_minutes", interval_value)
        return f"Agenda popup interval updated to {interval_value} minutes."

    recap_interval_match = re.match(
        r"^(?:set|change|update)\s+recap popup interval\s+to\s+(\d+)$", command
    )
    if recap_interval_match:
        interval_value = max(30, int(recap_interval_match.group(1)))
        update_setting("notifications.recap_popup_interval_minutes", interval_value)
        return f"Recap popup interval updated to {interval_value} minutes."

    morning_time_match = re.match(
        r"^(?:set|change|update)\s+morning brief time\s+to\s+(\d{1,2}:\d{2})$", command
    )
    if morning_time_match:
        update_setting("notifications.morning_brief_time", morning_time_match.group(1))
        return f"Morning brief time updated to {morning_time_match.group(1)}."

    night_time_match = re.match(
        r"^(?:set|change|update)\s+night summary time\s+to\s+(\d{1,2}:\d{2})$", command
    )
    if night_time_match:
        update_setting("notifications.night_summary_time", night_time_match.group(1))
        return f"Night summary time updated to {night_time_match.group(1)}."

    ocr_hotkey_match = re.match(
        r"^(?:set|change|update)\s+ocr hotkey\s+to\s+(.+)$", command
    )
    if ocr_hotkey_match:
        hotkey_value = ocr_hotkey_match.group(1).strip().lower()
        update_setting("ocr.region_hotkey", hotkey_value)
        return f"OCR region hotkey updated to {hotkey_value}. Restart the assistant to use the new hotkey."

    overlay_hotkey_match = re.match(
        r"^(?:set|change|update)\s+overlay hotkey\s+to\s+(.+)$", command
    )
    if overlay_hotkey_match:
        hotkey_value = overlay_hotkey_match.group(1).strip().lower()
        update_setting("overlay.hotkey", hotkey_value)
        return (
            f"Quick command overlay hotkey updated to {hotkey_value}. "
            "Restart the assistant to use the new hotkey."
        )

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
        whatsapp_retry_count = get_setting("browser.whatsapp_search_retry_count", 2)
        whatsapp_retry_delay = get_setting("browser.whatsapp_search_retry_delay_seconds", 1.2)
        whatsapp_auto_send = get_setting("browser.whatsapp_auto_send", True)
        whatsapp_send_press_count = get_setting("browser.whatsapp_send_press_count", 1)
        whatsapp_send_confirm_delay = get_setting(
            "browser.whatsapp_send_confirm_delay_seconds", 0.8
        )
        whatsapp_success_popup = get_setting("browser.whatsapp_success_popup_enabled", True)
        gmail_delay = get_setting("browser.gmail_load_delay_seconds", 8)
        ocr_hotkey_enabled = get_setting("ocr.region_hotkey_enabled", True)
        ocr_hotkey = get_setting("ocr.region_hotkey", "ctrl+shift+o")
        overlay_hotkey_enabled = get_setting("overlay.hotkey_enabled", True)
        overlay_hotkey = get_setting("overlay.hotkey", "ctrl+shift+space")
        reminder_monitor = get_setting("notifications.reminder_monitor_enabled", True)
        reminder_interval = get_setting("notifications.reminder_check_interval_minutes", 15)
        event_monitor = get_setting("notifications.event_monitor_enabled", True)
        event_interval = get_setting("notifications.event_check_interval_minutes", 15)
        health_popup_enabled = get_setting("notifications.health_popup_enabled", False)
        health_popup_on_startup = get_setting("notifications.health_popup_on_startup", False)
        health_popup_interval = get_setting("notifications.health_popup_interval_minutes", 60)
        weather_popup_enabled = get_setting("notifications.weather_popup_enabled", False)
        weather_popup_on_startup = get_setting("notifications.weather_popup_on_startup", False)
        weather_popup_interval = get_setting("notifications.weather_popup_interval_minutes", 120)
        status_popup_enabled = get_setting("notifications.status_popup_enabled", False)
        status_popup_on_startup = get_setting("notifications.status_popup_on_startup", False)
        status_popup_interval = get_setting("notifications.status_popup_interval_minutes", 120)
        brief_popup_enabled = get_setting("notifications.brief_popup_enabled", False)
        brief_popup_on_startup = get_setting("notifications.brief_popup_on_startup", False)
        brief_popup_interval = get_setting("notifications.brief_popup_interval_minutes", 180)
        morning_brief_automation = get_setting("notifications.morning_brief_automation_enabled", False)
        morning_brief_time = get_setting("notifications.morning_brief_time", "08:00")
        morning_agenda_combo = get_setting("notifications.morning_agenda_combo_enabled", False)
        night_summary_export = get_setting("notifications.night_summary_export_enabled", False)
        night_summary_time = get_setting("notifications.night_summary_time", "21:00")
        weekdays_only = get_setting("notifications.automation_weekdays_only", False)
        weekend_automation = get_setting("notifications.weekend_automation_enabled", True)
        compact_voice_replies = get_setting("assistant.compact_voice_replies", True)
        agenda_popup_enabled = get_setting("notifications.agenda_popup_enabled", False)
        agenda_popup_on_startup = get_setting("notifications.agenda_popup_on_startup", False)
        agenda_popup_interval = get_setting("notifications.agenda_popup_interval_minutes", 60)
        recap_popup_enabled = get_setting("notifications.recap_popup_enabled", False)
        recap_popup_on_startup = get_setting("notifications.recap_popup_on_startup", False)
        recap_popup_interval = get_setting("notifications.recap_popup_interval_minutes", 180)
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
            f"WhatsApp retry count is {whatsapp_retry_count}. "
            f"WhatsApp retry delay is {whatsapp_retry_delay} seconds. "
            f"WhatsApp auto send is {'on' if whatsapp_auto_send else 'off'}. "
            f"WhatsApp send press count is {whatsapp_send_press_count}. "
            f"WhatsApp send confirm delay is {whatsapp_send_confirm_delay} seconds. "
            f"WhatsApp success popup is {'on' if whatsapp_success_popup else 'off'}. "
            f"Gmail load delay is {gmail_delay} seconds. "
            f"OCR region hotkey is {ocr_hotkey}. "
            f"OCR hotkey is {'on' if ocr_hotkey_enabled else 'off'}. "
            f"Quick overlay hotkey is {overlay_hotkey}. "
            f"Quick overlay is {'on' if overlay_hotkey_enabled else 'off'}. "
            f"Tray startup is {'on' if tray_mode else 'off'}. "
            f"Reminder monitor is {'on' if reminder_monitor else 'off'}. "
            f"Reminder interval is {reminder_interval} minutes. "
            f"Event monitor is {'on' if event_monitor else 'off'}. "
            f"Event interval is {event_interval} minutes. "
            f"Health popup is {'on' if health_popup_enabled else 'off'}. "
            f"Health popup on startup is {'on' if health_popup_on_startup else 'off'}. "
            f"Health popup interval is {health_popup_interval} minutes. "
            f"Weather popup is {'on' if weather_popup_enabled else 'off'}. "
            f"Weather popup on startup is {'on' if weather_popup_on_startup else 'off'}. "
            f"Weather popup interval is {weather_popup_interval} minutes. "
            f"Status popup is {'on' if status_popup_enabled else 'off'}. "
            f"Status popup on startup is {'on' if status_popup_on_startup else 'off'}. "
            f"Status popup interval is {status_popup_interval} minutes. "
            f"Brief popup is {'on' if brief_popup_enabled else 'off'}. "
            f"Brief popup on startup is {'on' if brief_popup_on_startup else 'off'}. "
            f"Brief popup interval is {brief_popup_interval} minutes. "
            f"Morning brief automation is {'on' if morning_brief_automation else 'off'}. "
            f"Morning brief time is {morning_brief_time}. "
            f"Morning agenda combo is {'on' if morning_agenda_combo else 'off'}. "
            f"Night summary export is {'on' if night_summary_export else 'off'}. "
            f"Night summary time is {night_summary_time}. "
            f"Weekday only automations are {'on' if weekdays_only else 'off'}. "
            f"Weekend automations are {'on' if weekend_automation else 'off'}. "
            f"Compact voice replies are {'on' if compact_voice_replies else 'off'}. "
            f"Agenda popup is {'on' if agenda_popup_enabled else 'off'}. "
            f"Agenda popup on startup is {'on' if agenda_popup_on_startup else 'off'}. "
            f"Agenda popup interval is {agenda_popup_interval} minutes. "
            f"Recap popup is {'on' if recap_popup_enabled else 'off'}. "
            f"Recap popup on startup is {'on' if recap_popup_on_startup else 'off'}. "
            f"Recap popup interval is {recap_popup_interval} minutes. "
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

    if command in ["enable health popup", "turn on health popup"]:
        update_setting("notifications.health_popup_enabled", True)
        return "Health popup monitor enabled."

    if command in ["disable health popup", "turn off health popup"]:
        update_setting("notifications.health_popup_enabled", False)
        return "Health popup monitor disabled."

    if command in ["enable weather popup", "turn on weather popup"]:
        update_setting("notifications.weather_popup_enabled", True)
        return "Weather popup monitor enabled."

    if command in ["disable weather popup", "turn off weather popup"]:
        update_setting("notifications.weather_popup_enabled", False)
        return "Weather popup monitor disabled."

    if command in ["enable status popup", "turn on status popup"]:
        update_setting("notifications.status_popup_enabled", True)
        return "Status popup monitor enabled."

    if command in ["disable status popup", "turn off status popup"]:
        update_setting("notifications.status_popup_enabled", False)
        return "Status popup monitor disabled."

    if command in ["enable brief popup", "turn on brief popup"]:
        update_setting("notifications.brief_popup_enabled", True)
        return "Brief popup monitor enabled."

    if command in ["disable brief popup", "turn off brief popup"]:
        update_setting("notifications.brief_popup_enabled", False)
        return "Brief popup monitor disabled."

    if command in ["enable startup health popup", "turn on startup health popup"]:
        update_setting("notifications.health_popup_on_startup", True)
        return "Startup health popup enabled."

    if command in ["disable startup health popup", "turn off startup health popup"]:
        update_setting("notifications.health_popup_on_startup", False)
        return "Startup health popup disabled."

    if command in ["enable startup weather popup", "turn on startup weather popup"]:
        update_setting("notifications.weather_popup_on_startup", True)
        return "Startup weather popup enabled."

    if command in ["disable startup weather popup", "turn off startup weather popup"]:
        update_setting("notifications.weather_popup_on_startup", False)
        return "Startup weather popup disabled."

    if command in ["enable startup status popup", "turn on startup status popup"]:
        update_setting("notifications.status_popup_on_startup", True)
        return "Startup status popup enabled."

    if command in ["disable startup status popup", "turn off startup status popup"]:
        update_setting("notifications.status_popup_on_startup", False)
        return "Startup status popup disabled."

    if command in ["enable startup brief popup", "turn on startup brief popup"]:
        update_setting("notifications.brief_popup_on_startup", True)
        return "Startup brief popup enabled."

    if command in ["disable startup brief popup", "turn off startup brief popup"]:
        update_setting("notifications.brief_popup_on_startup", False)
        return "Startup brief popup disabled."

    if command in ["enable morning brief automation", "turn on morning brief automation"]:
        update_setting("notifications.morning_brief_automation_enabled", True)
        return "Morning brief automation enabled."

    if command in ["disable morning brief automation", "turn off morning brief automation"]:
        update_setting("notifications.morning_brief_automation_enabled", False)
        return "Morning brief automation disabled."

    if command in ["enable morning agenda combo", "turn on morning agenda combo"]:
        update_setting("notifications.morning_agenda_combo_enabled", True)
        return "Morning agenda combo enabled."

    if command in ["disable morning agenda combo", "turn off morning agenda combo"]:
        update_setting("notifications.morning_agenda_combo_enabled", False)
        return "Morning agenda combo disabled."

    if command in ["enable night summary export", "turn on night summary export"]:
        update_setting("notifications.night_summary_export_enabled", True)
        return "Night summary export enabled."

    if command in ["disable night summary export", "turn off night summary export"]:
        update_setting("notifications.night_summary_export_enabled", False)
        return "Night summary export disabled."

    if command in ["enable weekday only automations", "turn on weekday only automations"]:
        update_setting("notifications.automation_weekdays_only", True)
        return "Weekday only automations enabled."

    if command in ["disable weekday only automations", "turn off weekday only automations"]:
        update_setting("notifications.automation_weekdays_only", False)
        return "Weekday only automations disabled."

    if command in ["enable weekend automations", "turn on weekend automations"]:
        update_setting("notifications.weekend_automation_enabled", True)
        return "Weekend automations enabled."

    if command in ["disable weekend automations", "turn off weekend automations"]:
        update_setting("notifications.weekend_automation_enabled", False)
        return "Weekend automations disabled."

    if command in ["enable compact voice replies", "turn on compact voice replies"]:
        update_setting("assistant.compact_voice_replies", True)
        return "Compact voice replies enabled."

    if command in ["disable compact voice replies", "turn off compact voice replies"]:
        update_setting("assistant.compact_voice_replies", False)
        return "Compact voice replies disabled."

    if command in ["enable agenda popup", "turn on agenda popup"]:
        update_setting("notifications.agenda_popup_enabled", True)
        return "Agenda popup monitor enabled."

    if command in ["disable agenda popup", "turn off agenda popup"]:
        update_setting("notifications.agenda_popup_enabled", False)
        return "Agenda popup monitor disabled."

    if command in ["enable startup agenda popup", "turn on startup agenda popup"]:
        update_setting("notifications.agenda_popup_on_startup", True)
        return "Startup agenda popup enabled."

    if command in ["disable startup agenda popup", "turn off startup agenda popup"]:
        update_setting("notifications.agenda_popup_on_startup", False)
        return "Startup agenda popup disabled."

    if command in ["enable recap popup", "turn on recap popup"]:
        update_setting("notifications.recap_popup_enabled", True)
        return "Recap popup monitor enabled."

    if command in ["disable recap popup", "turn off recap popup"]:
        update_setting("notifications.recap_popup_enabled", False)
        return "Recap popup monitor disabled."

    if command in ["enable startup recap popup", "turn on startup recap popup"]:
        update_setting("notifications.recap_popup_on_startup", True)
        return "Startup recap popup enabled."

    if command in ["disable startup recap popup", "turn off startup recap popup"]:
        update_setting("notifications.recap_popup_on_startup", False)
        return "Startup recap popup disabled."

    if command in ["enable ocr hotkey", "turn on ocr hotkey", "enable region hotkey"]:
        update_setting("ocr.region_hotkey_enabled", True)
        return "OCR region hotkey enabled. Restart the assistant if it was already running."

    if command in ["disable ocr hotkey", "turn off ocr hotkey", "disable region hotkey"]:
        update_setting("ocr.region_hotkey_enabled", False)
        return "OCR region hotkey disabled. Restart the assistant if it was already running."

    if command in ["enable quick overlay", "turn on quick overlay", "enable overlay hotkey"]:
        update_setting("overlay.hotkey_enabled", True)
        return "Quick command overlay enabled. Restart the assistant if it was already running."

    if command in ["disable quick overlay", "turn off quick overlay", "disable overlay hotkey"]:
        update_setting("overlay.hotkey_enabled", False)
        return "Quick command overlay disabled. Restart the assistant if it was already running."

    if command in ["toggle overlay hotkey", "toggle quick overlay hotkey"]:
        current = bool(get_setting("overlay.hotkey_enabled", True))
        update_setting("overlay.hotkey_enabled", not current)
        state = "enabled" if not current else "disabled"
        return f"Quick command overlay hotkey {state}. Restart the assistant if it was already running."

    if command in ["toggle ocr hotkey", "toggle region hotkey"]:
        current = bool(get_setting("ocr.region_hotkey_enabled", True))
        update_setting("ocr.region_hotkey_enabled", not current)
        state = "enabled" if not current else "disabled"
        return f"OCR region hotkey {state}. Restart the assistant if it was already running."

    if command in ["enable whatsapp auto send", "turn on whatsapp auto send"]:
        update_setting("browser.whatsapp_auto_send", True)
        return "WhatsApp auto send enabled."

    if command in ["disable whatsapp auto send", "turn off whatsapp auto send"]:
        update_setting("browser.whatsapp_auto_send", False)
        return "WhatsApp auto send disabled."

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

    command = _normalize_voice_friendly_command(command)
    if command:
        log_command(command, source=input_mode)

    pin_match = re.match(r"^pin command\s+(.+)$", command)
    if pin_match:
        speak(pin_overlay_command(pin_match.group(1).strip())[1])
        return

    unpin_match = re.match(r"^unpin command\s+(.+)$", command)
    if unpin_match:
        speak(unpin_overlay_command(unpin_match.group(1).strip())[1])
        return

    move_pin_match = re.match(r"^move pinned command\s+(.+?)\s+(up|down|top|bottom)$", command)
    if move_pin_match:
        speak(move_pinned_command(move_pin_match.group(1).strip(), move_pin_match.group(2).strip())[1])
        return

    if command in ["list pinned commands", "show pinned commands", "pinned commands"]:
        speak(list_pinned_commands())
        return

    config_reply = _handle_config_command(command)
    if config_reply:
        speak(config_reply)
        return

    contact_lookup_reply = _handle_contact_lookup_command(command)
    if contact_lookup_reply:
        speak(contact_lookup_reply)
        return

    contact_action_reply = _handle_contact_action_command(command)
    if contact_action_reply:
        speak(contact_action_reply)
        set_last_result(contact_action_reply)
        return

    followup_reply = _handle_followup_command(command)
    if followup_reply:
        speak(followup_reply)
        set_last_result(followup_reply)
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
        "open quick command overlay",
        "show quick command overlay",
        "open quick overlay",
        "show quick overlay",
    ]:
        recent_commands = get_recent_commands()
        overlay_suggestions = {
            "Planning": [
                "today agenda",
                "what is due today",
                "show overdue items",
            ],
            "System": [
                "weather",
                "dashboard",
                "show settings",
                "system status",
                "export productivity summary",
            ],
            "OCR": [
                "copy selected area text",
                "read selected area",
            ],
        }
        pinned_commands = get_pinned_commands()
        if pinned_commands:
            overlay_suggestions = {
                f"Pinned ({len(pinned_commands)})": pinned_commands,
                **overlay_suggestions,
            }
        success, message = show_quick_overlay(
            lambda overlay_command: process_command(
                overlay_command, INSTALLED_APPS, input_mode="text"
            ),
            suggestions=overlay_suggestions,
            recent_commands=recent_commands,
            recent_actions=recent_commands[:4],
        )
        speak(message if message else "Quick command overlay updated.")
        return

    if command in ["toggle quick overlay", "toggle quick command overlay"]:
        if is_quick_overlay_open():
            success, message = hide_quick_overlay()
            speak(message if message else "Quick command overlay updated.")
            return

        recent_commands = get_recent_commands()
        overlay_suggestions = {
            "Planning": [
                "today agenda",
                "what is due today",
                "show overdue items",
            ],
            "System": [
                "weather",
                "dashboard",
                "show settings",
                "system status",
                "export productivity summary",
            ],
            "OCR": [
                "copy selected area text",
                "read selected area",
            ],
        }
        pinned_commands = get_pinned_commands()
        if pinned_commands:
            overlay_suggestions = {
                f"Pinned ({len(pinned_commands)})": pinned_commands,
                **overlay_suggestions,
            }
        success, message = show_quick_overlay(
            lambda overlay_command: process_command(
                overlay_command, INSTALLED_APPS, input_mode="text"
            ),
            suggestions=overlay_suggestions,
            recent_commands=recent_commands,
            recent_actions=recent_commands[:4],
        )
        speak(message if message else "Quick command overlay updated.")
        return

    if command in [
        "hide quick command overlay",
        "close quick command overlay",
        "hide quick overlay",
        "close quick overlay",
    ]:
        success, message = hide_quick_overlay()
        speak(message if message else "Quick command overlay updated.")
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

    if command in [
        "copy selected area text",
        "copy selected region text",
        "copy text from selected area",
    ]:
        speak(
            "Move your mouse to the first corner now. I will capture the second corner in three seconds."
        )
        result = copy_selected_area_text()

        if isinstance(result, dict):
            print("\n===== SELECTED AREA TEXT =====\n")
            print(result["text"])
            print("\n==============================\n")
            speak(result["message"])
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

    named_region_copy_commands = {
        "copy top left area text": "top left",
        "copy top right area text": "top right",
        "copy bottom left area text": "bottom left",
        "copy bottom right area text": "bottom right",
        "copy center area text": "center",
    }
    if command in named_region_copy_commands:
        region_name = named_region_copy_commands[command]
        speak(f"Copying text from the {region_name} area")
        result = copy_named_screen_region_text(region_name)
        speak(result)
        return

    if "read screen" in command or "what is on screen" in command:
        speak("Scanning screen")

        text = read_screen_text()

        print("\n===== SCREEN TEXT =====\n")
        print(text)
        print("\n========================\n")

        speak("Screen content printed")
        return

    if command in ["copy screen text", "copy text from screen"]:
        speak("Scanning screen and copying text")
        result = copy_screen_text()
        speak(result)
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
        set_last_result(intent_result["reply"])
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
        compact_reply = input_mode == "voice" and get_setting("assistant.compact_voice_replies", True)
        if stream_output:
            start_streaming_reply()
        try:
            response = ask_ollama(
                f"The user is asking about {app_scan_module.LAST_TOPIC}. {command}",
                stream_callback=append_streaming_reply if stream_output else None,
                compact=compact_reply,
            )
        finally:
            if stream_output:
                end_streaming_reply()
        speak(response, already_printed=stream_output)
        set_last_result(response)
        return

    # -------- GENERAL AI RESPONSE --------
    try:
        stream_output = input_mode == "text"
        compact_reply = input_mode == "voice" and get_setting("assistant.compact_voice_replies", True)
        if stream_output:
            start_streaming_reply()
        try:
            response = ask_ollama(
                command,
                stream_callback=append_streaming_reply if stream_output else None,
                compact=compact_reply,
            )
        finally:
            if stream_output:
                end_streaming_reply()
        if response:
            speak(response, already_printed=stream_output)
            set_last_result(response)
        else:
            speak("I did not get a proper response.")

    except Exception as e:
        print("Error:", e)

        play_sound("error.wav")
        speak("Something went wrong")
