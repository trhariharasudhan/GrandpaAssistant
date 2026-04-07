import copy
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
        "wake_match_threshold": 0.64,
        "wake_requires_prefix": True,
        "wake_max_prefix_words": 2,
        "wake_retry_window_seconds": 6,
        "follow_up_timeout_seconds": 12,
        "continuous_conversation_enabled": True,
        "follow_up_keep_alive_seconds": 12,
        "wake_direct_fallback_enabled": True,
        "direct_fallback_min_chars": 7,
        "direct_fallback_min_words": 2,
        "duplicate_command_window_seconds": 4.0,
        "wake_ack_cooldown_seconds": 2.5,
        "clap_wake_enabled": False,
        "clap_required_count": 2,
        "clap_wake_window_seconds": 0.85,
        "clap_min_gap_ms": 180,
        "clap_max_gap_ms": 550,
        "clap_max_duration_ms": 120,
        "clap_peak_threshold_multiplier": 3.2,
        "clap_peak_min_rms": 2500,
        "clap_cooldown_seconds": 2.5,
        "clap_samplerate": 16000,
        "clap_blocksize": 512,
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
        "emotion_tone_enabled": True,
        "emotion_rate_happy": 185,
        "emotion_rate_sad": 145,
        "emotion_rate_angry": 150,
        "character_style": "male_deep",
        "whisper_model": "base",
        "whisper_language": "auto",
        "whisper_fp16": False,
        "whisper_condition_on_previous_text": False,
        "custom_voice_sample_path": "",
        "custom_voice_model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
        "custom_voice_language": "en",
        "custom_voice_tos_agreed": False,
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
        "output_language": "english",
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
    "security": {
        "encryption_enabled": True,
        "prompt_guard_enabled": True,
        "threat_detection_enabled": True,
        "session_timeout_seconds": 900,
        "admin_session_timeout_seconds": 300,
        "voice_auth_threshold": 0.82,
        "failed_attempt_limit": 3,
        "lockout_seconds": 300,
        "device_approval_required_types": ["usb", "storage", "camera", "microphone"],
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
    "mobile": {
        "pairing_code_ttl_seconds": 300,
        "event_history_limit": 240,
        "notification_history_limit": 80,
        "command_history_limit": 60,
    },
    "auth": {
        "enabled": True,
        "session_ttl_hours": 168,
        "ui_login_required": True,
        "allow_self_signup": True,
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

_SETTINGS_CACHE = None
_SETTINGS_CACHE_MTIME = None
_LAST_VALIDATION = {
    "ok": True,
    "warnings": [],
    "corrected_paths": [],
    "unknown_paths": [],
    "restored_defaults": False,
}


def _merge_dicts(base, override):
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def _write_settings_file(settings):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as file:
        json.dump(settings, file, indent=4)


def _settings_mtime():
    try:
        return os.path.getmtime(SETTINGS_PATH)
    except OSError:
        return None


def _coerce_bool(value):
    if isinstance(value, bool):
        return value, False
    if isinstance(value, (int, float)):
        return bool(value), True
    if isinstance(value, str):
        lowered = value.strip().lower()
        truthy = {"1", "true", "yes", "on", "enabled"}
        falsy = {"0", "false", "no", "off", "disabled"}
        if lowered in truthy:
            return True, True
        if lowered in falsy:
            return False, True
    return None, False


def _coerce_like_default(value, default):
    if isinstance(default, bool):
        coerced, changed = _coerce_bool(value)
        if coerced is not None:
            return coerced, changed
        return default, True

    if isinstance(default, int) and not isinstance(default, bool):
        if isinstance(value, int) and not isinstance(value, bool):
            return value, False
        if isinstance(value, float) and value.is_integer():
            return int(value), True
        if isinstance(value, str):
            try:
                return int(value.strip()), True
            except ValueError:
                pass
        return default, True

    if isinstance(default, float):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value), not isinstance(value, float)
        if isinstance(value, str):
            try:
                return float(value.strip()), True
            except ValueError:
                pass
        return default, True

    if isinstance(default, str):
        if isinstance(value, str):
            return value, False
        return str(value), True

    if isinstance(default, list):
        if isinstance(value, list):
            return copy.deepcopy(value), False
        if isinstance(value, tuple):
            return list(value), True
        return copy.deepcopy(default), True

    if isinstance(default, dict):
        if isinstance(value, dict):
            return copy.deepcopy(value), False
        return copy.deepcopy(default), True

    return copy.deepcopy(value), False


def _unknown_setting_paths(settings, defaults, prefix=""):
    unknown = []
    if not isinstance(settings, dict) or not isinstance(defaults, dict):
        return unknown

    for key, value in settings.items():
        path = f"{prefix}.{key}" if prefix else key
        if key not in defaults:
            unknown.append(path)
            continue
        if isinstance(value, dict) and isinstance(defaults.get(key), dict):
            unknown.extend(_unknown_setting_paths(value, defaults[key], path))
    return unknown


def _sanitize_settings_value(value, default, path, warnings, corrected_paths):
    if isinstance(default, dict):
        source = value if isinstance(value, dict) else {}
        if value is not None and not isinstance(value, dict):
            warnings.append(f"{path or 'root'} was reset because it should be an object.")
            corrected_paths.append(path or "root")

        result = {}
        for key, child_default in default.items():
            child_path = f"{path}.{key}" if path else key
            result[key] = _sanitize_settings_value(source.get(key), child_default, child_path, warnings, corrected_paths)

        for key, extra_value in source.items():
            if key not in default:
                result[key] = copy.deepcopy(extra_value)
        return result

    if value is None:
        return copy.deepcopy(default)

    coerced, changed = _coerce_like_default(value, default)
    if changed:
        warnings.append(f"{path} was corrected to match the expected setting type.")
        corrected_paths.append(path)
    return coerced


def _build_validation_payload(*, warnings=None, corrected_paths=None, unknown_paths=None, restored_defaults=False):
    warnings = list(warnings or [])
    corrected_paths = sorted({path for path in (corrected_paths or []) if path})
    unknown_paths = sorted({path for path in (unknown_paths or []) if path})
    if unknown_paths:
        warnings.append(
            "Unknown custom settings were preserved: " + ", ".join(unknown_paths[:8]) + ("." if len(unknown_paths) <= 8 else ", ...")
        )
    return {
        "ok": not warnings and not restored_defaults,
        "warnings": warnings,
        "corrected_paths": corrected_paths,
        "unknown_paths": unknown_paths,
        "restored_defaults": restored_defaults,
    }


def _cache_settings(settings, validation):
    global _SETTINGS_CACHE, _SETTINGS_CACHE_MTIME, _LAST_VALIDATION
    _SETTINGS_CACHE = copy.deepcopy(settings)
    _SETTINGS_CACHE_MTIME = _settings_mtime()
    _LAST_VALIDATION = {
        "ok": bool(validation.get("ok")),
        "warnings": list(validation.get("warnings", [])),
        "corrected_paths": list(validation.get("corrected_paths", [])),
        "unknown_paths": list(validation.get("unknown_paths", [])),
        "restored_defaults": bool(validation.get("restored_defaults", False)),
    }


def get_last_settings_validation():
    return copy.deepcopy(_LAST_VALIDATION)


def load_settings():
    global _SETTINGS_CACHE, _SETTINGS_CACHE_MTIME
    os.makedirs(DATA_DIR, exist_ok=True)

    current_mtime = _settings_mtime()
    if _SETTINGS_CACHE is not None and _SETTINGS_CACHE_MTIME == current_mtime:
        return copy.deepcopy(_SETTINGS_CACHE)

    if not os.path.exists(SETTINGS_PATH):
        defaults = copy.deepcopy(DEFAULT_SETTINGS)
        _write_settings_file(defaults)
        _cache_settings(
            defaults,
            _build_validation_payload(
                warnings=["settings.json was missing, so the default configuration was restored."],
                restored_defaults=True,
            ),
        )
        return copy.deepcopy(defaults)

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as file:
            saved = json.load(file)
    except (OSError, json.JSONDecodeError):
        defaults = copy.deepcopy(DEFAULT_SETTINGS)
        _write_settings_file(defaults)
        _cache_settings(
            defaults,
            _build_validation_payload(
                warnings=["settings.json was unreadable, so the default configuration was restored."],
                restored_defaults=True,
            ),
        )
        return copy.deepcopy(defaults)

    if not isinstance(saved, dict):
        defaults = copy.deepcopy(DEFAULT_SETTINGS)
        _write_settings_file(defaults)
        _cache_settings(
            defaults,
            _build_validation_payload(
                warnings=["settings.json did not contain a valid object, so the default configuration was restored."],
                restored_defaults=True,
            ),
        )
        return copy.deepcopy(defaults)

    warnings = []
    corrected_paths = []
    unknown_paths = _unknown_setting_paths(saved, DEFAULT_SETTINGS)
    merged = _merge_dicts(DEFAULT_SETTINGS, saved)
    sanitized = _sanitize_settings_value(merged, DEFAULT_SETTINGS, "", warnings, corrected_paths)

    if sanitized != saved:
        _write_settings_file(sanitized)

    _cache_settings(
        sanitized,
        _build_validation_payload(
            warnings=warnings,
            corrected_paths=corrected_paths,
            unknown_paths=unknown_paths,
            restored_defaults=False,
        ),
    )
    return copy.deepcopy(sanitized)


def save_settings(settings):
    sanitized = _sanitize_settings_value(settings, DEFAULT_SETTINGS, "", [], [])
    _write_settings_file(sanitized)
    _cache_settings(
        sanitized,
        _build_validation_payload(
            warnings=[],
            corrected_paths=[],
            unknown_paths=_unknown_setting_paths(settings, DEFAULT_SETTINGS) if isinstance(settings, dict) else [],
            restored_defaults=False,
        ),
    )


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
