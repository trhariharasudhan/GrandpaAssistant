import json
import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "wake_word": "hey grandpa",
    "initial_timeout": 15,
    "active_timeout": 60,
    "voice": {
        "mode": "sensitive",
        "ambient_duration": 0.25,
        "listen_timeout": 4,
        "follow_up_listen_timeout": 3,
        "phrase_time_limit": 6,
        "follow_up_phrase_time_limit": 5,
        "pause_threshold": 1.1,
        "non_speaking_duration": 0.5,
        "dynamic_energy_threshold": True,
        "energy_threshold": 110,
        "dynamic_energy_adjustment_ratio": 1.08,
        "recalibrate_interval": 30,
        "min_command_chars": 3,
        "post_wake_pause_seconds": 0.35,
        "empty_listen_backoff_seconds": 0.2,
        "wake_listen_timeout": 5,
        "wake_phrase_time_limit": 4,
        "wake_match_threshold": 0.68,
        "wake_requires_prefix": True,
        "wake_max_prefix_words": 1,
        "wake_retry_window_seconds": 6,
        "follow_up_timeout_seconds": 12,
        "continuous_conversation_enabled": True,
        "follow_up_keep_alive_seconds": 12,
        "wake_direct_fallback_enabled": True,
        "direct_fallback_min_chars": 7,
        "direct_fallback_min_words": 2,
        "duplicate_command_window_seconds": 4.0,
        "wake_ack_cooldown_seconds": 2.5,
        "error_recovery_backoff_seconds": 0.8,
        "interrupt_follow_up_seconds": 5,
        "interrupt_state_hold_seconds": 0.22,
        "speaking_state_hold_seconds": 0.2,
        "desktop_popup_enabled": True,
        "desktop_chime_enabled": True,
        "stt_backend": "auto",
        "tts_backend": "auto",
        "tts_rate": 170,
        "tts_volume": 1.0,
        "whisper_model": "base",
        "whisper_language": "auto",
        "whisper_fp16": False,
        "whisper_condition_on_previous_text": False,
        "piper_model_path": "",
        "piper_config_path": "",
        "piper_speaker": 0,
        "piper_sentence_silence": 0.15,
    },
    "sounds": {
        "enabled": True,
        "start": False,
        "success": False,
        "error": True,
    },
    "startup": {
        "tray_mode": False,
        "auto_launch_enabled": False,
        "react_ui_on_tray_enabled": False,
        "react_ui_on_tray_mode": "browser",
        "interface_mode": "terminal",
        "terminal_input_mode": "text",
        "show_installed_apps_on_boot": False,
        "print_diagnostics_on_boot": True,
        "print_ready_diagnostics_on_boot": False,
    },
    "assistant": {
        "persona": "casual",
        "model": "phi3",
        "chatgpt_mode_full": True,
        "compact_voice_replies": True,
        "offline_mode_enabled": False,
        "developer_mode_enabled": False,
        "emergency_mode_enabled": False,
        "focus_mode_enabled": False,
    },
    "memory": {
        "semantic_search_enabled": True,
        "semantic_search_model": "all-MiniLM-L6-v2",
        "semantic_search_top_k": 4,
        "semantic_search_min_score": 0.3,
        "semantic_context_enabled": True,
        "semantic_context_top_k": 3,
        "semantic_context_max_chars": 900,
    },
    "hardware": {
        "poll_interval_seconds": 4.0,
        "camera_probe_max_index": 2,
        "camera_probe_interval_seconds": 15.0,
        "iot_scan_enabled": True,
        "iot_scan_interval_seconds": 45.0,
        "storage_scan_entry_limit": 24,
        "event_history_limit": 40,
        "speak_events_enabled": True,
    },
    "iot": {
        "confirmation_mode": "risky_only",
        "allow_fuzzy_command_matching": True,
        "action_history_limit": 40,
        "network_name_lookup_enabled": False,
        "network_name_lookup_limit": 6,
    },
    "browser": {
        "page_load_delay_seconds": 3,
        "whatsapp_load_delay_seconds": 8,
        "gmail_load_delay_seconds": 8,
        "whatsapp_search_retry_count": 2,
        "whatsapp_search_retry_delay_seconds": 1.2,
        "whatsapp_auto_send": True,
        "whatsapp_send_press_count": 1,
        "whatsapp_send_confirm_delay_seconds": 0.8,
        "whatsapp_success_popup_enabled": True,
    },
    "ocr": {
        "region_hotkey_enabled": True,
        "region_hotkey": "ctrl+shift+o",
    },
    "hand_mouse": {
        "smoothing_alpha": 0.22,
        "frame_margin": 90,
        "zoom_threshold": 24,
        "scroll_delay_seconds": 0.28,
        "scroll_amount": 80,
        "click_threshold": 28,
        "gesture_stability_frames": 3,
        "double_click_delay_seconds": 0.4,
        "hold_threshold_seconds": 0.55,
        "right_click_cooldown_seconds": 0.6,
        "exit_hold_seconds": 1.4,
        "show_overlay": True,
    },
    "vision": {
        "object_detection_model": "yolov8n.pt",
        "object_detection_confidence": 0.45,
        "object_detection_person_confidence": 0.68,
        "object_detection_min_area_ratio": 0.0015,
        "object_detection_person_min_area_ratio": 0.03,
        "small_object_mode_enabled": False,
        "small_object_crop_ratio": 0.55,
        "object_detection_presets": [],
        "object_detection_camera_index": 0,
        "object_detection_announce_seconds": 5.0,
        "object_detection_show_overlay": True,
        "watch_alert_cooldown_seconds": 8.0,
        "object_detection_alert_profile": "balanced",
    },
    "overlay": {
        "hotkey_enabled": True,
        "hotkey": "ctrl+shift+space",
    },
    "ui": {
        "autocorrect_enabled": True,
    },
    "google_contacts": {
        "auto_refresh_enabled": True,
        "auto_refresh_hours": 24,
        "live_refresh_enabled": True,
        "live_refresh_minutes": 1,
        "change_popup_enabled": True,
        "confirmation_mode": "calls_only",
    },
    "notifications": {
        "reminder_monitor_enabled": True,
        "reminder_check_interval_minutes": 15,
        "event_monitor_enabled": True,
        "event_check_interval_minutes": 15,
        "status_popup_enabled": False,
        "status_popup_on_startup": False,
        "status_popup_interval_minutes": 120,
        "brief_popup_enabled": False,
        "brief_popup_on_startup": False,
        "brief_popup_interval_minutes": 180,
        "morning_brief_automation_enabled": False,
        "morning_brief_time": "08:00",
        "morning_agenda_combo_enabled": False,
        "night_summary_export_enabled": False,
        "night_summary_time": "21:00",
        "automation_weekdays_only": False,
        "weekend_automation_enabled": True,
        "health_popup_enabled": False,
        "health_popup_on_startup": False,
        "health_popup_interval_minutes": 60,
        "weather_popup_enabled": False,
        "weather_popup_on_startup": False,
        "weather_popup_interval_minutes": 120,
        "agenda_popup_enabled": False,
        "agenda_popup_on_startup": False,
        "agenda_popup_interval_minutes": 60,
        "recap_popup_enabled": False,
        "recap_popup_on_startup": False,
        "recap_popup_interval_minutes": 180,
        "popup_timeout_seconds": 10,
        "popup_cooldown_seconds": 180,
    },
}

APP_ALIASES = {
    "note": "notepad.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "chrome": "chrome.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "paint": "mspaint.exe",
}


def _merge_dicts(base, override):
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def load_settings():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(SETTINGS_PATH):
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as file:
            saved = json.load(file)
    except (OSError, json.JSONDecodeError):
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)

    merged = _merge_dicts(DEFAULT_SETTINGS, saved)
    if merged != saved:
        save_settings(merged)
    return merged


def save_settings(settings):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as file:
        json.dump(settings, file, indent=4)


def get_setting(path, default=None):
    current = load_settings()
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def update_setting(path, value):
    settings = load_settings()
    keys = path.split(".")
    current = settings

    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value
    save_settings(settings)
    return settings
