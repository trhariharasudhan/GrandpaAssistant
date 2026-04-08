import contextlib
import datetime
import json
import os
import re
import subprocess
import threading
import time
import webbrowser

import keyboard
from brain.ai_engine import ask_ollama, clear_memory
from brain.database import get_recent_commands, log_command
from core.followup_memory import (
    get_best_followup_text,
    get_last_interaction_id,
    get_last_user_input,
    set_last_interaction_id,
    set_last_result,
    set_last_user_input,
)
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
from brain.semantic_memory import (
    semantic_memory_search_summary,
    semantic_memory_status_summary,
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
    find_best_app_match,
    refresh_apps_cache,
)
import modules.app_scan_module as app_scan_module
from modules.briefing_module import build_due_reminder_alert
from modules.dictation_module import start_dictation, stop_dictation
from modules.media_module import media_control, type_text_dynamic
from modules.system_module import (
    take_screenshot,
    get_battery_info,
    get_cleanup_suggestion,
    get_motivation_line,
    get_storage_report,
    handle_wifi,
    handle_bluetooth,
    handle_airplane,
    handle_focus_assist,
    handle_camera_controls,
    handle_microphone_controls,
    handle_quick_settings_controls,
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
    is_running_as_admin,
    relaunch_assistant_as_admin,
)
from modules.web_module import wikipedia_search
from modules.notes_module import add_note
from modules.profile_module import remember_emotion_signal
from modules.task_module import add_reminder
from modules.nextgen_module import (
    add_goal_milestone,
    add_habit,
    automation_history_summary,
    capture_meeting_note,
    check_in_habit,
    complete_goal_milestone,
    create_automation_rule,
    create_goal,
    generate_ai_day_plan,
    goal_board_summary,
    habit_dashboard_summary,
    language_mode_status,
    list_automation_rules,
    meeting_mode_summary,
    mobile_companion_status,
    move_document_to_folder,
    nextgen_status_snapshot,
    preview_language_response,
    rag_library_summary,
    run_due_automation_rules,
    send_mobile_update,
    set_automation_enabled,
    set_language_mode,
    setup_mobile_companion,
    smart_reminder_priority_summary,
    tag_document,
    voice_trainer_status,
    apply_voice_trainer,
)
from modules.google_contacts_module import (
    add_favorite_contact,
    ensure_google_contacts_fresh,
    get_recent_contact_change_summary,
    get_google_contact_matches,
    import_google_contact_to_memory,
    list_contact_aliases,
    list_favorite_contacts,
    list_google_contacts,
    merge_google_contacts_into_memory,
    remove_favorite_contact,
    remove_contact_alias,
    set_contact_alias,
    sync_google_contacts,
)
from modules.google_calendar_module import (
    add_google_calendar_event,
    delete_google_calendar_event_by_title,
    delete_latest_google_calendar_event,
    google_calendar_status,
    list_google_calendar_event_titles,
    rename_google_calendar_event_by_title,
    rename_latest_google_calendar_event,
    reschedule_google_calendar_event_by_title,
    reschedule_latest_google_calendar_event,
    sync_google_calendar,
    today_google_calendar_events,
    upcoming_google_calendar_events,
)
from modules.messaging_automation_module import quick_email_shortcut, quick_whatsapp_message
from modules.desktop_launch_module import (
    open_react_browser_ui,
    open_react_desktop_ui,
    tray_react_status,
)
from modules.notification_module import show_custom_popup
from modules.startup_module import (
    disable_startup_auto_launch,
    enable_startup_auto_launch,
    refresh_startup_auto_launch,
    startup_auto_launch_status,
)
from modules.windows_voice_control_module import (
    get_active_window_summary,
    handle_desktop_action,
    handle_settings_page_action,
    handle_voice_access_control,
    open_default_windows_app,
    open_windows_settings_page,
    run_windows_voice_macro,
)
from modules.window_context_module import (
    editor_run_current_file,
    editor_save_current_file,
    get_active_app_name,
    handle_visible_screen_action,
    handle_whatsapp_screen_action,
    summarize_code_editor,
)
from controls.brightness_control import handle_brightness
from controls.volume_control import handle_volume, set_volume_percentage
from utils.sound import play_sound
from utils.config import APP_ALIASES, get_setting, update_setting
from device_manager import DEVICE_MANAGER
from startup_diagnostics import collect_startup_diagnostics, format_startup_diagnostics_report
from features.productivity.briefing_module import build_brief_details
from features.productivity.profile_module import build_proactive_nudge
from features.productivity.proactive_suggestion_engine import (
    generate_proactive_suggestions,
    get_latest_proactive_suggestions,
)
from features.productivity.task_module import (
    due_today_summary,
    get_planner_focus_snapshot,
    latest_reminder,
    latest_task,
    overdue_items,
)
from features.security.emergency_dispatch import trigger_dual_emergency_protocol
from features.security.face_verification import enroll_user_face, verify_user_face, is_face_enrolled
from cognition.hub import record_assistant_turn, submit_response_feedback
from cognition.learning_engine import learning_status_payload
from security.auth_manager import (
    admin_mode_active,
    auth_status_payload,
    disable_admin_mode,
    disable_lockdown,
    enable_admin_mode,
    enable_lockdown,
    enroll_user_voice,
    set_security_pin,
    verify_face_identity,
    verify_security_pin,
    verify_user_voice,
)
from security.device_monitor import device_security_status_payload, trust_device
from security.hub import security_logs_payload, security_status_payload, validate_command
from features.integrations.iot_module import dispatch_iot_command, recent_iot_actions, resolve_iot_command, run_iot_command
from iot_registry import validate_iot_config
from vision.hand_mouse_control import run_hand_mouse
from vision.object_detection import (
    apply_object_detection_alert_profile,
    clear_watch_target,
    delete_object_detection_preset,
    clear_detection_history,
    consume_watch_alert,
    count_detected_object,
    detect_objects_on_screen,
    detect_objects_once,
    get_detection_history,
    get_latest_detection_summary,
    get_object_detection_model_name,
    get_object_detection_alert_profile,
    get_object_detection_presets,
    get_supported_object_labels,
    get_watch_alert_cooldown_seconds,
    get_watch_event_history,
    get_watch_status,
    is_small_object_mode_enabled,
    is_object_detection_available,
    is_detected_object_visible,
    object_detection_import_error,
    reset_object_detection_model,
    run_object_detection,
    save_object_detection_preset,
    set_object_detection_model_name,
    set_watch_alert_cooldown_seconds,
    set_small_object_mode,
    set_watch_target,
    use_object_detection_preset,
)
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
from voice.listen import (
    apply_voice_profile,
    clap_wake_status_summary,
    continuous_conversation_enabled,
    current_voice_mode,
    enable_easy_wake_mode,
    set_clap_wake_enabled,
    set_stt_backend,
    stt_backend_status_summary,
    voice_status_summary,
)
from voice.speak import (
    accept_custom_voice_license,
    autoconfigure_piper_model,
    append_streaming_reply,
    autoconfigure_custom_voice_sample,
    choose_custom_voice_sample_summary,
    choose_piper_model_summary,
    clear_piper_config_path,
    clear_piper_model_path,
    clear_custom_voice_sample_path,
    custom_voice_license_status_summary,
    custom_voice_status_summary,
    end_streaming_reply,
    list_custom_voice_samples_summary,
    list_piper_models_summary,
    piper_setup_status_summary,
    prefer_custom_voice_backend,
    prefer_piper_backend,
    set_custom_voice_sample_path,
    set_piper_config_path,
    set_piper_model_path,
    set_tts_backend,
    speak,
    start_streaming_reply,
    tts_backend_status_summary,
    voice_output_status_summary,
)
from utils.paths import backend_data_path, backend_path, config_path, docs_path

mouse_stop_event = None
mouse_stop_requested_by_command = False
object_detection_stop_event = None
object_detection_stop_requested_by_command = False
pending_confirmation = None
last_contact_context = {"name": "", "action": ""}
security_bypass_context = {"command": "", "expires_at": 0.0}
IOT_CREDENTIALS_PATH = config_path("iot_credentials.json")
IOT_EXAMPLE_PATH = backend_path("assets", "iot_credentials.example.json")
FACE_PROFILE_PATH = backend_data_path("face_profile.json")
VOICE_IOT_SETUP_DOC_PATH = docs_path("local-voice-iot-setup.md")


def _current_location_text():
    city = get_memory("personal.location.current_location.city")
    area = get_memory("personal.location.current_location.area")
    state = get_memory("personal.location.current_location.state")
    country = get_memory("personal.location.current_location.country")
    address = get_memory("personal.contact.address")
    location_parts = [part for part in [area, city, state, country] if part]
    if address:
        return address
    if location_parts:
        return ", ".join(location_parts)
    return None


def _offline_mode_summary():
    return (
        "Offline core mode is for local-safe features like tasks, reminders, notes, contacts, OCR, local AI, "
        "basic system control, and developer shortcuts. Internet-based services like Telegram, Google sync, "
        "cloud GitHub actions, and online messaging verification may stay limited."
    )


def _offline_quick_help():
    return (
        "Offline quick help: tasks, reminders, notes, contacts, OCR, local system commands, local AI, "
        "developer shortcuts, and saved memory should work best. Cloud sync, Telegram, Google services, and "
        "internet-dependent messaging checks may stay limited."
    )


def _security_status_summary():
    payload = security_status_payload(DEVICE_MANAGER)
    auth = payload.get("auth", {})
    threats = payload.get("threats", {})
    devices = payload.get("devices", {})
    encryption = payload.get("encryption", {})
    session = "active" if auth.get("session_active") else "inactive"
    admin = "active" if auth.get("admin_mode_active") else "inactive"
    lockdown = "on" if auth.get("lockdown") else "off"
    return (
        f"Security status: session is {session}. "
        f"Admin mode is {admin}. "
        f"Lockdown is {lockdown}. "
        f"Failed attempts are {auth.get('failed_attempts', 0)}. "
        f"Unknown devices: {devices.get('unknown_device_count', 0)}. "
        f"Blocked security events: {threats.get('blocked_count', 0)}. "
        f"Encrypted data protection is {'ready' if encryption.get('available') else 'not ready'}."
    )


def _security_alerts_summary():
    payload = device_security_status_payload()
    alerts = payload.get("recent_alerts") or []
    if not alerts:
        return "No recent security alerts were recorded."
    return "Recent security alerts: " + " | ".join(item.get("message", "Security alert") for item in alerts[:6])


def _security_logs_summary():
    items = security_logs_payload(limit=6).get("items") or []
    if not items:
        return "No security activity has been recorded yet."
    return "Recent security log entries: " + " | ".join(
        f"{item.get('event_type', 'event')}: {item.get('message', '')}" for item in items[:6]
    )


def _set_security_bypass(command, seconds=8.0):
    security_bypass_context["command"] = " ".join((command or "").lower().strip().split())
    security_bypass_context["expires_at"] = time.time() + max(1.0, float(seconds))


def _consume_security_bypass(command):
    normalized = " ".join((command or "").lower().strip().split())
    if not normalized:
        return False
    if security_bypass_context.get("command") != normalized:
        return False
    if time.time() > float(security_bypass_context.get("expires_at", 0.0) or 0.0):
        security_bypass_context["command"] = ""
        security_bypass_context["expires_at"] = 0.0
        return False
    security_bypass_context["command"] = ""
    security_bypass_context["expires_at"] = 0.0
    return True


def _developer_mode_summary():
    return (
        "Developer mode is ready. You can use local coding helpers like summarize code, save current file, run current file, "
        "open terminal, check git status, and ask for code generation or debugging."
    )


def _developer_workspace_summary():
    active_app = get_active_app_name()
    git_line = _local_git_status_summary()
    if active_app and "code" in active_app.lower():
        code_line = summarize_code_editor()
        return f"Developer summary: {code_line} {git_line}"
    return f"Developer summary: active app is {active_app or 'unknown'}. {git_line}"


def _developer_save_and_run():
    save_reply = editor_save_current_file()
    run_reply = editor_run_current_file()
    return f"{save_reply} {run_reply}"


def _emergency_mode_summary():
    return (
        "Emergency mode is ready. I can alert your emergency contact, share your saved location, and trigger a quick call flow."
    )


def _emergency_quick_response_summary():
    return (
        "Emergency quick responses: send emergency alert, send i am safe alert, share my location, call emergency contact."
    )


def _open_local_terminal():
    try:
        subprocess.Popen(
            ["cmd.exe", "/k", f"cd /d {os.getcwd()}"],
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
        )
        return "Opened a local terminal in the current project."
    except Exception:
        return "I could not open a local terminal right now."


def _normalize_open_target(command):
    normalized = " ".join((command or "").lower().strip().split())
    if not normalized:
        return ""
    normalized = re.sub(r"^please\s+", "", normalized).strip()
    normalized = re.sub(r"^(?:open|start|launch)\s+", "", normalized).strip()
    normalized = re.sub(r"^(?:the|my)\s+", "", normalized).strip()
    normalized = re.sub(r"\s+(?:app|application)$", "", normalized).strip()
    filler_tail_words = {"da", "please", "now", "bro", "macha", "sir"}
    words = normalized.split()
    while words and words[-1] in filler_tail_words:
        words.pop()
    normalized = " ".join(words).strip()
    return normalized


def _is_shell_apps_folder_target(target):
    value = (target or "").strip()
    if not value:
        return False
    if "!" in value:
        return True
    if value.startswith("{"):
        return True
    return "\\" in value and not os.path.isabs(value)


def _launch_app_target(target):
    value = (target or "").strip()
    if not value:
        return False

    try:
        if _is_shell_apps_folder_target(value):
            subprocess.Popen(["explorer", f"shell:AppsFolder\\{value}"], shell=False)
            return True
        if os.path.exists(value):
            os.startfile(value)
            return True
        if value.lower().startswith(("ms-", "shell:", "http://", "https://", "mailto:")):
            os.startfile(value)
            return True
        subprocess.Popen(["cmd.exe", "/c", "start", "", value], shell=False)
        return True
    except Exception:
        return False


def _open_scanned_or_known_app(command, installed_apps):
    app_requested = _normalize_open_target(command)
    if not app_requested:
        return "Tell me which app you want me to open."

    alias_target = APP_ALIASES.get(app_requested)
    if alias_target:
        if _launch_app_target(alias_target):
            return f"Opening {app_requested}."
        return f"I could not open {app_requested} right now."

    match = find_best_app_match(app_requested, installed_apps)
    if not match:
        refreshed_apps = refresh_apps_cache()
        installed_apps.clear()
        installed_apps.update(refreshed_apps)
        match = find_best_app_match(app_requested, installed_apps)

    if not match:
        return f"{app_requested.title()} is not installed on this system."

    app_name, launcher_target, _score = match
    if _launch_app_target(launcher_target):
        return f"Opening {app_name}."
    return f"I found {app_name}, but I could not open it right now."


def _local_git_status_summary():
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            capture_output=True,
            text=True,
            timeout=8,
            cwd=os.getcwd(),
        )
    except Exception:
        return "I could not read git status right now."

    output = " ".join((result.stdout or "").split())
    if not output:
        return "Git status looks clean right now."
    return f"Git status: {output}"


def _run_git_command(args, timeout=8):
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd(),
        )
    except Exception:
        return None

    if result.returncode != 0:
        return None
    return (result.stdout or "").strip()


def _git_current_branch_summary():
    branch = _run_git_command(["branch", "--show-current"])
    if not branch:
        return "I could not detect the current git branch."
    return f"Current git branch is {branch}."


def _git_remote_summary():
    remote = _run_git_command(["remote", "-v"])
    if not remote:
        return "I could not read git remotes right now."

    lines = [line.strip() for line in remote.splitlines() if line.strip()]
    if not lines:
        return "No git remotes are configured for this repository."

    unique = []
    seen = set()
    for line in lines:
        compact = " ".join(line.split())
        if compact in seen:
            continue
        seen.add(compact)
        unique.append(compact)

    preview = " | ".join(unique[:3])
    return f"Git remotes: {preview}"


def _git_recent_commits_summary(limit=3):
    log_output = _run_git_command(["log", f"-{limit}", "--pretty=format:%h %s"])
    if not log_output:
        return "I could not read recent git commits right now."

    commits = [line.strip() for line in log_output.splitlines() if line.strip()]
    if not commits:
        return "There are no recent git commits to show."
    return "Recent commits: " + " | ".join(commits)


def _git_repo_summary():
    branch_line = _git_current_branch_summary()
    status_line = _local_git_status_summary()
    remote_line = _git_remote_summary()
    return f"{branch_line} {status_line} {remote_line}"


def _load_local_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return None


def _proactive_suggestions_summary(force_refresh=False):
    suggestions = (
        generate_proactive_suggestions("default")
        if force_refresh
        else get_latest_proactive_suggestions("default", limit=4)
    )
    if not suggestions:
        suggestions = generate_proactive_suggestions("default")

    summary_parts = [build_proactive_nudge()]
    today_line = due_today_summary()
    latest_task_line = latest_task()
    latest_reminder_line = latest_reminder()
    overdue_line = overdue_items()

    if today_line and today_line != "You have nothing due today.":
        summary_parts.append(today_line)
    if latest_task_line and latest_task_line != "You have no pending tasks right now.":
        summary_parts.append(latest_task_line)
    if latest_reminder_line and latest_reminder_line != "You have no reminders right now.":
        summary_parts.append(latest_reminder_line)
    if overdue_line and overdue_line != "You have no overdue reminders right now.":
        summary_parts.append(overdue_line)

    if suggestions:
        top_lines = " | ".join(item.get("text", "") for item in suggestions[:3] if item.get("text"))
        if top_lines:
            summary_parts.append(f"Top proactive suggestions: {top_lines}.")
    else:
        summary_parts.append(build_brief_details())

    focus_mode = get_setting("assistant.focus_mode_enabled", False)
    if focus_mode:
        summary_parts.append("Focus mode is on, so proactive popups stay quiet until you turn it off.")

    return " ".join(part for part in summary_parts if part)


def _smart_home_status_summary():
    creds = _load_local_json(IOT_CREDENTIALS_PATH)
    if not creds:
        return (
            f"Smart Home is not configured yet. Add {IOT_CREDENTIALS_PATH} "
            "with your webhook commands to enable device control."
        )

    enabled = bool(creds.get("enabled"))
    webhooks = creds.get("webhooks") or {}
    if not webhooks:
        return "Smart Home config is loaded, but no device commands are configured yet."

    sample_commands = list(webhooks.keys())[:4]
    placeholder_count = 0
    for config in webhooks.values():
        url = str((config or {}).get("url") or "")
        if "YOUR_KEY_HERE" in url or "YOUR_HOME_ASSISTANT_WEBHOOK_ID" in url:
            placeholder_count += 1

    status = "enabled" if enabled else "disabled"
    summary = [f"Smart Home is {status} with {len(webhooks)} configured command(s)."]
    if sample_commands:
        summary.append("Try commands like " + " | ".join(sample_commands) + ".")
    if placeholder_count:
        summary.append(f"{placeholder_count} device webhook(s) still need real keys or URLs.")
    return " ".join(summary)


def _smart_home_setup_summary():
    return (
        f"Smart Home setup help: copy {IOT_EXAMPLE_PATH} to {IOT_CREDENTIALS_PATH}, "
        "replace the placeholder values with your local webhook, Home Assistant, or MQTT settings, "
        "then set enabled to true. "
        f"Full setup notes are in {VOICE_IOT_SETUP_DOC_PATH}."
    )


def _iot_awareness_summary():
    return DEVICE_MANAGER.iot_summary()


def _hardware_status_summary() -> str:
    return DEVICE_MANAGER.status_summary()


def _hardware_event_history_summary() -> str:
    events = DEVICE_MANAGER.get_recent_events(limit=6)
    if not events:
        return "No recent hardware events were recorded yet."
    return "Recent hardware events: " + " | ".join(
        item.get("message") or f"{item.get('device_name', 'device')}: {item.get('status', 'updated')}"
        for item in events
    )


def _rescan_hardware_summary() -> str:
    status = DEVICE_MANAGER.refresh(emit_events=True)
    devices = status.get("devices") or []
    capabilities = status.get("capabilities") or {}
    summary = status.get("capabilities", {}).get("summary") or "Hardware scan finished."
    return (
        f"Hardware rescan complete. I can currently see {len(devices)} connected device or devices. "
        f"{summary} Event history now has {status.get('event_count', 0)} item or items."
    )


def _iot_knowledge_summary(command: str) -> str | None:
    return DEVICE_MANAGER.local_response(command)


def _iot_action_history_summary() -> str:
    actions = recent_iot_actions(limit=6)
    if not actions:
        return "No recent Smart Home actions were recorded yet."
    return "Recent Smart Home actions: " + " | ".join(
        f"{item.get('matched_command', item.get('input', 'command'))}: {'ok' if item.get('ok') else 'failed'}"
        for item in actions
    )


def _iot_validation_summary() -> str:
    payload = validate_iot_config(test_connectivity=True)
    checks = payload.get("checks") or []
    warnings = [item.get("detail", "") for item in checks if item.get("status") == "warning"][:3]
    errors = [item.get("detail", "") for item in checks if item.get("status") == "error"][:3]
    parts = [payload.get("summary", "IoT validation finished.")]
    if errors:
        parts.append("Errors: " + " | ".join(errors))
    if warnings:
        parts.append("Warnings: " + " | ".join(warnings))
    return " ".join(part for part in parts if part)


def _piper_setup_summary():
    return piper_setup_status_summary()


def _custom_voice_setup_summary():
    return custom_voice_status_summary()


def _face_security_status_summary():
    enrolled = is_face_enrolled()
    if not enrolled:
        return (
            "Face security is not enrolled yet. Say enroll my face to create a local profile, "
            "then verify my face to test it."
        )

    profile_size = 0
    if os.path.exists(FACE_PROFILE_PATH):
        with contextlib.suppress(OSError):
            profile_size = os.path.getsize(FACE_PROFILE_PATH)

    details = ["Face security is enrolled locally and ready for verification."]
    if profile_size:
        details.append(f"Saved profile size is {profile_size} bytes.")
    details.append("Say verify my face whenever you want to confirm identity.")
    return " ".join(details)


def _voice_diagnostics_summary():
    wake_word = get_setting("wake_word", "hey grandpa")
    mode = current_voice_mode()
    stt_backend = get_setting("voice.stt_backend", "auto")
    tts_backend = get_setting("voice.tts_backend", "auto")
    whisper_model = get_setting("voice.whisper_model", "base")
    post_wake_pause = get_setting("voice.post_wake_pause_seconds", 0.35)
    wake_timeout = get_setting("voice.wake_listen_timeout", 5)
    phrase_limit = get_setting("voice.wake_phrase_time_limit", 4)
    wake_threshold = get_setting("voice.wake_match_threshold", 0.68)
    wake_requires_prefix = get_setting("voice.wake_requires_prefix", True)
    wake_max_prefix_words = get_setting("voice.wake_max_prefix_words", 1)
    wake_retry = get_setting("voice.wake_retry_window_seconds", 6)
    follow_up_timeout = get_setting("voice.follow_up_timeout_seconds", 12)
    follow_up_listen_timeout = get_setting("voice.follow_up_listen_timeout", 3)
    follow_up_keep_alive = get_setting("voice.follow_up_keep_alive_seconds", 12)
    continuous_voice = get_setting("voice.continuous_conversation_enabled", True)
    duplicate_window = get_setting("voice.duplicate_command_window_seconds", 4.0)
    wake_ack_cooldown = get_setting("voice.wake_ack_cooldown_seconds", 2.5)
    direct_fallback_min_chars = get_setting("voice.direct_fallback_min_chars", 7)
    direct_fallback_min_words = get_setting("voice.direct_fallback_min_words", 2)
    interrupt_follow_up_seconds = get_setting("voice.interrupt_follow_up_seconds", 5)
    fallback_enabled = get_setting("voice.wake_direct_fallback_enabled", True)
    popup_enabled = get_setting("voice.desktop_popup_enabled", True)
    chime_enabled = get_setting("voice.desktop_chime_enabled", True)
    offline_mode = get_setting("assistant.offline_mode_enabled", False)

    return (
        f"Voice diagnostics: wake word is {wake_word}. "
        f"Profile is {mode}. "
        f"Speech input backend is {stt_backend}. "
        f"Speech output backend is {tts_backend}. "
        f"Whisper model is {whisper_model}. "
        f"Post wake pause is {post_wake_pause} seconds. "
        f"Wake listen timeout is {wake_timeout} seconds. "
        f"Wake phrase limit is {phrase_limit} seconds. "
        f"Wake match threshold is {wake_threshold}. "
        f"Strict wake detection is {'on' if wake_requires_prefix else 'off'}. "
        f"Wake prefix window is {wake_max_prefix_words} words. "
        f"Wake retry window is {wake_retry} seconds. "
        f"Follow up timeout is {follow_up_timeout} seconds. "
        f"Follow up listen timeout is {follow_up_listen_timeout} seconds. "
        f"Follow up keep alive is {follow_up_keep_alive} seconds. "
        f"Continuous conversation is {'on' if continuous_voice else 'off'}. "
        f"Duplicate command guard is {duplicate_window} seconds. "
        f"Wake reply cooldown is {wake_ack_cooldown} seconds. "
        f"Direct fallback minimum is {direct_fallback_min_words} words or {direct_fallback_min_chars} characters. "
        f"Interrupt follow up hold is {interrupt_follow_up_seconds} seconds. "
        f"Direct fallback is {'on' if fallback_enabled else 'off'}. "
        f"Desktop voice popup is {'on' if popup_enabled else 'off'}. "
        f"Desktop voice chime is {'on' if chime_enabled else 'off'}. "
        f"Offline mode is {'on' if offline_mode else 'off'}."
    )


def _assistant_doctor_summary(include_ready=False):
    diagnostics = collect_startup_diagnostics(use_cache=False, allow_create_dirs=False)
    lines = format_startup_diagnostics_report(diagnostics, include_ready=include_ready)
    return " ".join(lines)


def _learning_context_for_text(text):
    lowered = " ".join(str(text or "").lower().split())
    if any(token in lowered for token in ("project", "code", "bug", "meeting", "email", "deadline", "task", "deploy", "server")):
        return "work"
    return "casual"


def _looks_like_explicit_date_query(text):
    normalized = " ".join(str(text or "").lower().split())
    if not normalized:
        return False

    explicit_phrases = (
        "what is the date",
        "what's the date",
        "today date",
        "today's date",
        "what day is it",
        "tell me the date",
        "date today",
        "current date",
        "week number",
        "which day is today",
    )
    if any(phrase in normalized for phrase in explicit_phrases):
        return True

    if re.fullmatch(
        r"(today|tomorrow|yesterday|day after tomorrow|next week|next month|next year|this weekend|monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        normalized,
    ):
        return True

    if re.fullmatch(r"\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?", normalized):
        return True

    if re.search(r"\b(date|day|calendar|week|month|year)\b", normalized):
        return True

    return False


def _remember_terminal_learning_turn(user_text, reply_text, route="terminal-ai", model="assistant"):
    user_text = " ".join(str(user_text or "").split()).strip()
    reply_text = " ".join(str(reply_text or "").split()).strip()
    if not user_text or not reply_text:
        return ""
    interaction = record_assistant_turn(
        user_text,
        reply_text,
        context=_learning_context_for_text(user_text),
        emotion="neutral",
        mood="neutral",
        source="terminal",
        route=route,
        model=model,
    )
    interaction_id = (interaction or {}).get("id", "")
    if interaction_id:
        set_last_interaction_id(interaction_id)
    return interaction_id


def _learning_status_summary():
    status = learning_status_payload()
    preferences = status.get("user_preferences", {})
    response_memory = status.get("response_memory", {})
    behavior = status.get("behavior_learning", {})
    return (
        f"Learning status: {status.get('interaction_count', 0)} interaction(s), "
        f"{status.get('feedback_count', 0)} feedback item(s), and {status.get('success_rate', 0)} percent positive feedback. "
        f"Preferred style is {preferences.get('response_length', 'adaptive')} and {preferences.get('tone', 'adaptive')}. "
        f"Best response memory has {response_memory.get('best_response_count', 0)} example(s), "
        f"failed response memory has {response_memory.get('failed_response_count', 0)} example(s), "
        f"and the most active time window is {behavior.get('active_time_window', 'unknown')}."
    )


def _handle_learning_feedback_command(command, input_mode="text"):
    normalized = " ".join(str(command or "").lower().split())
    positive_commands = {
        "good response",
        "good answer",
        "that was good",
        "that was helpful",
        "helpful response",
        "correct answer",
        "correct response",
        "nice answer",
    }
    negative_commands = {
        "bad response",
        "bad answer",
        "that was bad",
        "that was wrong",
        "that is wrong",
        "wrong answer",
        "wrong response",
        "incorrect answer",
        "incorrect response",
        "not useful",
        "not helpful",
    }

    if normalized in {"learning status", "self learning status", "self improvement status", "what have you learned"}:
        speak(_learning_status_summary())
        return True

    if normalized not in positive_commands and normalized not in negative_commands:
        return False

    last_interaction_id = get_last_interaction_id()
    previous_user_text = get_last_user_input()
    previous_reply = get_best_followup_text()
    if not last_interaction_id and previous_user_text and previous_reply:
        last_interaction_id = _remember_terminal_learning_turn(
            previous_user_text,
            previous_reply,
            route="terminal-retroactive-learning",
            model="assistant",
        )
    if not last_interaction_id:
        speak("I do not have a recent learnable reply to rate yet.")
        return True

    if normalized in positive_commands:
        submit_response_feedback(last_interaction_id, "good", note=normalized, source="terminal")
        speak("Got it. I will treat that last reply as a good example.")
        return True

    submit_response_feedback(last_interaction_id, "bad", note=normalized, source="terminal")
    if not previous_user_text or not previous_reply:
        speak("Got it. I marked that last reply as unhelpful.")
        return True

    compact_reply = input_mode == "voice" and get_setting("assistant.compact_voice_replies", True)
    correction_prompt = (
        f"The user previously asked: {previous_user_text}\n"
        f"Your previous reply was: {previous_reply}\n"
        f"The user said that reply was wrong or not useful.\n"
        "Correct yourself now in natural English. Start with 'Let me correct that.' "
        "Answer the original user message directly. Do not mention earlier conversation history unless the user asked for it. "
        "Keep it accurate, calm, and concise."
    )
    try:
        corrected_reply = ask_ollama(correction_prompt, compact=compact_reply)
    except Exception:
        corrected_reply = "Let me correct that. I will avoid that reply pattern and try to answer more clearly next time."

    speak(corrected_reply)
    set_last_result(corrected_reply)
    _remember_terminal_learning_turn(previous_user_text, corrected_reply, route="terminal-self-correction", model="assistant")
    return True


def _semantic_memory_summary():
    return semantic_memory_status_summary()


def _semantic_memory_lookup_summary(query):
    return semantic_memory_search_summary(query, limit=3)


def _build_emergency_alert_message():
    location = _current_location_text()
    if location:
        return f"This is an emergency. My saved location is {location}. Please contact me immediately."
    return "This is an emergency. Please contact me immediately."


def _send_emergency_alert():
    location = _current_location_text()
    success, dispatch_reply = trigger_dual_emergency_protocol(location)
    if success:
        return f"Emergency activated. {dispatch_reply}"
    return dispatch_reply + " " + quick_whatsapp_message(f"message my emergency contact saying {_build_emergency_alert_message()}")


def _send_safe_alert():
    location = _current_location_text()
    message = "I am safe now."
    if location:
        message += f" My saved location is {location}."
    
    # Repurpose the dual protocol to say safe instead of emergency, but if it fails, fallback to WA
    # Note: For safe alerts, we are just using WA fallback logic to keep it simple, but we could make a send_custom_dispatch later.
    return quick_whatsapp_message(f"message my emergency contact saying {message}")


def _trigger_emergency_protocol():
    if is_face_enrolled():
        success, msg = verify_user_face()
        if not success:
            return "Emergency protocol aborted. Unauthorized face detected."

    location = _current_location_text()
    success, dispatch_reply = trigger_dual_emergency_protocol(location)
    
    parts = []
    if success:
        parts.append(f"Emergency activated via APIs: {dispatch_reply}.")
    else:
        parts.append("API Emergency failed, falling back to WhatsApp.")
        parts.append(_send_emergency_alert())
        
    if location:
        parts.append(f"Saved location: {location}.")
    parts.append("Emergency protocol started.")
    return " ".join(part for part in parts if part)


def _emergency_protocol_summary():
    return (
        "Emergency protocol will send an alert, include your saved location when available, "
        "and use your saved WhatsApp shortcut when it is available."
    )


def _share_saved_location():
    location = _current_location_text()
    if not location:
        return "I do not have your location saved yet."
    copied = _copy_to_clipboard(location)
    if copied:
        return f"Your saved location is {location}. I copied it to the clipboard too."
    return f"Your saved location is {location}."


def _share_saved_location_everywhere():
    location = _current_location_text()
    if not location:
        return "I do not have your location saved yet."
    return quick_whatsapp_message(
        f"message my emergency contact saying My saved location is {location}"
    )


def _call_emergency_contact():
    ensure_google_contacts_fresh(force=True)
    value, reply = get_named_contact_field("my emergency contact", "phone")
    if not value:
        return reply
    copied = _copy_to_clipboard(str(value))
    try:
        webbrowser.open(f"tel:{value}")
        _try_auto_confirm_phone_call()
        return reply + (" I copied the number to the clipboard too." if copied else "")
    except Exception:
        if copied:
            return reply + " I copied the number to the clipboard so you can call now."
        return reply


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
        "call him": "call him",
        "call her": "call her",
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

    normalized = re.sub(r"^open\s+open\s+(.+)$", r"open \1", normalized)
    normalized = re.sub(r"^start\s+start\s+(.+)$", r"start \1", normalized)
    normalized = re.sub(r"^launch\s+launch\s+(.+)$", r"launch \1", normalized)

    normalized = re.sub(r"^what(?:'s| is)\s+the\s+time(?:\s+now)?$", "what is the time now", normalized)
    normalized = re.sub(r"^what(?:'s| is)\s+the\s+date$", "what is the date", normalized)
    normalized = re.sub(r"^what(?:'s| is)\s+my\s+agenda$", "today agenda", normalized)
    normalized = re.sub(r"^show\s+me\s+my\s+agenda$", "today agenda", normalized)
    normalized = re.sub(r"^(.+?)\s+ku\s+call\s+pannu$", r"call \1", normalized)
    normalized = re.sub(r"^(.+?)\s+ku\s+phone\s+pannu$", r"call \1", normalized)
    normalized = re.sub(r"^(.+?)\s+ku\s+message\s+anupu\s+(.+)$", r"message \1 saying \2", normalized)
    normalized = re.sub(r"^(.+?)\s+ku\s+text\s+anupu\s+(.+)$", r"message \1 saying \2", normalized)
    normalized = re.sub(r"^(.+?)\s+ku\s+whatsapp\s+anupu\s+(.+)$", r"message \1 saying \2", normalized)
    normalized = re.sub(r"^(.+?)\s+ku\s+mail\s+podu\s+(.+)$", r"mail \1 about \2", normalized)
    normalized = re.sub(r"^(.+?)\s+ku\s+mail\s+anupu\s+(.+)$", r"mail \1 about \2", normalized)
    normalized = re.sub(r"^(.+?)\s+ku\s+email\s+anupu\s+(.+)$", r"mail \1 about \2", normalized)

    return normalized


def _remember_contact_context(contact_name, action_name):
    last_contact_context["name"] = (contact_name or "").strip()
    last_contact_context["action"] = (action_name or "").strip()


def _apply_contact_context(command):
    normalized = " ".join((command or "").strip().split())
    if not normalized:
        return normalized

    last_name = last_contact_context.get("name", "").strip()
    if not last_name:
        return normalized

    patterns = [
        (r"^(?:call)\s+(him|her|them)$", f"call {last_name}"),
        (r"^(?:message|text|whatsapp)\s+(him|her|them)\s+(?:saying|that)\s+(.+)$", f"message {last_name} saying " + r"\2"),
        (r"^(?:mail|email)\s+(him|her|them)\s+about\s+(.+)$", f"mail {last_name} about " + r"\2"),
        (r"^(?:mail|email)\s+(him|her|them)\s+(.+)$", f"mail {last_name} " + r"\2"),
    ]

    for pattern, replacement in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

    return normalized


def _split_multi_action_command(command):
    text = " ".join((command or "").strip().split())
    if not text:
        return []

    # Keep automation rule creation intact; it uses "when ... then ..." in one command.
    if re.match(r"^create\s+automation\s+.+\s+when\s+.+\s+then\s+.+$", text, flags=re.IGNORECASE):
        return []

    # Keep settings navigation actions intact (open/go to ... and search/click/find ...).
    if re.match(
        r"^(?:open|show|go to)\s+.+\s+and\s+(?:search|find|click)\s+.+$",
        text,
        flags=re.IGNORECASE,
    ):
        return []

    parts = [text]
    split_patterns = [
        r"\s+and then\s+",
        r"\s+then\s+",
        r"\s+and\s+",
    ]

    for pattern in split_patterns:
        candidate_parts = [segment.strip(" ,") for segment in re.split(pattern, text, flags=re.IGNORECASE) if segment.strip(" ,")]
        if len(candidate_parts) < 2:
            continue

        valid_starters = (
            "call ",
            "message ",
            "mail ",
            "email ",
            "send ",
            "save ",
            "make ",
            "create ",
            "add ",
            "set ",
            "remind ",
            "summarize ",
            "translate ",
            "extract ",
            "open ",
            "copy ",
            "search ",
            "read ",
            "preview ",
            "repeat",
            "what is ",
            "show ",
            "first one",
            "second one",
            "third one",
            "him ",
            "her ",
            "it ",
        )
        if all(any(segment.lower().startswith(starter) for starter in valid_starters) for segment in candidate_parts[1:]):
            parts = candidate_parts
            break

    return parts if len(parts) > 1 else []


def _continue_remaining_chain(remaining_chain, INSTALLED_APPS, input_mode):
    for index, next_command in enumerate(remaining_chain):
        process_command(next_command, INSTALLED_APPS, input_mode=input_mode)
        if pending_confirmation:
            pending_confirmation["remaining_chain"] = remaining_chain[index + 1 :]
            pending_confirmation.setdefault("chain_input_mode", input_mode)
            pending_confirmation.setdefault("chain_apps", INSTALLED_APPS)
            return


def _maybe_run_multi_action_chain(command, INSTALLED_APPS, input_mode):
    chain_parts = _split_multi_action_command(command)
    if not chain_parts:
        return False

    first_command = chain_parts[0]
    remaining_chain = chain_parts[1:]
    process_command(first_command, INSTALLED_APPS, input_mode=input_mode)

    if pending_confirmation:
        pending_confirmation["remaining_chain"] = remaining_chain
        pending_confirmation.setdefault("chain_input_mode", input_mode)
        pending_confirmation.setdefault("chain_apps", INSTALLED_APPS)
        return True

    _continue_remaining_chain(remaining_chain, INSTALLED_APPS, input_mode)
    return True


def _contact_confirmation_mode():
    return str(get_setting("google_contacts.confirmation_mode", "calls_only") or "calls_only").lower()


def _should_confirm_contact_action(action_kind):
    mode = _contact_confirmation_mode()
    if mode in {"off", "disabled", "direct"}:
        return False
    if mode == "all":
        return action_kind in {"call", "message", "mail"}
    return action_kind == "call"


def _is_positive_confirmation(command):
    normalized = " ".join((command or "").lower().strip().split())
    if not normalized:
        return False
    exact = {
        "yes",
        "yes da",
        "confirm",
        "confirm it",
        "ok",
        "okay",
        "okay da",
        "ok da",
        "do it",
        "proceed",
        "continue",
        "sure",
    }
    if normalized in exact:
        return True
    return (
        normalized.startswith("yes")
        or normalized.startswith("ok")
        or normalized.startswith("okay")
        or normalized.startswith("confirm")
        or normalized.startswith("do it")
    )


def _is_negative_confirmation(command):
    normalized = " ".join((command or "").lower().strip().split())
    if not normalized:
        return False
    exact = {
        "no",
        "no da",
        "cancel",
        "cancel it",
        "stop",
        "stop it",
        "never mind",
        "leave it",
        "dont",
        "don't",
        "nope",
    }
    if normalized in exact:
        return True
    return (
        normalized.startswith("no")
        or normalized.startswith("cancel")
        or normalized.startswith("stop")
        or normalized.startswith("never")
    )


def _resume_secured_command(state, INSTALLED_APPS, input_mode):
    original_command = state.get("command", "")
    if not original_command:
        speak("I could not find the secured command to continue.")
        return
    _set_security_bypass(original_command)
    process_command(original_command, INSTALLED_APPS, input_mode=state.get("input_mode", input_mode))


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


def _extract_contact_suggestions(reply):
    match = re.search(
        r"I found multiple Google contacts for .+?: (.+?)\. Say the exact name or set a contact alias\.",
        reply or "",
    )
    if not match:
        return []
    return [item.strip() for item in match.group(1).split("|") if item.strip()]


def _best_contact_display_name(target_text, force_refresh=False):
    if force_refresh:
        with contextlib.suppress(Exception):
            ensure_google_contacts_fresh(force=True)
    ranked = get_google_contact_matches(target_text, limit=1)
    if ranked:
        return ranked[0][0].get("display_name") or target_text
    return target_text


def _queue_contact_choice(kind, target, options, field=None, message_text=None, topic=None):
    global pending_confirmation
    pending_confirmation = {
        "type": "contact_choice",
        "kind": kind,
        "target": target,
        "field": field,
        "message_text": message_text,
        "topic": topic,
        "options": options,
    }
    option_text = " | ".join(f"{index + 1}. {name}" for index, name in enumerate(options[:3]))
    return (
        f"I found multiple contacts for {target}. "
        f"Say first one, second one, third one, or the exact name. {option_text}"
    )


def _resolve_contact_choice_command(command, options):
    normalized = " ".join((command or "").lower().strip().split())
    index_map = {
        "1": 0,
        "one": 0,
        "first": 0,
        "first one": 0,
        "2": 1,
        "two": 1,
        "second": 1,
        "second one": 1,
        "3": 2,
        "three": 2,
        "third": 2,
        "third one": 2,
    }
    if normalized in index_map and index_map[normalized] < len(options):
        return options[index_map[normalized]]
    for option in options:
        if normalized == " ".join(option.lower().split()):
            return option
    return None


def _execute_contact_choice(choice_state, selected_name):
    kind = choice_state.get("kind")
    if kind == "lookup":
        _value, reply = get_named_contact_field(selected_name, choice_state.get("field", "phone"))
        _remember_contact_context(selected_name, "lookup")
        return reply
    if kind == "call":
        ensure_google_contacts_fresh(force=True)
        value, reply = get_named_contact_field(selected_name, "phone")
        if not value:
            return reply
        _remember_contact_context(selected_name, "call")
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
    if kind == "message":
        _remember_contact_context(selected_name, "message")
        return quick_whatsapp_message(f"message {selected_name} saying {choice_state.get('message_text', '')}")
    if kind == "mail":
        _remember_contact_context(selected_name, "mail")
        return quick_email_shortcut(f"mail {selected_name} {choice_state.get('topic', '')}")
    return "I could not finish that contact choice right now."


def _queue_contact_choice_from_reply(command, reply):
    suggestions = _extract_contact_suggestions(reply)
    if not suggestions:
        return None

    clean_text = lambda value: " ".join((value or "").split())

    call_match = re.match(r"^call\s+(.+)$", command)
    if call_match:
        return _queue_contact_choice("call", call_match.group(1).strip(), suggestions)

    lookup_match = re.match(
        r"^what is\s+(.+?)\s+(email|mail|phone|mobile|number|whatsapp)$",
        command,
    )
    if lookup_match:
        return _queue_contact_choice(
            "lookup",
            lookup_match.group(1).strip(),
            suggestions,
            field=lookup_match.group(2).strip(),
        )

    message_match = re.match(r"^(?:message|whatsapp)\s+(.+?)\s+(?:saying|that)\s+(.+)$", command)
    if message_match:
        return _queue_contact_choice(
            "message",
            message_match.group(1).strip(),
            suggestions,
            message_text=clean_text(message_match.group(2)),
        )

    mail_match = re.match(r"^(?:mail|email)\s+(.+?)\s+about\s+(.+)$", command)
    if mail_match:
        return _queue_contact_choice(
            "mail",
            mail_match.group(1).strip(),
            suggestions,
            topic=clean_text(mail_match.group(2)),
        )

    quick_mail_match = re.match(r"^(?:mail|email)\s+(.+?)\s+(.+)$", command)
    if quick_mail_match:
        return _queue_contact_choice(
            "mail",
            quick_mail_match.group(1).strip(),
            suggestions,
            topic=clean_text(quick_mail_match.group(2)),
        )

    return None


def _extract_contact_intent(command):
    message_match = re.match(r"^(?:message|whatsapp)\s+(.+?)\s+(?:saying|that|about)\s+(.+)$", command)
    if message_match:
        return "message", message_match.group(1).strip(), " ".join(message_match.group(2).split())

    mail_match = re.match(r"^(?:mail|email)\s+(.+?)\s+about\s+(.+)$", command)
    if mail_match:
        return "mail", mail_match.group(1).strip(), " ".join(mail_match.group(2).split())

    quick_mail_match = re.match(r"^(?:mail|email)\s+(.+?)\s+(.+)$", command)
    if quick_mail_match:
        return "mail", quick_mail_match.group(1).strip(), " ".join(quick_mail_match.group(2).split())

    return None, None, None


def _maybe_confirm_contact_intent(command):
    global pending_confirmation
    action_kind, target, content = _extract_contact_intent(command)
    if not action_kind or not _should_confirm_contact_action(action_kind):
        return None

    display_target = _best_contact_display_name(target)

    if action_kind == "message":
        pending_confirmation = {
            "type": "contact_action_confirm",
            "kind": "message",
            "message": f"Should I message {display_target} now?",
            "action": lambda: (_remember_contact_context(target, "message") or quick_whatsapp_message(f"message {target} saying {content}")),
        }
        return pending_confirmation["message"]

    if action_kind == "mail":
        pending_confirmation = {
            "type": "contact_action_confirm",
            "kind": "mail",
            "message": f"Should I open a mail draft for {display_target}?",
            "action": lambda: (_remember_contact_context(target, "mail") or quick_email_shortcut(f"mail {target} {content}")),
        }
        return pending_confirmation["message"]

    return None


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
        ensure_google_contacts_fresh(force=True)
        value, reply = get_named_contact_field(target, field)
        if not value:
            return reply
        if _copy_to_clipboard(str(value)):
            return f"{reply} I copied it to the clipboard."
        return reply

    call_match = re.match(r"^call\s+(.+)$", command)
    if call_match:
        target = call_match.group(1).strip()
        with contextlib.suppress(Exception):
            ensure_google_contacts_fresh(force=True)
        if _should_confirm_contact_action("call"):
            global pending_confirmation
            pending_confirmation = {
                "type": "contact_action_confirm",
                "kind": "call",
                "message": f"Should I call {_best_contact_display_name(target, force_refresh=False)}?",
                "action": lambda: _execute_contact_choice({"kind": "call"}, target),
            }
            return pending_confirmation["message"]
        ensure_google_contacts_fresh(force=True)
        value, reply = get_named_contact_field(target, "phone")
        if not value:
            suggestions = _extract_contact_suggestions(reply)
            if suggestions:
                return _queue_contact_choice("call", target, suggestions)
            return reply
        _remember_contact_context(target, "call")
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

    if command in ["show google contact changes", "google contact changes", "recent contact changes"]:
        return get_recent_contact_change_summary()

    if command in ["list favorite contacts", "show favorite contacts"]:
        return list_favorite_contacts()

    favorite_match = re.match(r"^(?:favorite|pin)\s+contact\s+(.+)$", command)
    if favorite_match:
        return add_favorite_contact(favorite_match.group(1).strip())[1]

    unfavorite_match = re.match(r"^(?:unfavorite|remove favorite|unpin)\s+contact\s+(.+)$", command)
    if unfavorite_match:
        return remove_favorite_contact(unfavorite_match.group(1).strip())[1]

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
    ensure_google_contacts_fresh(force=True)
    value, reply = get_named_contact_field(contact_name, field_name)
    suggestions = _extract_contact_suggestions(reply)
    if suggestions:
        return _queue_contact_choice("lookup", contact_name, suggestions, field=field_name)
    if value:
        _remember_contact_context(contact_name, "lookup")
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

    if command in ["enable google contacts live refresh", "enable live contact refresh"]:
        update_setting("google_contacts.live_refresh_enabled", True)
        return "Google Contacts live refresh enabled."

    if command in ["disable google contacts live refresh", "disable live contact refresh"]:
        update_setting("google_contacts.live_refresh_enabled", False)
        return "Google Contacts live refresh disabled."

    google_live_refresh_match = re.match(
        r"^(?:set|change|update)\s+google contacts live refresh(?: interval)?\s+to\s+(\d+(?:\.\d+)?)$",
        command,
    )
    if google_live_refresh_match:
        minutes = max(0.1, float(google_live_refresh_match.group(1)))
        update_setting("google_contacts.live_refresh_minutes", minutes)
        if minutes == int(minutes):
            minutes = int(minutes)
        return f"Google Contacts live refresh interval updated to {minutes} minutes."

    if command in ["enable google contact change popup", "enable contact change popup"]:
        update_setting("google_contacts.change_popup_enabled", True)
        return "Google contact change popup enabled."

    if command in ["disable google contact change popup", "disable contact change popup"]:
        update_setting("google_contacts.change_popup_enabled", False)
        return "Google contact change popup disabled."

    if command in ["enable contact confirmation", "enable call confirmation"]:
        update_setting("google_contacts.confirmation_mode", "calls_only")
        return "Contact confirmation enabled for calls."

    if command in ["enable full contact confirmation", "confirm all contact actions"]:
        update_setting("google_contacts.confirmation_mode", "all")
        return "Contact confirmation enabled for calls, messages, and mails."

    if command in ["disable contact confirmation", "disable call confirmation"]:
        update_setting("google_contacts.confirmation_mode", "off")
        return "Contact confirmation disabled."

    wake_word_match = re.match(r"^(?:set|change|update)\s+wake word\s+to\s+(.+)$", command)
    if wake_word_match:
        new_wake_word = wake_word_match.group(1).strip().strip("\"'")
        if not new_wake_word:
            return "Tell me the new wake word."
        update_setting("wake_word", new_wake_word)
        return f"Wake word updated to {new_wake_word}. Restart the assistant to use the new wake word."

    initial_timeout_match = re.match(
        r"^(?:set|change|update)\s+initial timeout\s+to\s+(\d+)(?:\s+(?:second|seconds|sec|secs|s))?$",
        command,
    )
    if initial_timeout_match:
        timeout_value = int(initial_timeout_match.group(1))
        update_setting("initial_timeout", timeout_value)
        return f"Initial timeout updated to {timeout_value} seconds."

    active_timeout_match = re.match(
        r"^(?:set|change|update)\s+active timeout\s+to\s+(\d+)(?:\s+(?:second|seconds|sec|secs|s))?$",
        command,
    )
    if active_timeout_match:
        timeout_value = int(active_timeout_match.group(1))
        update_setting("active_timeout", timeout_value)
        return f"Active timeout updated to {timeout_value} seconds."

    wake_pause_match = re.match(
        r"^(?:set|change|update)\s+post wake pause\s+to\s+(\d+(?:\.\d+)?)(?:\s+(?:second|seconds|sec|secs|s))?$",
        command,
    )
    if wake_pause_match:
        pause_value = max(0.1, float(wake_pause_match.group(1)))
        update_setting("voice.post_wake_pause_seconds", pause_value)
        return f"Post wake pause updated to {pause_value} seconds."

    backoff_match = re.match(
        r"^(?:set|change|update)\s+empty listen backoff\s+to\s+(\d+(?:\.\d+)?)(?:\s+(?:second|seconds|sec|secs|s))?$",
        command,
    )
    if backoff_match:
        backoff_value = max(0.0, float(backoff_match.group(1)))
        update_setting("voice.empty_listen_backoff_seconds", backoff_value)
        return f"Empty listen backoff updated to {backoff_value} seconds."

    wake_timeout_match = re.match(
        r"^(?:set|change|update)\s+wake listen timeout\s+to\s+(\d+(?:\.\d+)?)(?:\s+(?:second|seconds|sec|secs|s))?$",
        command,
    )
    if wake_timeout_match:
        timeout_value = max(1.0, float(wake_timeout_match.group(1)))
        update_setting("voice.wake_listen_timeout", timeout_value)
        return f"Wake listen timeout updated to {timeout_value} seconds."

    wake_phrase_match = re.match(
        r"^(?:set|change|update)\s+wake phrase time limit\s+to\s+(\d+(?:\.\d+)?)(?:\s+(?:second|seconds|sec|secs|s))?$",
        command,
    )
    if wake_phrase_match:
        phrase_value = max(1.0, float(wake_phrase_match.group(1)))
        update_setting("voice.wake_phrase_time_limit", phrase_value)
        return f"Wake phrase time limit updated to {phrase_value} seconds."

    wake_threshold_match = re.match(
        r"^(?:set|change|update)\s+wake(?:\s+match)?\s+threshold\s+to\s+(.+)$",
        command,
    )
    if wake_threshold_match:
        raw_value = wake_threshold_match.group(1).strip()
        is_percent = raw_value.endswith("%")
        raw_number = raw_value[:-1].strip() if is_percent else raw_value
        try:
            parsed_value = float(raw_number)
        except ValueError:
            return "Wake threshold should be a number between 0.4 and 1.0."
        threshold_value = parsed_value / 100.0 if is_percent else parsed_value
        threshold_value = min(1.0, max(0.4, threshold_value))
        update_setting("voice.wake_match_threshold", threshold_value)
        return f"Wake match threshold updated to {threshold_value}."

    wake_prefix_match = re.match(
        r"^(?:set|change|update)\s+wake\s+prefix\s+words\s+to\s+(\d+)$",
        command,
    )
    if wake_prefix_match:
        prefix_words = max(0, min(4, int(wake_prefix_match.group(1))))
        update_setting("voice.wake_max_prefix_words", prefix_words)
        return f"Wake prefix window updated to {prefix_words} words."

    if command in ["enable strict wake word", "enable strict wake detection", "turn on strict wake word"]:
        update_setting("voice.wake_requires_prefix", True)
        return "Strict wake word detection enabled."

    if command in ["disable strict wake word", "disable strict wake detection", "turn off strict wake word"]:
        update_setting("voice.wake_requires_prefix", False)
        return "Strict wake word detection disabled."

    wake_retry_match = re.match(
        r"^(?:set|change|update)\s+wake retry window\s+to\s+(\d+(?:\.\d+)?)(?:\s+(?:second|seconds|sec|secs|s))?$",
        command,
    )
    if wake_retry_match:
        retry_value = max(1.0, float(wake_retry_match.group(1)))
        update_setting("voice.wake_retry_window_seconds", retry_value)
        return f"Wake retry window updated to {retry_value} seconds."

    follow_up_timeout_match = re.match(
        r"^(?:set|change|update)\s+follow up timeout\s+to\s+(\d+(?:\.\d+)?)(?:\s+(?:second|seconds|sec|secs|s))?$",
        command,
    )
    if follow_up_timeout_match:
        timeout_value = max(3.0, float(follow_up_timeout_match.group(1)))
        update_setting("voice.follow_up_timeout_seconds", timeout_value)
        return f"Follow up timeout updated to {timeout_value} seconds."

    follow_up_keep_alive_match = re.match(
        r"^(?:set|change|update)\s+follow up keep alive\s+to\s+(\d+(?:\.\d+)?)(?:\s+(?:second|seconds|sec|secs|s))?$",
        command,
    )
    if follow_up_keep_alive_match:
        timeout_value = max(3.0, float(follow_up_keep_alive_match.group(1)))
        update_setting("voice.follow_up_keep_alive_seconds", timeout_value)
        return f"Follow up keep alive updated to {timeout_value} seconds."

    if command in ["enable continuous conversation", "turn on continuous conversation"]:
        update_setting("voice.continuous_conversation_enabled", True)
        return "Continuous conversation enabled."

    if command in ["disable continuous conversation", "turn off continuous conversation"]:
        update_setting("voice.continuous_conversation_enabled", False)
        return "Continuous conversation disabled."

    follow_up_listen_timeout_match = re.match(
        r"^(?:set|change|update)\s+follow up listen timeout\s+to\s+(\d+(?:\.\d+)?)(?:\s+(?:second|seconds|sec|secs|s))?$",
        command,
    )
    if follow_up_listen_timeout_match:
        timeout_value = max(1.0, float(follow_up_listen_timeout_match.group(1)))
        update_setting("voice.follow_up_listen_timeout", timeout_value)
        return f"Follow up listen timeout updated to {timeout_value} seconds."

    follow_up_phrase_limit_match = re.match(
        r"^(?:set|change|update)\s+follow up phrase(?:\s+time)?\s+limit\s+to\s+(\d+(?:\.\d+)?)(?:\s+(?:second|seconds|sec|secs|s))?$",
        command,
    )
    if follow_up_phrase_limit_match:
        phrase_value = max(1.0, float(follow_up_phrase_limit_match.group(1)))
        update_setting("voice.follow_up_phrase_time_limit", phrase_value)
        return f"Follow up phrase time limit updated to {phrase_value} seconds."

    interrupt_follow_up_match = re.match(
        r"^(?:set|change|update)\s+interrupt follow up(?:\s+window)?\s+to\s+(\d+(?:\.\d+)?)(?:\s+(?:second|seconds|sec|secs|s))?$",
        command,
    )
    if interrupt_follow_up_match:
        seconds_value = max(2.0, float(interrupt_follow_up_match.group(1)))
        update_setting("voice.interrupt_follow_up_seconds", seconds_value)
        return f"Interrupt follow up window updated to {seconds_value} seconds."

    if command in [
        "enable wake direct fallback",
        "turn on wake direct fallback",
        "enable wake fallback",
        "turn on wake fallback",
    ]:
        update_setting("voice.wake_direct_fallback_enabled", True)
        return "Wake direct fallback enabled."

    if command in [
        "disable wake direct fallback",
        "turn off wake direct fallback",
        "disable wake fallback",
        "turn off wake fallback",
    ]:
        update_setting("voice.wake_direct_fallback_enabled", False)
        return "Wake direct fallback disabled."

    if command in [
        "enable voice desktop popup",
        "turn on voice desktop popup",
        "enable voice popup",
        "turn on voice popup",
        "enable voice wake popup",
        "turn on voice wake popup",
    ]:
        update_setting("voice.desktop_popup_enabled", True)
        return "Voice desktop popup enabled."

    if command in [
        "disable voice desktop popup",
        "turn off voice desktop popup",
        "disable voice popup",
        "turn off voice popup",
        "disable voice wake popup",
        "turn off voice wake popup",
    ]:
        update_setting("voice.desktop_popup_enabled", False)
        return "Voice desktop popup disabled."

    if command in [
        "enable voice desktop chime",
        "turn on voice desktop chime",
        "enable voice chime",
        "turn on voice chime",
        "enable wake chime",
        "turn on wake chime",
    ]:
        update_setting("voice.desktop_chime_enabled", True)
        return "Voice desktop chime enabled."

    if command in [
        "disable voice desktop chime",
        "turn off voice desktop chime",
        "disable voice chime",
        "turn off voice chime",
        "disable wake chime",
        "turn off wake chime",
    ]:
        update_setting("voice.desktop_chime_enabled", False)
        return "Voice desktop chime disabled."

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

    if command in [
        "enable full control mode",
        "enable full settings access",
        "full settings access",
        "full control mode",
        "run as administrator",
        "start admin mode",
        "admin mode on",
    ]:
        return relaunch_assistant_as_admin()

    if re.search(
        r"\b(?:enable|start|turn on|switch on|give|take|get)\b.*\b(?:full\s+)?(?:settings|system)\s+(?:access|acces|control|mode)\b",
        command,
    ):
        return relaunch_assistant_as_admin()

    if re.search(
        r"\b(?:enable|start|turn on|switch on)\b.*\b(?:admin|administrator)\b.*\b(?:mode|access|control)\b",
        command,
    ):
        return relaunch_assistant_as_admin()

    if re.search(r"\bfull\s+(?:settings|system)\s+(?:access|acces|control|mode)\b", command):
        return relaunch_assistant_as_admin()

    if command in [
        "admin status",
        "administrator status",
        "full control status",
        "settings access status",
    ] or (("admin" in command or "administrator" in command) and "status" in command):
        return (
            "Administrator mode is enabled. Full settings controls should work."
            if is_running_as_admin()
            else "Administrator mode is not enabled. Say enable full control mode."
        )

    if command in ["show settings", "show config", "settings"]:
        wake_word = get_setting("wake_word", "hey grandpa")
        tray_mode = get_setting("startup.tray_mode", False)
        interface_mode = str(get_setting("startup.interface_mode", "terminal") or "terminal").lower()
        terminal_input_mode = str(get_setting("startup.terminal_input_mode", "text") or "text").lower()
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
        follow_up_listen_timeout = get_setting("voice.follow_up_listen_timeout", 3)
        follow_up_phrase_limit = get_setting("voice.follow_up_phrase_time_limit", 5)
        wake_match_threshold = get_setting("voice.wake_match_threshold", 0.68)
        wake_retry_window = get_setting("voice.wake_retry_window_seconds", 6)
        interrupt_follow_up = get_setting("voice.interrupt_follow_up_seconds", 5)
        voice_popup_enabled = get_setting("voice.desktop_popup_enabled", True)
        voice_chime_enabled = get_setting("voice.desktop_chime_enabled", True)
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
        chatgpt_mode_full = get_setting("assistant.chatgpt_mode_full", False)
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
            f"Follow up listen timeout is {follow_up_listen_timeout} seconds. "
            f"Follow up phrase time limit is {follow_up_phrase_limit} seconds. "
            f"Wake match threshold is {wake_match_threshold}. "
            f"Wake retry window is {wake_retry_window} seconds. "
            f"Interrupt follow up window is {interrupt_follow_up} seconds. "
            f"Voice desktop popup is {'on' if voice_popup_enabled else 'off'}. "
            f"Voice desktop chime is {'on' if voice_chime_enabled else 'off'}. "
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
            f"Interface mode is {interface_mode}. "
            f"Terminal input mode is {terminal_input_mode}. "
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
            f"ChatGPT mode full is {'on' if chatgpt_mode_full else 'off'}. "
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
        refresh_startup_auto_launch()
        return "Tray startup enabled."

    if command in ["disable tray startup", "turn off tray startup"]:
        update_setting("startup.tray_mode", False)
        refresh_startup_auto_launch()
        return "Tray startup disabled."

    if command in [
        "enable terminal mode",
        "use terminal mode",
        "terminal mode on",
        "disable ui mode",
        "ui off",
        "no ui mode",
    ]:
        update_setting("startup.interface_mode", "terminal")
        return "Terminal mode enabled. Restart assistant to run without UI."

    if command in [
        "enable ui mode",
        "use ui mode",
        "ui mode on",
        "terminal mode off",
    ]:
        update_setting("startup.interface_mode", "ui")
        return "UI mode enabled. Restart assistant to open UI on startup."

    if command in [
        "set terminal input mode to text",
        "terminal input text",
        "text terminal mode",
    ]:
        update_setting("startup.terminal_input_mode", "text")
        return "Terminal input mode set to text."

    if command in [
        "set terminal input mode to voice",
        "terminal input voice",
        "voice terminal mode",
    ]:
        update_setting("startup.terminal_input_mode", "voice")
        return "Terminal input mode set to voice."

    if command in [
        "interface mode status",
        "startup interface status",
        "terminal mode status",
    ]:
        interface_mode = str(get_setting("startup.interface_mode", "terminal") or "terminal").lower()
        terminal_input_mode = str(get_setting("startup.terminal_input_mode", "text") or "text").lower()
        return (
            f"Interface mode is {interface_mode}. "
            f"Terminal input mode is {terminal_input_mode}."
        )

    if command in [
        "enable assistant startup",
        "enable startup launch",
        "turn on assistant startup",
        "launch assistant on startup",
    ]:
        return enable_startup_auto_launch()

    if command in [
        "disable assistant startup",
        "disable startup launch",
        "turn off assistant startup",
    ]:
        return disable_startup_auto_launch()

    if command in [
        "assistant startup status",
        "startup launch status",
        "auto launch status",
    ]:
        return startup_auto_launch_status()

    if command in [
        "open react ui",
        "open react browser ui",
        "open web ui",
    ]:
        _ok, reply = open_react_browser_ui()
        return reply

    if command in [
        "open react desktop",
        "open desktop shell",
        "open react desktop ui",
    ]:
        _ok, reply = open_react_desktop_ui()
        return reply

    if command in [
        "tray react status",
        "react tray status",
    ]:
        return tray_react_status()

    if command in [
        "enable tray react ui",
        "enable react ui on tray startup",
    ]:
        update_setting("startup.react_ui_on_tray_enabled", True)
        return "Tray React UI launch enabled."

    if command in [
        "disable tray react ui",
        "disable react ui on tray startup",
    ]:
        update_setting("startup.react_ui_on_tray_enabled", False)
        return "Tray React UI launch disabled."

    if command in [
        "set tray react mode to browser",
        "set react tray mode to browser",
    ]:
        update_setting("startup.react_ui_on_tray_mode", "browser")
        return "Tray React UI mode set to browser."

    if command in [
        "set tray react mode to desktop",
        "set react tray mode to desktop",
    ]:
        update_setting("startup.react_ui_on_tray_mode", "desktop")
        return "Tray React UI mode set to desktop."

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

    if command in [
        "chatgpt mode full",
        "enable chatgpt mode",
        "enable chatgpt mode full",
        "turn on chatgpt mode",
        "turn on chatgpt mode full",
        "full chatgpt mode",
    ]:
        update_setting("assistant.chatgpt_mode_full", True)
        update_setting("assistant.persona", "casual")
        return "ChatGPT mode full is enabled."

    if command in [
        "disable chatgpt mode",
        "disable chatgpt mode full",
        "turn off chatgpt mode",
        "turn off chatgpt mode full",
    ]:
        update_setting("assistant.chatgpt_mode_full", False)
        return "ChatGPT mode full is disabled."

    if command in [
        "chatgpt mode status",
        "chatgpt full mode status",
        "is chatgpt mode on",
    ]:
        enabled = bool(get_setting("assistant.chatgpt_mode_full", False))
        return f"ChatGPT mode full is {'on' if enabled else 'off'}."

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

    if command in [
        "casual mode",
        "set persona to casual",
        "change persona to casual",
        "friendly casual mode",
    ]:
        update_setting("assistant.persona", "casual")
        return "Persona mode changed to Casual."

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
        "enable easy wake mode",
        "turn on easy wake mode",
        "easy wake mode",
        "make wake easier",
        "make wake word easier",
    ]:
        enable_easy_wake_mode()
        return (
            "Easy wake mode enabled. Wake detection should be easier now. "
            "It may react a little more often to nearby speech."
        )

    if command in [
        "disable easy wake mode",
        "turn off easy wake mode",
        "normal wake mode",
        "make wake stricter",
    ]:
        apply_voice_profile("sensitive")
        update_setting("voice.wake_match_threshold", 0.64)
        update_setting("voice.wake_requires_prefix", True)
        update_setting("voice.wake_max_prefix_words", 2)
        update_setting("voice.wake_retry_window_seconds", 6)
        return "Easy wake mode disabled. Wake detection is back to the normal stricter profile."

    if command in [
        "set voice mode to normal",
        "enable normal voice mode",
        "turn on normal voice mode",
    ]:
        apply_voice_profile("normal")
        return "Voice mode changed to normal."

    voice_backend_match = re.match(
        r"^(?:set|change|use|switch\s+to)\s+(?:voice|speech|stt)(?:\s+input)?\s*(?:backend|engine|mode)?\s*(?:to\s+)?(auto|google|whisper)$",
        command,
    )
    if voice_backend_match:
        selected_backend = voice_backend_match.group(1).strip()
        if set_stt_backend(selected_backend):
            return f"Speech input backend set to {selected_backend}."
        return "I could not change the speech input backend."

    if command in [
        "voice backend status",
        "speech backend status",
        "stt status",
        "speech input status",
        "voice input backend",
    ]:
        return stt_backend_status_summary()

    if command in [
        "enable clap wake",
        "turn on clap wake",
        "enable double clap wake",
        "turn on double clap wake",
    ]:
        set_clap_wake_enabled(True)
        return "Double clap wake enabled. Clap twice to wake the assistant."

    if command in [
        "disable clap wake",
        "turn off clap wake",
        "disable double clap wake",
        "turn off double clap wake",
    ]:
        set_clap_wake_enabled(False)
        return "Double clap wake disabled."

    if command in [
        "clap wake status",
        "double clap status",
        "double clap wake status",
    ]:
        return clap_wake_status_summary()

    tts_backend_match = re.match(
        r"^(?:set|change|use|switch\s+to)\s+(?:voice|speech|tts)(?:\s+output)?\s*(?:backend|engine|mode)?\s*(?:to\s+)?(auto|sapi|pyttsx3|piper|coqui)$",
        command,
    )
    if tts_backend_match:
        selected_backend = tts_backend_match.group(1).strip()
        if set_tts_backend(selected_backend):
            return f"Speech output backend set to {selected_backend}."
        return "I could not change the speech output backend."

    if command in [
        "tts backend status",
        "speech output status",
        "voice output status",
        "tts status",
        "voice output backend",
    ]:
        return tts_backend_status_summary()

    custom_voice_sample_match = re.match(
        r"^(?:set|change|update|use)\s+(?:my|own|custom|cloned)\s+voice\s+sample\s+(?:path\s+)?(?:to\s+)?(.+)$",
        command,
    )
    if custom_voice_sample_match:
        return set_custom_voice_sample_path(custom_voice_sample_match.group(1).strip())[1]

    if command in [
        "clear my voice sample",
        "remove my voice sample",
        "reset my voice sample",
        "clear custom voice sample",
    ]:
        return clear_custom_voice_sample_path()[1]

    if command in [
        "my voice status",
        "own voice status",
        "custom voice status",
        "voice clone status",
        "cloned voice status",
    ]:
        return custom_voice_status_summary()

    if command in [
        "my voice license status",
        "custom voice license status",
        "voice license status",
        "coqui license status",
    ]:
        return custom_voice_license_status_summary()

    if command in [
        "list my voice samples",
        "list custom voice samples",
        "show custom voice samples",
        "available custom voice samples",
    ]:
        return list_custom_voice_samples_summary()

    choose_custom_voice_match = re.match(
        r"^(?:use|choose|select|set)\s+(?:my|own|custom|cloned)\s+voice\s+sample\s+(?:to\s+)?(.+)$",
        command,
    )
    if choose_custom_voice_match:
        return choose_custom_voice_sample_summary(choose_custom_voice_match.group(1).strip())

    if command in [
        "auto configure my voice",
        "autoconfigure my voice",
        "detect my voice sample",
        "auto configure custom voice",
    ]:
        return autoconfigure_custom_voice_sample()[1]

    if command in [
        "use my voice",
        "switch to my voice",
        "use own voice",
        "use custom voice",
        "switch to custom voice",
        "use cloned voice",
    ]:
        return prefer_custom_voice_backend()[1]

    if command in [
        "accept my voice license",
        "accept custom voice license",
        "accept coqui license",
        "agree to my voice license",
        "agree to coqui license",
    ]:
        return accept_custom_voice_license()[1]

    piper_model_match = re.match(
        r"^(?:set|change|update)\s+piper\s+(?:voice\s+)?model\s+(?:path\s+)?to\s+(.+)$",
        command,
    )
    if piper_model_match:
        return set_piper_model_path(piper_model_match.group(1).strip())[1]

    if command in ["clear piper model path", "remove piper model path", "reset piper model path"]:
        return clear_piper_model_path()[1]

    piper_config_match = re.match(
        r"^(?:set|change|update)\s+piper\s+config\s+(?:path\s+)?to\s+(.+)$",
        command,
    )
    if piper_config_match:
        return set_piper_config_path(piper_config_match.group(1).strip())[1]

    if command in ["clear piper config path", "remove piper config path", "reset piper config path"]:
        return clear_piper_config_path()[1]

    return None


# ---------------- PROCESS COMMAND ----------------
def process_command(command, INSTALLED_APPS, input_mode="text"):
    global mouse_stop_event, mouse_stop_requested_by_command
    global object_detection_stop_event, object_detection_stop_requested_by_command
    global pending_confirmation

    command = _normalize_voice_friendly_command(command)
    command = _apply_contact_context(command)
    if not pending_confirmation and _maybe_run_multi_action_chain(command, INSTALLED_APPS, input_mode):
        return
    if command and _handle_learning_feedback_command(command, input_mode=input_mode):
        return
    if command:
        set_last_user_input(command)
        remember_emotion_signal(command)
        log_command(command, source=input_mode)

    if pending_confirmation and pending_confirmation.get("type") == "contact_choice":
        selected_name = _resolve_contact_choice_command(
            command, pending_confirmation.get("options", [])
        )
        if selected_name:
            choice_state = pending_confirmation
            pending_confirmation = None
            reply = _execute_contact_choice(choice_state, selected_name)
            speak(reply)
            set_last_result(reply)
            remaining_chain = choice_state.get("remaining_chain", [])
            if remaining_chain:
                _continue_remaining_chain(
                    remaining_chain,
                    choice_state.get("chain_apps", INSTALLED_APPS),
                    choice_state.get("chain_input_mode", input_mode),
                )
            return

    if pending_confirmation and pending_confirmation.get("type") == "contact_action_confirm":
        if _is_positive_confirmation(command):
            confirmation_state = pending_confirmation
            action = confirmation_state["action"]
            pending_confirmation = None
            reply = action()
            speak(reply)
            set_last_result(reply)
            remaining_chain = confirmation_state.get("remaining_chain", [])
            if remaining_chain:
                _continue_remaining_chain(
                    remaining_chain,
                    confirmation_state.get("chain_apps", INSTALLED_APPS),
                    confirmation_state.get("chain_input_mode", input_mode),
                )
            return
        if _is_negative_confirmation(command):
            pending_confirmation = None
            speak("Cancelled.")
            return

    if pending_confirmation and pending_confirmation.get("type") == "security_confirmation":
        if _is_positive_confirmation(command):
            confirmation_state = pending_confirmation
            pending_confirmation = None
            _resume_secured_command(confirmation_state, INSTALLED_APPS, input_mode)
            return
        if _is_negative_confirmation(command):
            pending_confirmation = None
            speak("Cancelled.")
            return

    if pending_confirmation and pending_confirmation.get("type") == "security_auth":
        if _is_negative_confirmation(command):
            pending_confirmation = None
            speak("Cancelled.")
            return

        pin_auth_match = re.match(r"^(?:security\s+pin|pin|verify\s+pin|unlock\s+with\s+pin)\s+(.+)$", command)
        if pin_auth_match:
            auth_state = pending_confirmation
            success, reply = verify_security_pin(pin_auth_match.group(1).strip(), admin=bool(auth_state.get("admin")))
            if success:
                pending_confirmation = None
                speak(reply)
                _resume_secured_command(auth_state, INSTALLED_APPS, input_mode)
            else:
                speak(reply)
            return

    if command and not _consume_security_bypass(command):
        security_decision = validate_command(command, source=f"command-{input_mode}")
        if not security_decision.get("allowed", True):
            action = security_decision.get("action", "block")
            if action == "confirm":
                pending_confirmation = {
                    "type": "security_confirmation",
                    "message": security_decision.get("message", "Please confirm."),
                    "command": command,
                    "input_mode": input_mode,
                }
                speak(pending_confirmation["message"])
                return
            if action == "authenticate":
                pending_confirmation = {
                    "type": "security_auth",
                    "message": security_decision.get("message", "Authentication required."),
                    "command": command,
                    "input_mode": input_mode,
                    "admin": bool(security_decision.get("permission", {}).get("requires_admin_mode")),
                }
                speak(pending_confirmation["message"])
                return
            speak(security_decision.get("message", "That command was blocked for security reasons."))
            return

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

    if command in ["enable offline mode", "turn on offline mode", "offline mode on"]:
        update_setting("assistant.offline_mode_enabled", True)
        speak("Offline core mode enabled.")
        return

    if command in ["disable offline mode", "turn off offline mode", "offline mode off"]:
        update_setting("assistant.offline_mode_enabled", False)
        speak("Offline core mode disabled.")
        return

    if command in ["offline mode status", "is offline mode on", "what works offline"]:
        enabled = get_setting("assistant.offline_mode_enabled", False)
        prefix = "Offline core mode is enabled. " if enabled else "Offline core mode is disabled. "
        speak(prefix + _offline_mode_summary())
        return

    if command in ["offline help", "offline quick help", "offline commands"]:
        speak(_offline_quick_help())
        return

    if command in ["offline ai status", "local ai status", "is local ai ready"]:
        offline_mode = get_setting("assistant.offline_mode_enabled", False)
        model_name = get_setting("assistant.model", "phi3")
        if offline_mode:
            speak(
                f"Offline mode is enabled. Local AI fallback is ready. Preferred local model is {model_name} when available."
            )
        else:
            speak(
                f"Offline mode is disabled. Preferred local model is {model_name}. If the local AI server is unavailable, responses may be limited."
            )
        return

    if command in ["enable developer mode", "turn on developer mode", "developer mode on"]:
        update_setting("assistant.developer_mode_enabled", True)
        speak("Developer mode enabled.")
        return

    if command in ["disable developer mode", "turn off developer mode", "developer mode off"]:
        update_setting("assistant.developer_mode_enabled", False)
        speak("Developer mode disabled.")
        return

    if command in ["developer mode status", "what is developer mode", "developer help"]:
        enabled = get_setting("assistant.developer_mode_enabled", False)
        prefix = "Developer mode is enabled. " if enabled else "Developer mode is disabled. "
        speak(prefix + _developer_mode_summary())
        return

    if command in ["enable focus mode", "turn on focus mode", "focus mode on"]:
        update_setting("assistant.focus_mode_enabled", True)
        speak("Focus mode enabled. Proactive notifications are now silenced.")
        return

    if command in ["disable focus mode", "turn off focus mode", "focus mode off"]:
        update_setting("assistant.focus_mode_enabled", False)
        speak("Focus mode disabled. Proactive notifications will resume.")
        return

    if command in ["focus mode status", "is focus mode on"]:
        enabled = get_setting("assistant.focus_mode_enabled", False)
        status = "enabled" if enabled else "disabled"
        speak(f"Focus mode is currently {status}.")
        return

    if command in [
        "planner focus",
        "planner focus summary",
        "today focus suggestions",
        "focus suggestions",
        "what should i focus on today",
    ]:
        snapshot = get_planner_focus_snapshot(limit=4)
        summary = snapshot.get("summary") or "Planner summary unavailable."
        suggestion_lines = [
            item.get("label")
            for item in snapshot.get("focus_suggestions", [])
            if isinstance(item, dict) and item.get("label")
        ]
        if suggestion_lines:
            speak(summary + " Suggestions: " + " | ".join(suggestion_lines[:4]))
        else:
            speak(summary)
        return

    if command in [
        "reminder timeline",
        "today reminder timeline",
        "upcoming reminder timeline",
    ]:
        snapshot = get_planner_focus_snapshot(limit=4)
        timeline = snapshot.get("reminder_timeline", {})
        overdue = timeline.get("overdue") or []
        due_today = timeline.get("today") or []
        upcoming = timeline.get("upcoming") or []
        parts = []
        if overdue:
            parts.append("Overdue: " + " | ".join(overdue[:3]))
        if due_today:
            parts.append("Today: " + " | ".join(due_today[:3]))
        if upcoming:
            parts.append("Upcoming: " + " | ".join(upcoming[:3]))
        if not parts:
            speak("Your reminder timeline is clear right now.")
        else:
            speak("Reminder timeline: " + " || ".join(parts))
        return

    if command in [
        "ai day plan",
        "generate ai day plan",
        "day plan with ai",
        "smart day planner",
    ]:
        plan = generate_ai_day_plan()
        summary = plan.get("summary") or "AI day plan generated."
        blocks = []
        for item in plan.get("blocks", [])[:4]:
            title = str(item.get("title") or "Task").strip()
            start = str(item.get("start") or "").strip()
            end = str(item.get("end") or "").strip()
            if start and end:
                blocks.append(f"{start}-{end} {title}")
            elif start:
                blocks.append(f"{start} {title}")
            else:
                blocks.append(title)
        if blocks:
            speak(summary + " Blocks: " + " | ".join(blocks))
        else:
            speak(summary)
        return

    add_habit_match = re.match(r"^(?:add|create)\s+habit\s+(.+)$", command)
    if add_habit_match:
        speak(add_habit(add_habit_match.group(1).strip()))
        return

    habit_check_in_match = re.match(
        r"^(?:check\s*in|checkin|mark|complete)\s+habit\s+(.+?)(?:\s+done)?$",
        command,
    )
    if habit_check_in_match:
        speak(check_in_habit(habit_check_in_match.group(1).strip()))
        return

    if command in [
        "habit dashboard",
        "habit summary",
        "show habit dashboard",
        "habit status",
    ]:
        speak(habit_dashboard_summary())
        return

    add_goal_match = re.match(r"^(?:add|create)\s+goal\s+(.+)$", command)
    if add_goal_match:
        speak(create_goal(add_goal_match.group(1).strip()))
        return

    add_goal_milestone_match = re.match(
        r"^(?:add|create)\s+milestone\s+(.+?)\s+to\s+goal\s+(.+)$",
        command,
    )
    if add_goal_milestone_match:
        milestone_title = add_goal_milestone_match.group(1).strip()
        goal_title = add_goal_milestone_match.group(2).strip()
        speak(add_goal_milestone(goal_title, milestone_title))
        return

    complete_goal_milestone_match = re.match(
        r"^(?:complete|finish|mark)\s+milestone\s+(.+?)\s+(?:in|for)\s+goal\s+(.+?)(?:\s+done)?$",
        command,
    )
    if complete_goal_milestone_match:
        milestone_title = complete_goal_milestone_match.group(1).strip()
        goal_title = complete_goal_milestone_match.group(2).strip()
        speak(complete_goal_milestone(goal_title, milestone_title))
        return

    if command in [
        "goal board",
        "goal board summary",
        "goal summary",
        "show goals",
    ]:
        speak(goal_board_summary())
        return

    if command in [
        "smart reminder priority",
        "smart reminders",
        "prioritize reminders",
        "reminder priority",
    ]:
        speak(smart_reminder_priority_summary())
        return

    if command in [
        "voice trainer status",
        "voice trainer",
    ]:
        speak(voice_trainer_status())
        return

    voice_trainer_match = re.match(
        r"^(?:set|apply|use|switch\s+to)\s+voice\s+trainer\s+(quiet|normal|noisy)$",
        command,
    )
    if not voice_trainer_match:
        voice_trainer_match = re.match(r"^voice\s+trainer\s+(quiet|normal|noisy)$", command)
    if voice_trainer_match:
        speak(apply_voice_trainer(voice_trainer_match.group(1).strip()))
        return

    set_language_mode_match = re.match(
        r"^(?:set|change|use|switch\s+to)\s+language\s+mode\s+(auto|english|tamil)$",
        command,
    )
    if set_language_mode_match:
        speak(set_language_mode(set_language_mode_match.group(1).strip()))
        return

    if command in [
        "language mode status",
        "current language mode",
        "language mode",
    ]:
        speak(language_mode_status())
        return

    preview_language_match = re.match(
        r"^(?:preview|test)\s+language\s+(?:switch|mode)\s+(.+)$",
        command,
    )
    if preview_language_match:
        speak(preview_language_response(preview_language_match.group(1).strip()))
        return

    if command in [
        "meeting summary",
        "meeting mode summary",
        "show meeting summary",
    ]:
        speak(meeting_mode_summary())
        return

    capture_meeting_match = re.match(r"^(?:capture|save)\s+meeting(?:\s+note)?\s+(.+)$", command)
    if capture_meeting_match:
        payload = capture_meeting_match.group(1).strip()
        title = None
        notes = payload
        if ":" in payload:
            possible_title, possible_body = payload.split(":", 1)
            if possible_title.strip() and possible_body.strip():
                title = possible_title.strip()
                notes = possible_body.strip()
        speak(capture_meeting_note(notes, title=title))
        return

    tag_document_match = re.match(r"^tag\s+document\s+(.+?)\s+as\s+(.+)$", command)
    if tag_document_match:
        filename = tag_document_match.group(1).strip()
        tags_text = tag_document_match.group(2).strip()
        speak(tag_document(filename, tags_text))
        return

    move_document_match = re.match(
        r"^(?:move|send)\s+document\s+(.+?)\s+to\s+folder\s+(.+)$",
        command,
    )
    if move_document_match:
        filename = move_document_match.group(1).strip()
        folder = move_document_match.group(2).strip()
        speak(move_document_to_folder(filename, folder))
        return

    if command in [
        "rag library",
        "rag library summary",
        "show rag library",
    ]:
        speak(rag_library_summary())
        return

    create_automation_match = re.match(
        r"^create\s+automation\s+(.+?)\s+when\s+(.+?)\s+then\s+(.+)$",
        command,
    )
    if create_automation_match:
        name = create_automation_match.group(1).strip()
        trigger = create_automation_match.group(2).strip()
        action = create_automation_match.group(3).strip()
        speak(create_automation_rule(name, trigger, action))
        return

    if command in [
        "run automations now",
        "run automation rules now",
        "execute automation rules",
        "test automation rules",
    ]:
        result = run_due_automation_rules(force=True)
        executed = result.get("executed") or []
        failed = result.get("failed") or []
        if executed:
            lines = [
                f"{item.get('rule', 'automation')}: {item.get('message', '')}"
                for item in executed[:3]
            ]
            speak("Automation run complete. " + " | ".join(lines))
            return
        if failed:
            lines = [
                f"{item.get('rule', 'automation')}: {item.get('message', '')}"
                for item in failed[:3]
            ]
            speak("Automation run failed. " + " | ".join(lines))
            return
        speak("No enabled automation rules were available to run.")
        return

    if command in [
        "list automations",
        "automation rules",
        "show automation rules",
    ]:
        speak(list_automation_rules())
        return

    if command in [
        "automation history",
        "automation run history",
        "show automation history",
    ]:
        speak(automation_history_summary())
        return

    automation_toggle_match = re.match(r"^(enable|disable)\s+automation\s+(.+)$", command)
    if automation_toggle_match:
        enabled = automation_toggle_match.group(1) == "enable"
        name = automation_toggle_match.group(2).strip()
        speak(set_automation_enabled(name, enabled))
        return

    setup_mobile_companion_match = re.match(
        r"^(?:setup|set\s+up|connect)\s+mobile\s+companion\s+(.+)$",
        command,
    )
    if setup_mobile_companion_match:
        speak(setup_mobile_companion(setup_mobile_companion_match.group(1).strip()))
        return

    if command in [
        "mobile companion status",
        "mobile status",
        "show mobile companion status",
    ]:
        speak(mobile_companion_status())
        return

    send_mobile_update_match = re.match(r"^send\s+mobile\s+update\s+(.+)$", command)
    if send_mobile_update_match:
        speak(send_mobile_update(send_mobile_update_match.group(1).strip()))
        return

    if command in [
        "nextgen status",
        "new feature status",
        "feature pack status",
    ]:
        snapshot = nextgen_status_snapshot()
        highlights = snapshot.get("highlights") or []
        if highlights:
            speak("Nextgen feature status: " + " | ".join(highlights[:6]))
        else:
            speak("Nextgen features are ready.")
        return

    if command in [
        "show proactive suggestions",
        "proactive suggestions",
        "assistant suggestions",
    ]:
        speak(_proactive_suggestions_summary(force_refresh=False))
        return

    if command in [
        "refresh proactive suggestions",
        "update proactive suggestions",
        "refresh assistant suggestions",
    ]:
        speak(_proactive_suggestions_summary(force_refresh=True))
        return

    if command in ["smart home status", "iot status", "smart home devices", "list smart home devices"]:
        speak(_smart_home_status_summary())
        return

    if command in [
        "smart home setup help",
        "iot setup help",
        "smart home setup",
        "iot config help",
    ]:
        speak(_smart_home_setup_summary())
        return

    if command in [
        "iot validate",
        "validate iot",
        "iot config validation",
        "validate smart home config",
        "smart home validation",
    ]:
        speak(_iot_validation_summary())
        return

    if command in [
        "iot inventory",
        "iot overview",
        "smart home inventory",
        "what iot devices are connected",
        "what smart devices are connected",
        "list iot devices",
    ]:
        speak(_iot_awareness_summary())
        return

    if command in [
        "hardware status",
        "device status",
        "connected hardware",
        "what hardware is connected",
        "what devices are connected",
    ]:
        speak(_hardware_status_summary())
        return

    if command in [
        "recent hardware events",
        "hardware events",
        "recent device events",
        "device events",
    ]:
        speak(_hardware_event_history_summary())
        return

    if command in [
        "rescan hardware",
        "scan hardware",
        "refresh hardware",
        "rescan devices",
        "scan devices",
        "refresh devices",
    ]:
        speak(_rescan_hardware_summary())
        return

    if command in [
        "iot action history",
        "smart home history",
        "smart home action history",
        "recent smart home actions",
    ]:
        speak(_iot_action_history_summary())
        return

    if any(
        token in command
        for token in [
            "what is matter",
            "what is zigbee",
            "what is z wave",
            "what is zwave",
            "what is thread",
            "what is mqtt",
            "what is iot",
            "what is smart home",
            "what is home assistant",
            "what is esp32",
            "compare zigbee and matter",
            "compare matter and zigbee",
            "zigbee vs matter",
            "matter vs zigbee",
            "compare zigbee and z wave",
            "compare zigbee and zwave",
            "zigbee vs z wave",
            "zigbee vs zwave",
        ]
    ):
        response = _iot_knowledge_summary(command)
        if response:
            speak(response)
            return

    if command in [
        "piper setup status",
        "piper voice setup",
        "piper status",
    ]:
        speak(_piper_setup_summary())
        return

    if command in [
        "my voice setup",
        "my voice setup status",
        "own voice setup",
        "custom voice setup",
        "voice clone setup",
    ]:
        speak(_custom_voice_setup_summary())
        return

    if command in [
        "my voice license status",
        "custom voice license status",
        "voice license status",
        "coqui license status",
    ]:
        speak(custom_voice_license_status_summary())
        return

    if command in [
        "list my voice samples",
        "list custom voice samples",
        "show custom voice samples",
        "available custom voice samples",
    ]:
        speak(list_custom_voice_samples_summary())
        return

    choose_custom_voice_match = re.match(
        r"^(?:use|choose|select|set)\s+(?:my|own|custom|cloned)\s+voice\s+sample\s+(?:to\s+)?(.+)$",
        command,
    )
    if choose_custom_voice_match:
        speak(choose_custom_voice_sample_summary(choose_custom_voice_match.group(1).strip()))
        return

    if command in [
        "auto configure my voice",
        "autoconfigure my voice",
        "detect my voice sample",
        "auto configure custom voice",
    ]:
        speak(autoconfigure_custom_voice_sample()[1])
        return

    if command in [
        "use my voice",
        "switch to my voice",
        "use own voice",
        "use custom voice",
        "switch to custom voice",
        "use cloned voice",
    ]:
        speak(prefer_custom_voice_backend()[1])
        return

    if command in [
        "accept my voice license",
        "accept custom voice license",
        "accept coqui license",
        "agree to my voice license",
        "agree to coqui license",
    ]:
        speak(accept_custom_voice_license()[1])
        return

    if command in ["list piper models", "show piper models", "available piper models"]:
        speak(list_piper_models_summary())
        return

    choose_piper_match = re.match(
        r"^(?:use|choose|select|set)\s+piper\s+(?:voice\s+)?model\s+(?:to\s+)?(.+)$",
        command,
    )
    if choose_piper_match:
        speak(choose_piper_model_summary(choose_piper_match.group(1).strip()))
        return

    if command in ["auto configure piper", "autoconfigure piper", "detect piper model"]:
        speak(autoconfigure_piper_model()[1])
        return

    if command in ["use piper voice", "prefer piper voice", "switch to piper voice"]:
        speak(prefer_piper_backend()[1])
        return

    if command in [
        "security status",
        "assistant security status",
        "system security status",
    ]:
        speak(_security_status_summary())
        return

    if command in [
        "security alerts",
        "show security alerts",
        "security warnings",
    ]:
        speak(_security_alerts_summary())
        return

    if command in [
        "security logs",
        "show security logs",
        "recent security logs",
    ]:
        speak(_security_logs_summary())
        return

    trust_device_match = re.match(r"^(?:trust|approve)\s+device\s+(.+)$", command)
    if trust_device_match:
        security_status_payload(DEVICE_MANAGER)
        speak(trust_device(trust_device_match.group(1).strip())[1])
        return

    if command in [
        "my voice auth status",
        "voice authentication status",
        "voice auth status",
    ]:
        auth = auth_status_payload()
        if auth.get("voice_profile_enrolled"):
            speak("Voice authentication is enrolled and ready.")
        else:
            speak("Voice authentication is not enrolled yet. Say enroll my voice auth.")
        return

    if command in ["enroll my voice auth", "register my voice", "save my voice auth"]:
        speak("Listening to your voice for security enrollment.")
        success, msg = enroll_user_voice()
        speak(msg)
        return

    if command in ["verify my voice", "recognize my voice", "authenticate my voice"]:
        success, msg, _score = verify_user_voice()
        if success:
            speak(msg)
            if pending_confirmation and pending_confirmation.get("type") == "security_auth":
                auth_state = pending_confirmation
                pending_confirmation = None
                if auth_state.get("admin"):
                    enable_admin_mode()
                _resume_secured_command(auth_state, INSTALLED_APPS, input_mode)
            return
        speak(msg)
        return

    set_security_pin_match = re.match(r"^(?:set|create|change|update)\s+security\s+pin(?:\s+to)?\s+(.+)$", command)
    if set_security_pin_match:
        speak(set_security_pin(set_security_pin_match.group(1).strip())[1])
        return

    verify_pin_match = re.match(r"^(?:security\s+pin|pin|verify\s+pin|unlock\s+with\s+pin)\s+(.+)$", command)
    if verify_pin_match:
        success, msg = verify_security_pin(verify_pin_match.group(1).strip())
        speak(msg)
        return

    if command in ["enable security admin mode", "security admin mode on", "security admin mode"]:
        success, msg = enable_admin_mode()
        if not success:
            pending_confirmation = {
                "type": "security_auth",
                "message": "Authentication is required for security admin mode. Verify your face, verify your voice, or use your security PIN.",
                "command": "enable security admin mode",
                "input_mode": input_mode,
                "admin": True,
            }
            speak(pending_confirmation["message"])
            return
        speak(msg)
        return

    if command in ["disable security admin mode", "security admin mode off"]:
        speak(disable_admin_mode()[1])
        return

    if command in ["security admin status", "is security admin mode on"]:
        speak("Security admin mode is active." if admin_mode_active() else "Security admin mode is not active.")
        return

    if command in ["unlock assistant", "disable assistant lockdown", "assistant lockdown off"]:
        if not auth_status_payload().get("session_active"):
            pending_confirmation = {
                "type": "security_auth",
                "message": "Authentication is required before I can unlock the assistant.",
                "command": "disable assistant lockdown",
                "input_mode": input_mode,
                "admin": False,
            }
            speak(pending_confirmation["message"])
            return
        speak(disable_lockdown()[1])
        return

    if command in ["assistant lockdown", "security lockdown", "emergency", "emergency lockdown", "lock system"]:
        enable_lockdown("emergency request")
        lock_system()
        if get_setting("assistant.emergency_mode_enabled", False):
            speak(_send_emergency_alert())
        speak("Emergency lockdown enabled.")
        return

    if command in [
        "face security status",
        "face verification status",
        "face status",
        "is my face enrolled",
    ]:
        speak(_face_security_status_summary())
        return

    if command in ["voice diagnostics", "voice tuning status", "voice debug"]:
        speak(_voice_diagnostics_summary())
        return

    if command in [
        "assistant doctor",
        "startup doctor",
        "system doctor",
        "check assistant health",
        "assistant health check",
    ]:
        speak(_assistant_doctor_summary(include_ready=False))
        return

    if command in [
        "semantic memory status",
        "memory semantic status",
        "semantic search status",
    ]:
        reply = _semantic_memory_summary()
        speak(reply)
        set_last_result(reply)
        return

    semantic_memory_search_match = re.match(
        r"^(?:search|find|look\s+up)\s+(?:my\s+)?memory\s+(?:for\s+)?(.+)$",
        command,
    )
    if semantic_memory_search_match:
        reply = _semantic_memory_lookup_summary(semantic_memory_search_match.group(1).strip())
        speak(reply)
        set_last_result(reply)
        return

    # Phase 4: Smart Home IoT Catch-all
    # Only triggered if it's explicitly "turn on/off" or "switch on/off" 
    # and wasn't caught by internal settings (like "turn on focus mode")
    network_like_command = any(
        token in command
        for token in [
            "wifi",
            "wi-fi",
            "wireless",
            "bluetooth",
            "blue tooth",
            "blutooth",
            "airplane mode",
            "flight mode",
            "energy saver",
            "battery saver",
            "power saver",
            "night light",
            "night mode",
            "blue light",
            "mobile hotspot",
            "wifi hotspot",
            "hotspot",
            "nearby sharing",
            "nearby share",
            "live captions",
            "live caption",
            "accessibility",
            "cast screen",
            "screen cast",
            "project screen",
            "second screen",
            "projection mode",
            "focus assist",
            "do not disturb",
            "quiet hours",
            "dnd",
            "camera",
            "microphone",
            "mic",
            "display mode",
            "duplicate screen",
            "extend screen",
            "pc screen only",
            "second screen only",
            "volume",
            "brightness",
        ]
    )

    if not network_like_command:
        iot_resolution = resolve_iot_command(command)
        if iot_resolution.get("matched"):
            if iot_resolution.get("requires_confirmation"):
                pending_confirmation = {
                    "type": "iot_action_confirm",
                    "action": lambda: run_iot_command(command, confirm=True).get("message", "Smart Home command completed."),
                    "message": iot_resolution.get("message")
                    or f"Please confirm before I run {iot_resolution.get('matched_command', command)}.",
                }
                speak(pending_confirmation["message"])
                return

            success, msg = dispatch_iot_command(command)
            speak(msg)
            if success:
                set_last_result(msg)
            return
        if iot_resolution.get("handled") and iot_resolution.get("message"):
            candidate_commands = iot_resolution.get("candidate_commands") or []
            if candidate_commands:
                speak(iot_resolution["message"] + " Try " + " | ".join(candidate_commands[:3]) + ".")
            else:
                speak(iot_resolution["message"])
            return

    if command in ["enroll my face", "register my face", "save my face"]:
        speak("Looking for your face. Please look at the camera for a moment.")
        success, msg = enroll_user_face()
        if success:
            speak("Your face has been securely enrolled.")
        else:
            speak(f"Failed to enroll face: {msg}")
        return

    if command in ["verify my face", "recognize my face", "who am i"]:
        speak("Verifying...")
        success, msg = verify_face_identity()
        if success:
            speak("Identity verified! Hello there.")
            if pending_confirmation and pending_confirmation.get("type") == "security_auth":
                auth_state = pending_confirmation
                pending_confirmation = None
                if auth_state.get("admin"):
                    enable_admin_mode()
                _resume_secured_command(auth_state, INSTALLED_APPS, input_mode)
        else:
            speak(f"Verification failed: {msg}")
        return

    if command in ["voice status", "voice recognition status", "current voice profile"]:
        speak(voice_status_summary())
        return

    if command in ["developer summary", "workspace summary", "coding summary"]:
        speak(_developer_workspace_summary())
        return

    if command in ["open terminal", "open developer terminal", "start terminal"]:
        speak(_open_local_terminal())
        return

    if command in ["git status", "check git status", "developer git status"]:
        speak(_local_git_status_summary())
        return

    if command in ["current git branch", "what branch am i on", "git branch"]:
        speak(_git_current_branch_summary())
        return

    if command in ["git remotes", "show git remotes", "github remotes"]:
        speak(_git_remote_summary())
        return

    if command in ["recent commits", "git recent commits", "show recent commits"]:
        speak(_git_recent_commits_summary())
        return

    if command in ["github summary", "git summary", "repository summary"]:
        speak(_git_repo_summary())
        return

    if command in ["google calendar status", "calendar sync status"]:
        speak(google_calendar_status())
        return

    if command in ["sync google calendar", "refresh google calendar"]:
        success, reply = sync_google_calendar()
        speak(reply)
        return

    if command in ["today in google calendar", "google calendar today", "today google calendar events"]:
        speak(today_google_calendar_events())
        return

    if command in ["upcoming google calendar events", "google calendar upcoming events"]:
        speak(upcoming_google_calendar_events())
        return

    if command in ["list google calendar event titles", "google calendar titles", "show google calendar titles"]:
        speak(list_google_calendar_event_titles())
        return

    if command.startswith(("add google calendar event", "create google calendar event", "schedule google calendar event")):
        speak(add_google_calendar_event(command))
        return

    if command in ["delete latest google calendar event", "remove latest google calendar event"]:
        speak(delete_latest_google_calendar_event())
        return

    if command.startswith(("rename latest google calendar event", "update latest google calendar event")):
        speak(rename_latest_google_calendar_event(command))
        return

    if command.startswith(("delete google calendar event", "remove google calendar event")):
        speak(delete_google_calendar_event_by_title(command))
        return

    if command.startswith(("rename google calendar event", "update google calendar event")):
        speak(rename_google_calendar_event_by_title(command))
        return

    if command.startswith(("reschedule latest google calendar event", "move latest google calendar event")):
        speak(reschedule_latest_google_calendar_event(command))
        return

    if command.startswith(("reschedule google calendar event", "move google calendar event")):
        speak(reschedule_google_calendar_event_by_title(command))
        return

    if command in ["save and run current file", "developer save and run", "save run current file"]:
        speak(_developer_save_and_run())
        return

    if command in ["debug current code", "summarize current code", "explain current code"]:
        speak(summarize_code_editor())
        return

    if command in ["enable emergency mode", "turn on emergency mode", "emergency mode on"]:
        update_setting("assistant.emergency_mode_enabled", True)
        speak("Emergency mode enabled.")
        return

    if command in ["disable emergency mode", "turn off emergency mode", "emergency mode off"]:
        update_setting("assistant.emergency_mode_enabled", False)
        speak("Emergency mode disabled.")
        return

    if command in ["emergency mode status", "what is emergency mode", "emergency help"]:
        enabled = get_setting("assistant.emergency_mode_enabled", False)
        prefix = "Emergency mode is enabled. " if enabled else "Emergency mode is disabled. "
        speak(prefix + _emergency_mode_summary())
        return

    if command in ["emergency quick response", "emergency quick responses", "quick response system"]:
        speak(_emergency_quick_response_summary())
        return

    if command in ["emergency protocol status", "what is emergency protocol"]:
        speak(_emergency_protocol_summary())
        return

    if command in ["start emergency protocol", "trigger emergency protocol", "emergency protocol"]:
        pending_confirmation = {
            "type": "contact_action_confirm",
            "message": "Should I start the emergency protocol now?",
            "action": _trigger_emergency_protocol,
        }
        speak(pending_confirmation["message"])
        return

    if command in ["send emergency alert", "emergency alert", "alert emergency contact", "send sos"]:
        speak(_send_emergency_alert())
        return

    if command in ["send i am safe alert", "i am safe alert", "send safe alert"]:
        speak(_send_safe_alert())
        return

    if command in ["send safe alert everywhere", "i am safe everywhere"]:
        speak(_send_safe_alert())
        return

    if command in ["share my location", "share saved location", "what is my saved location"]:
        speak(_share_saved_location())
        return

    if command in ["share my location everywhere", "share saved location everywhere", "send my location to emergency contact"]:
        speak(_share_saved_location_everywhere())
        return

    if command in ["send emergency alert everywhere", "send sos everywhere", "alert everyone emergency"]:
        speak(_send_emergency_alert())
        return

    if command in ["call emergency contact", "emergency call", "call my emergency contact"]:
        if _should_confirm_contact_action("call"):
            display_name = _best_contact_display_name("my emergency contact")
            pending_confirmation = {
                "type": "contact_action_confirm",
                "message": f"Should I call {display_name}?",
                "action": _call_emergency_contact,
            }
            speak(pending_confirmation["message"])
            return
        speak(_call_emergency_contact())
        return

    if command in ["repeat that", "say that again", "repeat last reply", "repeat last response"]:
        last_text = get_best_followup_text()
        speak(last_text or "I do not have a recent reply to repeat right now.")
        return

    preferred_language_match = re.match(
        r"^(?:set|change|update)\s+preferred\s+(?:response\s+)?language\s+to\s+(.+)$",
        command,
    )
    if preferred_language_match:
        value = preferred_language_match.group(1).strip()
        speak(update_memory_field("preferred response language", value)[1])
        return

    preferred_tone_match = re.match(
        r"^(?:set|change|update)\s+preferred\s+(?:response\s+)?tone\s+to\s+(.+)$",
        command,
    )
    if preferred_tone_match:
        value = preferred_tone_match.group(1).strip()
        speak(update_memory_field("preferred response tone", value)[1])
        return

    if command in ["what is my preferred language", "my preferred language", "preferred language"]:
        value = get_memory("personal.assistant.preferred_response_language")
        speak(f"Your preferred language is {value}." if value else "You have not saved a preferred language yet.")
        return

    if command in ["what is my preferred tone", "my preferred tone", "preferred tone"]:
        value = get_memory("personal.assistant.preferred_response_tone")
        speak(f"Your preferred tone is {value}." if value else "You have not saved a preferred tone yet.")
        return

    if command in ["storage status", "disk space", "storage report"]:
        reply = get_storage_report()
        speak(reply)
        set_last_result(reply)
        return

    if command in ["storage cleanup suggestion", "cleanup suggestion", "how should i clean storage"]:
        reply = get_cleanup_suggestion()
        speak(reply)
        set_last_result(reply)
        return

    if command in ["motivate me", "give me motivation", "motivation please"]:
        reply = get_motivation_line()
        speak(reply)
        set_last_result(reply)
        return

    interview_match = re.match(
        r"^(?:interview me for|give me interview questions for|start interview practice for)\s+(.+)$",
        command,
    )
    if interview_match:
        topic = interview_match.group(1).strip()
        reply = ask_ollama(
            f"Give 3 concise interview practice questions for {topic} with one-line intent for each.",
            compact=False,
        )
        final_reply = f"Interview practice for {topic}: {reply}"
        speak(final_reply)
        set_last_result(final_reply)
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

    confirm_contact_reply = _maybe_confirm_contact_intent(command)
    if confirm_contact_reply:
        speak(confirm_contact_reply)
        return

    if pending_confirmation:
        if _is_positive_confirmation(command):
            confirmation_state = pending_confirmation
            action = confirmation_state["action"]
            pending_confirmation = None
            action()
            remaining_chain = confirmation_state.get("remaining_chain", [])
            if remaining_chain:
                _continue_remaining_chain(
                    remaining_chain,
                    confirmation_state.get("chain_apps", INSTALLED_APPS),
                    confirmation_state.get("chain_input_mode", input_mode),
                )
            return

        if _is_negative_confirmation(command):
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
    now_dt = datetime.datetime.now()

    if command in [
        "start object detection",
        "start object detector",
        "start camera object detection",
        "object detection mode",
        "detect objects using camera",
    ]:
        if not is_object_detection_available():
            speak(object_detection_import_error() or "Object detection is not available right now.")
            return

        if object_detection_stop_event and not object_detection_stop_event.is_set():
            speak("Object detection is already running.")
            return

        speak("Starting object detection.")
        object_detection_stop_event = threading.Event()
        object_detection_stop_requested_by_command = False

        def notify_object_detection_stopped():
            global object_detection_stop_event, object_detection_stop_requested_by_command
            object_detection_stop_event = None
            if object_detection_stop_requested_by_command:
                object_detection_stop_requested_by_command = False
                return
            print("\nObject detection stopped.")
            if input_mode == "text":
                print("User: ", end="", flush=True)

        def announce_detected_objects(summary):
            alert = consume_watch_alert()
            if alert:
                show_custom_popup("Object Alert", alert["summary"], dedupe_key=f"object-watch-{alert['target']}", force=False)
                speak(alert["summary"])
                return
            if summary and input_mode == "voice":
                speak(summary)

        def silent_object_detection():
            try:
                run_object_detection(
                    object_detection_stop_event,
                    on_stop=notify_object_detection_stopped,
                    announce_callback=announce_detected_objects,
                )
            except Exception as error:
                notify_object_detection_stopped()
                speak(str(error))

        threading.Thread(target=silent_object_detection, daemon=True).start()
        return

    if command in [
        "stop object detection",
        "stop object detector",
        "exit object detection",
        "close object detection",
    ]:
        if object_detection_stop_event:
            object_detection_stop_requested_by_command = True
            object_detection_stop_event.set()
            object_detection_stop_event = None
            speak("Stopping object detection.")
        else:
            speak("Object detection is not running.")
        return

    if command in [
        "what objects do you see",
        "what objects can you see",
        "detected objects",
        "object detection status",
        "what do you see on camera",
    ]:
        if object_detection_stop_event and not object_detection_stop_event.is_set():
            speak(get_latest_detection_summary())
            return

        if not is_object_detection_available():
            speak(object_detection_import_error() or "Object detection is not available right now.")
            return

        result = detect_objects_once()
        if result.get("ok"):
            speak(result.get("summary") or "I could not detect any known objects right now.")
        else:
            speak(result.get("error") or "I could not run object detection right now.")
        return

    if command in [
        "enable small object mode",
        "turn on small object mode",
        "small object mode on",
    ]:
        set_small_object_mode(True)
        speak("Small object mode is now on.")
        return

    if command in [
        "disable small object mode",
        "turn off small object mode",
        "small object mode off",
    ]:
        set_small_object_mode(False)
        speak("Small object mode is now off.")
        return

    if command in [
        "small object mode status",
        "is small object mode on",
    ]:
        if is_small_object_mode_enabled():
            speak("Small object mode is on.")
        else:
            speak("Small object mode is off.")
        return

    if command in [
        "prepare key detection",
        "setup key detection",
        "enable key detection mode",
    ]:
        set_small_object_mode(True)
        set_watch_target("key")
        speak(
            "Key detection mode is ready. Small object mode is on, watch target is key, "
            f"and current model is {get_object_detection_model_name()}."
        )
        return

    if command in [
        "key detection status",
        "show key detection status",
    ]:
        small_mode_text = "on" if is_small_object_mode_enabled() else "off"
        watch_summary = get_watch_status().get("summary") or "No watch status."
        alert_profile = get_object_detection_alert_profile()
        cooldown = int(get_watch_alert_cooldown_seconds())
        speak(
            f"Key detection status: model {get_object_detection_model_name()}, "
            f"small object mode {small_mode_text}, alert profile {alert_profile}, "
            f"cooldown {cooldown} seconds. {watch_summary}"
        )
        return

    if command in [
        "object quick actions",
        "vision quick actions",
        "object detection quick actions",
    ]:
        speak(
            "Quick actions: start object detection, stop object detection, detect objects on screen, "
            "prepare key detection, set object alert mode to fast, set object alert mode to balanced, "
            "set object alert mode to quiet."
        )
        return

    if command in [
        "object quick scan",
        "vision quick scan",
        "scan camera and screen objects",
    ]:
        if not is_object_detection_available():
            speak(object_detection_import_error() or "Object detection is not available right now.")
            return
        camera_result = detect_objects_once()
        if not camera_result.get("ok"):
            speak(camera_result.get("error") or "I could not run quick object scan right now.")
            return
        try:
            screen_result = detect_objects_on_screen()
        except Exception:
            screen_result = {"summary": "Screen scan was skipped."}
        speak(
            "Quick scan done. Camera: "
            + (camera_result.get("summary") or "No camera summary.")
            + " Screen: "
            + (screen_result.get("summary") or "No screen summary.")
        )
        return

    if command in [
        "set object alert mode to fast",
        "object alert mode fast",
        "fast object alerts",
    ]:
        profile = apply_object_detection_alert_profile("fast")
        speak(
            f"Object alert mode set to fast. Announce every {profile['announce_seconds']} seconds, "
            f"watch cooldown {int(profile['cooldown_seconds'])} seconds."
        )
        return

    if command in [
        "set object alert mode to balanced",
        "object alert mode balanced",
        "balanced object alerts",
    ]:
        profile = apply_object_detection_alert_profile("balanced")
        speak(
            f"Object alert mode set to balanced. Announce every {profile['announce_seconds']} seconds, "
            f"watch cooldown {int(profile['cooldown_seconds'])} seconds."
        )
        return

    if command in [
        "set object alert mode to quiet",
        "object alert mode quiet",
        "quiet object alerts",
    ]:
        profile = apply_object_detection_alert_profile("quiet")
        speak(
            f"Object alert mode set to quiet. Announce every {profile['announce_seconds']} seconds, "
            f"watch cooldown {int(profile['cooldown_seconds'])} seconds."
        )
        return

    object_cooldown_match = re.match(
        r"^(?:set|change|update)\s+object\s+alert\s+cooldown\s+to\s+(\d+(?:\.\d+)?)\s*(?:second|seconds|sec|secs|s)?$",
        command,
    )
    if object_cooldown_match:
        value = float(object_cooldown_match.group(1))
        cooldown = set_watch_alert_cooldown_seconds(value)
        speak(f"Object alert cooldown updated to {cooldown:.1f} seconds.")
        return

    if command in [
        "object alert status",
        "vision alert status",
        "object detection alert status",
    ]:
        profile = get_object_detection_alert_profile()
        cooldown = get_watch_alert_cooldown_seconds()
        watch_summary = get_watch_status().get("summary") or "No watch status."
        speak(
            f"Object alert profile is {profile}. Cooldown is {cooldown:.1f} seconds. {watch_summary}"
        )
        return

    if command in [
        "current object model",
        "object detection model status",
    ]:
        speak(f"Current object model is {get_object_detection_model_name()}.")
        return

    if command in [
        "list object model presets",
        "object model presets",
    ]:
        presets = get_object_detection_presets()
        if not presets:
            speak("There are no saved object model presets yet.")
            return
        speak("Saved object model presets: " + ", ".join(preset["name"] for preset in presets[:8]) + ".")
        return

    if command in [
        "reset object model",
        "use default object model",
    ]:
        model_name = reset_object_detection_model()
        speak(f"Object detection model reset to {model_name}.")
        return

    if command.startswith("use object model "):
        model_name = command.replace("use object model", "", 1).strip()
        if not model_name:
            speak("Tell me the object model file name or path.")
            return
        try:
            selected_model = set_object_detection_model_name(model_name)
        except Exception as error:
            speak(str(error))
            return
        speak(f"Object detection model set to {selected_model}.")
        return

    if command.startswith("save object model preset "):
        remainder = command.replace("save object model preset", "", 1).strip()
        if " as " not in remainder:
            speak("Use the format: save object model preset path as preset name.")
            return
        model_name, preset_name = remainder.rsplit(" as ", 1)
        try:
            preset = save_object_detection_preset(preset_name.strip(), model_name.strip())
        except Exception as error:
            speak(str(error))
            return
        speak(f"Saved object model preset {preset['name']}.")
        return

    if command.startswith("use object preset "):
        preset_name = command.replace("use object preset", "", 1).strip()
        if not preset_name:
            speak("Tell me which object preset you want to use.")
            return
        try:
            preset = use_object_detection_preset(preset_name)
        except Exception as error:
            speak(str(error))
            return
        speak(f"Object detection preset {preset['name']} is now active.")
        return

    if command.startswith("delete object preset "):
        preset_name = command.replace("delete object preset", "", 1).strip()
        if not preset_name:
            speak("Tell me which object preset you want me to delete.")
            return
        try:
            delete_object_detection_preset(preset_name)
        except Exception as error:
            speak(str(error))
            return
        speak(f"Deleted object preset {preset_name}.")
        return

    if command in [
        "what objects can you detect",
        "supported objects",
        "object detection supported objects",
    ]:
        if not is_object_detection_available():
            speak(object_detection_import_error() or "Object detection is not available right now.")
            return
        try:
            labels = get_supported_object_labels(limit=24)
        except Exception as error:
            speak(str(error))
            return
        if not labels:
            speak("I could not load the supported object list right now.")
            return
        speak("I can detect objects like " + ", ".join(labels[:12]) + ".")
        return

    if command.startswith("watch for "):
        target = command.replace("watch for", "", 1).strip()
        if not target:
            speak("Tell me which object you want me to watch.")
            return
        set_watch_target(target)
        speak(f"Okay, I will watch for {target}.")
        return

    if command.startswith("if ") and command.endswith(" appears alert me"):
        target = command[3:-16].strip()
        if not target:
            speak("Tell me which object you want me to watch.")
            return
        set_watch_target(target)
        speak(f"Okay, I will alert you when {target} appears.")
        return

    if command in [
        "stop object watch",
        "clear object watch",
        "disable object alert",
        "stop watching objects",
    ]:
        clear_watch_target()
        speak("Object watch cleared.")
        return

    if command in [
        "object watch status",
        "what object am i watching",
        "watch target status",
    ]:
        speak(get_watch_status().get("summary") or "No object watch is active.")
        return

    if command in [
        "object detection history",
        "show object history",
        "recent detections",
        "detection log",
    ]:
        history = get_detection_history()
        if not history:
            speak("There is no object detection history yet.")
            return
        summaries = [item.get("summary") for item in history[:3] if item.get("summary")]
        speak("Recent detections: " + " | ".join(summaries))
        return

    if command in [
        "object alert history",
        "watch alert history",
        "show watch alerts",
    ]:
        history = get_watch_event_history()
        if not history:
            speak("There is no object watch alert history yet.")
            return
        summaries = [item.get("summary") for item in history[:3] if item.get("summary")]
        speak("Recent watch alerts: " + " | ".join(summaries))
        return

    if command in [
        "clear object history",
        "clear detection history",
        "reset object history",
    ]:
        clear_detection_history()
        speak("Object detection history cleared.")
        return

    if command in [
        "detect objects on screen",
        "what objects are on screen",
        "scan screen for objects",
        "screen object detection",
    ]:
        if not is_object_detection_available():
            speak(object_detection_import_error() or "Object detection is not available right now.")
            return
        try:
            result = detect_objects_on_screen()
            speak(result.get("summary") or "I could not detect any known objects on screen right now.")
        except Exception as error:
            speak(str(error))
        return

    if command.startswith("count ") and command.endswith(" on camera"):
        target = command.replace("count", "", 1).replace("on camera", "", 1).strip()
        if not target:
            speak("Tell me which object you want me to count.")
            return
        if not is_object_detection_available():
            speak(object_detection_import_error() or "Object detection is not available right now.")
            return
        result = detect_objects_once()
        if not result.get("ok"):
            speak(result.get("error") or "I could not run object detection right now.")
            return
        count = count_detected_object(target, result.get("labels", []))
        speak(f"I found {count} {target} on camera.")
        return

    if command.startswith("count ") and command.endswith(" on screen"):
        target = command.replace("count", "", 1).replace("on screen", "", 1).strip()
        if not target:
            speak("Tell me which object you want me to count on screen.")
            return
        if not is_object_detection_available():
            speak(object_detection_import_error() or "Object detection is not available right now.")
            return
        try:
            result = detect_objects_on_screen()
        except Exception as error:
            speak(str(error))
            return
        count = count_detected_object(target, result.get("labels", []))
        speak(f"I found {count} {target} on screen.")
        return

    if command.startswith("is ") and command.endswith(" visible on camera"):
        target = command[3:-17].strip()
        if not target:
            speak("Tell me which object you want me to check on camera.")
            return
        if not is_object_detection_available():
            speak(object_detection_import_error() or "Object detection is not available right now.")
            return
        result = detect_objects_once()
        if not result.get("ok"):
            speak(result.get("error") or "I could not run object detection right now.")
            return
        if is_detected_object_visible(target, result.get("labels", [])):
            speak(f"Yes, I can see {target} on camera.")
        else:
            speak(f"No, I could not see {target} on camera.")
        return

    if command.startswith("is ") and command.endswith(" visible on screen"):
        target = command[3:-17].strip()
        if not target:
            speak("Tell me which object you want me to check on screen.")
            return
        if not is_object_detection_available():
            speak(object_detection_import_error() or "Object detection is not available right now.")
            return
        try:
            result = detect_objects_on_screen()
        except Exception as error:
            speak(str(error))
            return
        if is_detected_object_visible(target, result.get("labels", [])):
            speak(f"Yes, I can see {target} on screen.")
        else:
            speak(f"No, I could not see {target} on screen.")
        return

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
                print("User: ", end="", flush=True)

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
        refreshed_apps = refresh_apps_cache()
        INSTALLED_APPS.clear()
        INSTALLED_APPS.update(refreshed_apps)
        speak(f"Applications rescanned and cache updated. Found {len(INSTALLED_APPS)} apps.")
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

    windows_macro_reply = run_windows_voice_macro(command)
    if windows_macro_reply:
        speak(windows_macro_reply)
        return

    voice_access_reply = handle_voice_access_control(command)
    if voice_access_reply:
        speak(voice_access_reply)
        return

    whatsapp_screen_reply = handle_whatsapp_screen_action(command)
    if whatsapp_screen_reply:
        speak(whatsapp_screen_reply)
        return

    settings_action_reply = handle_settings_page_action(command)
    if settings_action_reply:
        speak(settings_action_reply)
        return

    desktop_action_reply = handle_desktop_action(command)
    if desktop_action_reply:
        speak(desktop_action_reply)
        return

    windows_settings_reply = open_windows_settings_page(command)
    if windows_settings_reply:
        speak(windows_settings_reply)
        return

    windows_app_reply = open_default_windows_app(command)
    if windows_app_reply:
        speak(windows_app_reply)
        return

    visible_screen_reply = handle_visible_screen_action(command)
    if visible_screen_reply:
        speak(visible_screen_reply)
        return

    if command in [
        "what app am i in",
        "what window is active",
        "current window",
        "active window",
    ]:
        speak(get_active_window_summary())
        return

    intent_result = try_handle_intent(command)
    if intent_result["handled"]:
        final_reply = _queue_contact_choice_from_reply(command, intent_result["reply"]) or intent_result["reply"]
        action_kind, target, _content = _extract_contact_intent(command)
        if action_kind and target and final_reply == intent_result["reply"]:
            _remember_contact_context(target, action_kind)
        speak(final_reply)
        set_last_result(final_reply)
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

    if handle_focus_assist(command):
        return

    if handle_camera_controls(command):
        return

    if handle_microphone_controls(command):
        return

    if handle_quick_settings_controls(command):
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
    if date_obj and _looks_like_explicit_date_query(command):
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
        speak("My name is Odin. You can call me Grandpa.")
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

    if command in {
        "hi",
        "hello",
        "hey",
        "hi odin",
        "hello odin",
        "hey odin",
        "hi grandpa",
        "hello grandpa",
        "hey grandpa",
    }:
        speak("Hey! I am doing good. How are you?")
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

    if command.startswith(
        (
            "who is",
            "who was",
            "what is",
            "what are",
            "tell me about",
            "how is",
            "how are",
            "latest about",
            "latest on",
            "news about",
        )
    ):
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

    if command.startswith(("open ", "start ", "launch ")) or command in {"open", "start", "launch"}:
        speak(_open_scanned_or_known_app(command, INSTALLED_APPS))
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
        streamed_any = False

        def _stream_chunk(chunk):
            nonlocal streamed_any
            if not chunk:
                return
            if stream_output and not streamed_any:
                start_streaming_reply()
            streamed_any = True
            append_streaming_reply(chunk)

        try:
            response = ask_ollama(
                f"The user is asking about {app_scan_module.LAST_TOPIC}. {command}",
                stream_callback=_stream_chunk if stream_output else None,
                compact=compact_reply,
            )
        finally:
            if stream_output and streamed_any:
                end_streaming_reply()
        speak(response, already_printed=stream_output and streamed_any)
        set_last_result(response)
        _remember_terminal_learning_turn(command, response, route="terminal-followup-ai", model="assistant")
        return

    # -------- GENERAL AI RESPONSE --------
    try:
        stream_output = input_mode == "text"
        compact_reply = input_mode == "voice" and get_setting("assistant.compact_voice_replies", True)
        streamed_any = False

        def _stream_chunk(chunk):
            nonlocal streamed_any
            if not chunk:
                return
            if stream_output and not streamed_any:
                start_streaming_reply()
            streamed_any = True
            append_streaming_reply(chunk)

        try:
            response = ask_ollama(
                command,
                stream_callback=_stream_chunk if stream_output else None,
                compact=compact_reply,
            )
        finally:
            if stream_output and streamed_any:
                end_streaming_reply()
        if response:
            speak(response, already_printed=stream_output and streamed_any)
            set_last_result(response)
            _remember_terminal_learning_turn(command, response, route="terminal-general-ai", model="assistant")
        else:
            speak("I did not get a proper response.")

    except Exception as e:
        print("Error:", e)

        play_sound("error.wav")
        speak("Something went wrong")
