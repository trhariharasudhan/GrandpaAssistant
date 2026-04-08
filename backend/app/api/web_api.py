import asyncio
import contextlib
import datetime
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import threading
import time
import uuid
import zipfile
import atexit
from typing import Any
from xml.etree import ElementTree

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pypdf import PdfReader
from pydantic import BaseModel
import uvicorn

from agents.runtime import ASSISTANT_RUNTIME
from cognition.hub import (
    build_intelligence_prompt_boost,
    intelligence_status_payload,
    observe_user_turn,
    record_assistant_turn,
)
from cognition.recovery_engine import record_system_error
from brain.database import get_recent_commands
from brain.memory_engine import get_memory
from brain.semantic_memory import (
    build_semantic_memory_context,
    search_semantic_memory,
    semantic_memory_status,
)
from device_manager import DEVICE_MANAGER
from iot_control import get_iot_action_history
from iot_registry import summarize_iot_config
from core.unified_command_router import execute_command, looks_like_command_input
from security.hub import security_status_payload, validate_prompt_text
from llm_client import (
    DEFAULT_LLM_PROVIDER,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OLLAMA_MODEL,
    LLM_PROVIDER_ENV,
    OLLAMA_MODEL_ENV,
    OPENAI_MODEL_ENV,
    SYSTEM_PROMPT,
    generate_chat_reply,
    get_llm_status,
    load_env_file,
    stream_chat_reply,
)
from mobile_companion import MOBILE_COMPANION
from productivity_store import (
    get_user_preferences,
    load_chat_state_payload,
    save_chat_state_payload,
    update_user_preferences,
)
from app_auth import (
    authenticate_app_token,
    auth_bootstrap_status,
    auth_status_payload as app_auth_status_payload,
    login_app_user,
    logout_app_token,
    register_app_user,
    require_admin,
)
from app_data_store import (
    append_chat_message,
    get_audit_log as get_app_audit_log,
    list_chat_archive,
    log_audit_event,
    update_user_profile,
    upsert_chat_session,
)
from startup_diagnostics import collect_startup_diagnostics
from modules.event_module import get_event_data
from modules.google_contacts_module import CACHE_PATH as GOOGLE_CONTACTS_CACHE_PATH
from modules.google_contacts_module import (
    get_recent_contact_change_summary,
    list_contact_aliases,
    list_favorite_contacts,
)
from modules.health_module import get_system_status
from modules.notes_module import latest_note
from modules.nextgen_module import nextgen_status_snapshot, run_due_automation_rules
from modules.startup_module import (
    disable_startup_auto_launch,
    enable_startup_auto_launch,
    startup_auto_launch_status,
)
from modules.task_module import get_planner_focus_snapshot, get_task_data
from modules.weather_module import get_weather_report
from utils.config import get_setting, update_setting
from utils.emotion import analyze_emotion, build_emotion_prompt_context
from utils.mood_memory import build_mood_memory_context, mood_status_payload, record_mood_from_analysis
from utils.paths import backend_data_dir, backend_data_path, backend_path, docs_path, project_path
from plugin_system import plugin_status_payload
from vision.object_detection import (
    get_detection_history,
    get_latest_detection_summary,
    get_object_detection_alert_profile,
    get_object_detection_model_name,
    get_object_detection_presets,
    get_watch_alert_cooldown_seconds,
    get_watch_event_history,
    get_watch_status,
    is_small_object_mode_enabled,
)
from features.productivity.profile_module import build_proactive_nudge
from features.productivity.proactive_suggestion_engine import (
    generate_proactive_suggestions,
    get_latest_proactive_suggestions,
)
from voice.listen import (
    _active_voice_settings,
    _get_whisper_model,
    _resolved_whisper_language,
    continuous_conversation_enabled,
    current_voice_mode,
    follow_up_keep_alive_seconds,
    is_interrupt_phrase,
    is_follow_up_keepalive_phrase,
    is_wake_only_phrase,
    listen,
    normalize_phrase,
    stt_backend_payload,
    sanitize_follow_up_command,
    should_run_direct_fallback,
    strip_wake_word,
    wake_word_detected,
)
import voice.speak as voice_speak_module
from voice.speak import synthesize_speech_base64


PROJECT_ROOT = project_path()
load_env_file(project_path(".env"))
DATA_DIR = backend_data_dir()
CHAT_STATE_PATH = backend_data_path("chat_state.json")
IOT_EXAMPLE_PATH = backend_path("assets", "iot_credentials.example.json")
VOICE_IOT_SETUP_DOC_PATH = docs_path("local-voice-iot-setup.md")

app = FastAPI(title="Grandpa Assistant API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_server = None
_server_thread = None
_installed_apps = {}
_voice_thread = None
_voice_lock = threading.Lock()
_voice_enabled = False
_voice_activity = "Ready"
_voice_transcript = ""
_voice_error = ""
_voice_messages = []
_voice_last_reply = ""
_voice_follow_up_until = 0.0
_voice_state_label = "sleeping"
_voice_last_command_key = ""
_voice_last_command_at_ts = 0.0
_voice_last_wake_ack_at = 0.0
_voice_diagnostics = {
    "wake_detection_count": 0,
    "wake_only_count": 0,
    "command_count": 0,
    "follow_up_command_count": 0,
    "retry_window_command_count": 0,
    "direct_fallback_count": 0,
    "duplicate_ignored_count": 0,
    "ignored_count": 0,
    "interrupt_count": 0,
    "error_count": 0,
    "recovery_count": 0,
    "last_heard_phrase": "",
    "last_heard_at": "",
    "last_processed_command": "",
    "last_command_at": "",
    "last_wake_at": "",
    "last_interrupt_at": "",
    "last_ignored_phrase": "",
    "last_ignored_reason": "",
    "last_ignored_at": "",
    "last_recovery_at": "",
    "last_error_at": "",
    "last_error_message": "",
    "wake_retry_until": 0.0,
}
_cancelled_streams = set()
_pending_confirmations = {}

_chat_settings = {
    "llm_provider": os.getenv(LLM_PROVIDER_ENV, DEFAULT_LLM_PROVIDER),
    "model": os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
    "ollama_model": os.getenv(OLLAMA_MODEL_ENV, DEFAULT_OLLAMA_MODEL),
    "system_prompt": SYSTEM_PROMPT,
    "tone": "casual",
    "response_style": "natural",
    "tool_mode": True,
}

_chat_sessions = {}
_session_order = []
_RAG_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "and", "or", "to", "of", "in", "on", "for",
    "with", "by", "at", "from", "as", "it", "this", "that", "these", "those", "be", "been",
    "has", "have", "had", "do", "does", "did", "can", "could", "should", "would", "about",
    "into", "your", "you", "me", "my", "we", "our", "us", "what", "which", "who", "when",
    "where", "why", "how", "tell", "say", "show", "please",
}
_RAG_CHUNK_TOKEN_CACHE = {}
_RAG_CONTEXT_CACHE = {}
_RAG_CONTEXT_CACHE_LIMIT = 120
_chat_state_save_lock = threading.Lock()
_chat_state_save_timer = None
_CHAT_STATE_SAVE_DELAY_SECONDS = 0.35


class StartupSettingsRequest(BaseModel):
    auto_launch_enabled: bool | None = None
    tray_mode: bool | None = None


class PortableSetupRequest(BaseModel):
    action: str = "desktop"


class CommandRequest(BaseModel):
    command: str
    confirmation_id: str | None = None


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatSettingsRequest(BaseModel):
    llm_provider: str | None = None
    model: str | None = None
    ollama_model: str | None = None
    system_prompt: str | None = None
    tone: str | None = None
    response_style: str | None = None
    tool_mode: bool | None = None


class SessionRequest(BaseModel):
    title: str | None = None


class SessionUpdateRequest(BaseModel):
    session_id: str
    title: str


class RegenerateRequest(BaseModel):
    session_id: str


class CancelRequest(BaseModel):
    session_id: str


class RemoveDocumentRequest(BaseModel):
    session_id: str
    filename: str


class MobilePairStartRequest(BaseModel):
    device_name: str | None = None


class MobilePairCompleteRequest(BaseModel):
    pair_code: str
    device_name: str
    platform: str | None = None
    app_version: str | None = None


class MobileTokenAuthRequest(BaseModel):
    token: str


class MobileCommandRequest(BaseModel):
    command: str
    confirmation_id: str | None = None
    include_state: bool = True


class MobileChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    include_audio: bool = False


class MobileRevokeDeviceRequest(BaseModel):
    device_id: str


class AuthRegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str | None = None
    role: str | None = "user"
    device_name: str | None = None


class AuthLoginRequest(BaseModel):
    username: str
    password: str
    device_name: str | None = None


class AuthProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    preferred_language: str | None = None
    response_style: str | None = None
    tone: str | None = None
    theme: str | None = None
    short_answers: bool | None = None


def _compact_text(value):
    return " ".join(str(value or "").split()).strip()


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _is_local_host(host: str) -> bool:
    value = _compact_text(host).lower()
    return value in {"127.0.0.1", "::1", "localhost", "testclient"}


def _require_local_request(request: Request) -> None:
    client = getattr(request, "client", None)
    host = getattr(client, "host", "")
    if _is_local_host(host):
        return
    raise HTTPException(status_code=403, detail="This action is only allowed from the desktop device.")


def _extract_bearer_token(authorization_value: str) -> str:
    value = _compact_text(authorization_value)
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return value


def _authenticated_app_context(request: Request | None, *, required: bool = False) -> dict | None:
    if request is None:
        if required:
            raise HTTPException(status_code=401, detail="Authentication required.")
        return None
    token = _extract_bearer_token(request.headers.get("authorization", ""))
    if not token:
        if required:
            raise HTTPException(status_code=401, detail="Authentication required.")
        return None
    payload = authenticate_app_token(token)
    if not payload:
        if required:
            raise HTTPException(status_code=401, detail="Invalid or expired session.")
        return None
    return payload


def _authenticated_app_user(request: Request | None, *, required: bool = False) -> dict | None:
    payload = _authenticated_app_context(request, required=required)
    return (payload or {}).get("user") if payload else None


def _authenticated_user_id(request: Request | None) -> int | None:
    user = _authenticated_app_user(request, required=False)
    try:
        return int(user.get("id")) if user and user.get("id") is not None else None
    except Exception:
        return None


def _normalize_profile_preferences(payload: AuthProfileUpdateRequest) -> dict[str, Any]:
    preferences = {}
    if payload.preferred_language is not None:
        preferences["preferred_language"] = _compact_text(payload.preferred_language) or "en-US"
    if payload.response_style is not None:
        preferences["response_style"] = _compact_text(payload.response_style) or "balanced"
    if payload.tone is not None:
        preferences["tone"] = _compact_text(payload.tone) or "friendly"
    if payload.theme is not None:
        preferences["theme"] = _compact_text(payload.theme) or "system"
    if payload.short_answers is not None:
        preferences["short_answers"] = bool(payload.short_answers)
    return preferences


def _account_profile_payload(context: dict | None) -> dict[str, Any]:
    user = (context or {}).get("user") if isinstance(context, dict) else None
    user_id = None
    try:
        user_id = int(user.get("id")) if user and user.get("id") is not None else None
    except Exception:
        user_id = None
    preferences = get_user_preferences(user_id) if user_id is not None else {}
    return {
        "user": user,
        "preferences": preferences,
    }


def _web_ui_auth_required() -> bool:
    return bool(get_setting("auth.enabled", True) and get_setting("auth.ui_login_required", True))


def _enforce_app_auth(request: Request | None) -> dict | None:
    if request is None:
        return None
    return _authenticated_app_context(request, required=_web_ui_auth_required())


def _mobile_device_from_request(request: Request) -> dict:
    token = _extract_bearer_token(request.headers.get("authorization", ""))
    device = MOBILE_COMPANION.authenticate_token(token)
    if device:
        return device
    raise HTTPException(status_code=401, detail="Mobile authentication failed.")


def _mobile_device_from_token(token: str) -> dict:
    device = MOBILE_COMPANION.authenticate_token(token)
    if device:
        return device
    raise HTTPException(status_code=401, detail="Mobile authentication failed.")


def _mobile_runtime_snapshot() -> dict:
    try:
        import psutil  # type: ignore

        cpu_percent = round(float(psutil.cpu_percent(interval=0.05)), 1)
        memory = psutil.virtual_memory()
        ram_percent = round(float(memory.percent), 1)
        ram_used_mb = round(float(memory.used) / (1024 * 1024), 1)
        ram_total_mb = round(float(memory.total) / (1024 * 1024), 1)
    except Exception:
        cpu_percent = 0.0
        ram_percent = 0.0
        ram_used_mb = 0.0
        ram_total_mb = 0.0
    return {
        "assistant_state": "active" if _voice_enabled else "idle",
        "cpu_percent": cpu_percent,
        "ram_percent": ram_percent,
        "ram_used_mb": ram_used_mb,
        "ram_total_mb": ram_total_mb,
        "voice": _voice_status_payload(),
        "runtime": ASSISTANT_RUNTIME.status_payload(),
    }


def _mobile_dashboard_payload(device: dict | None = None) -> dict:
    task_data = _safe_call(get_task_data, {"tasks": [], "reminders": []})
    tasks = task_data.get("tasks") or []
    reminders = task_data.get("reminders") or []
    ui_state = _build_ui_state()
    return {
        "device": device or {},
        "status": _mobile_runtime_snapshot(),
        "tasks": {
            "pending_count": sum(1 for item in tasks if not item.get("completed")),
            "items": tasks[:12],
        },
        "reminders": {
            "count": len(reminders),
            "items": reminders[:12],
        },
        "memory": {
            "mood": mood_status_payload(),
            "semantic": semantic_memory_status(prewarm=False),
        },
        "hardware": ui_state.get("integrations", {}).get("hardware", {}),
        "smart_home": ui_state.get("integrations", {}).get("smart_home", {}),
        "nextgen": ui_state.get("nextgen", {}),
        "overview": ui_state.get("overview", {}),
    }


def _mobile_audio_reply(text: str, include_audio: bool) -> dict:
    if not include_audio:
        return {}
    try:
        audio_payload = synthesize_speech_base64(text, preferred_backend="coqui")
        return audio_payload
    except Exception:
        try:
            return synthesize_speech_base64(text, preferred_backend="piper")
        except Exception:
            return {}


def _transcribe_mobile_audio_file(file_path: str, preferred_language: str = "en-US") -> str:
    settings = _active_voice_settings("normal")
    model = _get_whisper_model(settings["whisper_model"])
    whisper_language = _resolved_whisper_language(preferred_language=preferred_language)
    result = model.transcribe(
        file_path,
        language=whisper_language,
        fp16=bool(settings["whisper_fp16"]),
        condition_on_previous_text=bool(settings["whisper_condition_on_previous_text"]),
        task="transcribe",
    )
    text = _compact_text((result or {}).get("text"))
    if not text:
        raise ValueError("Whisper returned an empty transcription.")
    return text


def _save_chat_state():
    global _chat_state_save_timer
    with _chat_state_save_lock:
        timer = _chat_state_save_timer
        if timer is not None and timer.is_alive():
            return
        _chat_state_save_timer = threading.Timer(_CHAT_STATE_SAVE_DELAY_SECONDS, _flush_chat_state)
        _chat_state_save_timer.daemon = True
        _chat_state_save_timer.start()


def _default_chat_state_payload():
    return {
        "settings": dict(_chat_settings),
        "session_order": list(_session_order),
        "sessions": dict(_chat_sessions),
    }


def _load_legacy_chat_state_payload():
    _ensure_data_dir()
    if not os.path.exists(CHAT_STATE_PATH):
        return _default_chat_state_payload()
    try:
        with open(CHAT_STATE_PATH, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:
        return _default_chat_state_payload()
    return payload if isinstance(payload, dict) else _default_chat_state_payload()


def _flush_chat_state():
    global _chat_state_save_timer
    _ensure_data_dir()
    payload = _default_chat_state_payload()
    with _chat_state_save_lock:
        timer = _chat_state_save_timer
        _chat_state_save_timer = None
        if timer is not None and timer.is_alive():
            timer.cancel()
        try:
            save_chat_state_payload(payload, default_factory=_default_chat_state_payload)
        except Exception:
            try:
                temp_path = f"{CHAT_STATE_PATH}.tmp"
                with open(temp_path, "w", encoding="utf-8") as file:
                    json.dump(payload, file, ensure_ascii=False, indent=2)
                os.replace(temp_path, CHAT_STATE_PATH)
            except Exception:
                return


def _apply_runtime_chat_settings():
    os.environ[LLM_PROVIDER_ENV] = _compact_text(_chat_settings.get("llm_provider")) or DEFAULT_LLM_PROVIDER
    os.environ[OPENAI_MODEL_ENV] = _compact_text(_chat_settings.get("model")) or DEFAULT_OPENAI_MODEL
    os.environ[OLLAMA_MODEL_ENV] = _compact_text(_chat_settings.get("ollama_model")) or DEFAULT_OLLAMA_MODEL


def _load_chat_state():
    global _chat_settings, _chat_sessions, _session_order
    try:
        payload = load_chat_state_payload(
            default_factory=_default_chat_state_payload,
            legacy_loader=_load_legacy_chat_state_payload,
        )
    except Exception:
        payload = _load_legacy_chat_state_payload()

    saved_settings = payload.get("settings") or {}
    saved_sessions = payload.get("sessions") or {}
    saved_order = payload.get("session_order") or []

    if isinstance(saved_settings, dict):
        _chat_settings.update(
            {
                "llm_provider": _compact_text(saved_settings.get("llm_provider")) or _chat_settings["llm_provider"],
                "model": _compact_text(saved_settings.get("model")) or _chat_settings["model"],
                "ollama_model": _compact_text(saved_settings.get("ollama_model")) or _chat_settings["ollama_model"],
                "system_prompt": saved_settings.get("system_prompt") or _chat_settings["system_prompt"],
                "tone": _compact_text(saved_settings.get("tone")) or _chat_settings["tone"],
                "response_style": _compact_text(saved_settings.get("response_style")) or _chat_settings["response_style"],
                "tool_mode": bool(saved_settings.get("tool_mode", _chat_settings["tool_mode"])),
            }
        )
        _apply_runtime_chat_settings()

    if isinstance(saved_sessions, dict):
        _chat_sessions = saved_sessions
    if isinstance(saved_order, list):
        _session_order = [item for item in saved_order if item in _chat_sessions]


    if not _session_order and _chat_sessions:
        _session_order = list(_chat_sessions.keys())

    for session in _chat_sessions.values():
        session.setdefault("messages", [])
        session["documents"] = _normalize_documents(session.get("documents"))
        session.setdefault("created_at", _utc_now())
        session.setdefault("updated_at", _utc_now())
        session.setdefault("title", "New chat")
        session.setdefault("id", str(uuid.uuid4()))


atexit.register(_flush_chat_state)


def _safe_call(callback, fallback):
    try:
        value = callback()
    except Exception:
        return fallback
    return fallback if value is None else value


def _local_now_label():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _reset_voice_diagnostics():
    global _voice_diagnostics, _voice_last_command_key, _voice_last_command_at_ts, _voice_last_wake_ack_at
    _voice_last_command_key = ""
    _voice_last_command_at_ts = 0.0
    _voice_last_wake_ack_at = 0.0
    _voice_diagnostics = {
        "wake_detection_count": 0,
        "wake_only_count": 0,
        "command_count": 0,
        "follow_up_command_count": 0,
        "retry_window_command_count": 0,
        "direct_fallback_count": 0,
        "duplicate_ignored_count": 0,
        "ignored_count": 0,
        "interrupt_count": 0,
        "error_count": 0,
        "recovery_count": 0,
        "last_heard_phrase": "",
        "last_heard_at": "",
        "last_processed_command": "",
        "last_command_at": "",
        "last_wake_at": "",
        "last_interrupt_at": "",
        "last_ignored_phrase": "",
        "last_ignored_reason": "",
        "last_ignored_at": "",
        "last_recovery_at": "",
        "last_error_at": "",
        "last_error_message": "",
        "wake_retry_until": 0.0,
    }


def _mark_voice_heard(heard):
    global _voice_diagnostics
    _voice_diagnostics["last_heard_phrase"] = _compact_text(heard)
    _voice_diagnostics["last_heard_at"] = _local_now_label()


def _mark_voice_wake(retry_until):
    global _voice_diagnostics
    _voice_diagnostics["wake_detection_count"] += 1
    _voice_diagnostics["last_wake_at"] = _local_now_label()
    _voice_diagnostics["wake_retry_until"] = max(0.0, float(retry_until or 0.0))


def _mark_voice_command(heard, source):
    global _voice_diagnostics, _voice_last_command_key, _voice_last_command_at_ts
    source = _compact_text(source) or "direct"
    _voice_diagnostics["command_count"] += 1
    _voice_diagnostics["last_processed_command"] = _compact_text(heard)
    _voice_diagnostics["last_command_at"] = _local_now_label()
    _voice_last_command_key = normalize_phrase(heard)
    _voice_last_command_at_ts = time.time()
    if source == "follow_up":
        _voice_diagnostics["follow_up_command_count"] += 1
    elif source == "retry_window":
        _voice_diagnostics["retry_window_command_count"] += 1
    elif source == "direct_fallback":
        _voice_diagnostics["direct_fallback_count"] += 1


def _mark_voice_ignored(heard, reason):
    global _voice_diagnostics
    normalized_reason = _compact_text(reason) or "ignored"
    _voice_diagnostics["ignored_count"] += 1
    if normalized_reason == "duplicate":
        _voice_diagnostics["duplicate_ignored_count"] += 1
    _voice_diagnostics["last_ignored_phrase"] = _compact_text(heard)
    _voice_diagnostics["last_ignored_reason"] = normalized_reason
    _voice_diagnostics["last_ignored_at"] = _local_now_label()


def _mark_voice_interrupt():
    global _voice_diagnostics
    _voice_diagnostics["interrupt_count"] += 1
    _voice_diagnostics["last_interrupt_at"] = _local_now_label()


def _mark_voice_error(message):
    global _voice_diagnostics
    _voice_diagnostics["error_count"] += 1
    _voice_diagnostics["last_error_at"] = _local_now_label()
    _voice_diagnostics["last_error_message"] = _compact_text(message)


def _mark_voice_recovery():
    global _voice_diagnostics
    _voice_diagnostics["recovery_count"] += 1
    _voice_diagnostics["last_recovery_at"] = _local_now_label()


def _voice_diagnostics_payload():
    payload = dict(_voice_diagnostics)
    retry_until = float(payload.get("wake_retry_until") or 0.0)
    payload["wake_retry_window_active"] = retry_until > datetime.datetime.now().timestamp()
    payload["wake_retry_remaining"] = max(0, int(retry_until - datetime.datetime.now().timestamp()))
    return payload


def _load_local_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return None


def _smart_home_status_payload():
    configured = summarize_iot_config()
    discovered = _safe_call(DEVICE_MANAGER.get_iot_status, {"discovered_devices": [], "summary": "IoT status unavailable."})
    return {
        "configured": configured.get("configured", False),
        "enabled": configured.get("enabled", False),
        "device_count": configured.get("device_count", 0),
        "command_count": configured.get("command_count", 0),
        "sample_commands": configured.get("sample_commands", []),
        "placeholder_count": configured.get("placeholder_count", 0),
        "configured_devices": configured.get("devices", []),
        "discovered_devices": discovered.get("discovered_devices", []),
        "discovered_count": discovered.get("discovered_count", 0),
        "control_ready_count": discovered.get("control_ready_count", 0),
        "recent_actions": get_iot_action_history(limit=8),
        "config_example_path": IOT_EXAMPLE_PATH,
        "setup_doc_path": VOICE_IOT_SETUP_DOC_PATH,
        "supported_control_modes": ["webhook", "home_assistant_service", "mqtt"],
        "summary": " ".join(
            part
            for part in [
                configured.get("summary", ""),
                discovered.get("summary", ""),
            ]
            if part
        ).strip()
        or "Smart Home status unavailable.",
    }


def _face_security_payload():
    profile_path = backend_data_path("face_profile.json")
    enrolled = os.path.exists(profile_path)
    camera_ready = importlib.util.find_spec("cv2") is not None
    embedding_ready = importlib.util.find_spec("deepface") is not None
    updated_at = ""
    if enrolled:
        with contextlib.suppress(OSError):
            updated_at = datetime.datetime.fromtimestamp(
                os.path.getmtime(profile_path)
            ).isoformat(timespec="seconds")

    if enrolled:
        summary = "Face security is enrolled locally and ready for verification."
    else:
        summary = "Face security is not enrolled yet. Use enroll my face to create a local profile."

    if not camera_ready:
        summary += " OpenCV is not installed, so camera capture is not ready."
    elif not embedding_ready:
        summary += " DeepFace is not installed yet, so face matching is not ready."

    return {
        "enrolled": enrolled,
        "camera_ready": camera_ready,
        "embedding_ready": embedding_ready,
        "updated_at": updated_at,
        "summary": summary,
    }


def _proactive_state_payload(focus_mode):
    suggestions = _safe_call(lambda: get_latest_proactive_suggestions("default", limit=4), [])
    if not suggestions:
        suggestions = _safe_call(lambda: generate_proactive_suggestions("default"), [])

    normalized = []
    for item in suggestions[:4]:
        text = _compact_text(item.get("text") if isinstance(item, dict) else item)
        if not text:
            continue
        normalized.append(
            {
                "text": text,
                "kind": _compact_text(item.get("kind") if isinstance(item, dict) else "suggestion") or "suggestion",
                "score": float(item.get("score", 0.0)) if isinstance(item, dict) else 0.0,
            }
        )

    summary = _safe_call(build_proactive_nudge, "Stay focused on your next useful step today.")
    if normalized:
        summary = f"{summary} Top suggestion: {normalized[0]['text']}"
    if focus_mode:
        summary += " Focus mode is on, so proactive popups are muted."

    return {
        "focus_mode": bool(focus_mode),
        "summary": summary,
        "suggestions": normalized,
    }


def _utc_now():
    return datetime.datetime.utcnow().isoformat() + "Z"


def _history_item(role, content):
    return {
        "id": f"{role}-{datetime.datetime.utcnow().timestamp()}",
        "role": role,
        "content": _compact_text(content),
        "created_at": _utc_now(),
    }


def _trim_messages(messages):
    return messages[-60:]


def _normalize_documents(documents):
    normalized = []
    for item in documents or []:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "id": _compact_text(item.get("id")) or str(uuid.uuid4()),
                "name": _compact_text(item.get("name")) or "Untitled document",
                "kind": _compact_text(item.get("kind")) or "unknown",
                "uploaded_at": item.get("uploaded_at") or _utc_now(),
                "char_count": int(item.get("char_count") or 0),
                "chunk_count": int(item.get("chunk_count") or 0),
                "preview": item.get("preview") or "",
                "chunks": [str(chunk) for chunk in item.get("chunks") or [] if _compact_text(chunk)],
            }
        )
    return normalized


def _tokenize_for_rag(text):
    words = []
    for raw in str(text or "").lower().split():
        cleaned = "".join(char for char in raw if char.isalnum())
        if len(cleaned) < 2 or cleaned in _RAG_STOPWORDS:
            continue
        words.append(cleaned)
    return words


def _chunk_tokens_cached(chunk):
    cached = _RAG_CHUNK_TOKEN_CACHE.get(chunk)
    if cached is not None:
        return cached
    tokens = set(_tokenize_for_rag(chunk))
    _RAG_CHUNK_TOKEN_CACHE[chunk] = tokens
    if len(_RAG_CHUNK_TOKEN_CACHE) > 6000:
        _RAG_CHUNK_TOKEN_CACHE.clear()
    return tokens


def _rag_context_cache_key(session, query, max_chunks, max_chars):
    parts = [
        _compact_text(query).lower(),
        str(max_chunks),
        str(max_chars),
    ]
    for document in session.get("documents") or []:
        parts.append(
            ":".join(
                [
                    _compact_text(document.get("id")),
                    _compact_text(document.get("name")),
                    _compact_text(document.get("uploaded_at")),
                    str(int(document.get("chunk_count") or 0)),
                    str(int(document.get("char_count") or 0)),
                ]
            )
        )
    return "|".join(parts)


def _get_rag_context_from_cache(cache_key):
    return _RAG_CONTEXT_CACHE.get(cache_key)


def _save_rag_context_cache(cache_key, value):
    _RAG_CONTEXT_CACHE[cache_key] = value
    if len(_RAG_CONTEXT_CACHE) > _RAG_CONTEXT_CACHE_LIMIT:
        oldest_key = next(iter(_RAG_CONTEXT_CACHE.keys()))
        _RAG_CONTEXT_CACHE.pop(oldest_key, None)


def _chunk_text(text, chunk_size=900, overlap=150):
    cleaned = " ".join(str(text or "").split())
    if not cleaned:
        return []
    chunks = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(length, start + chunk_size)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(start + 1, end - overlap)
    return chunks


def _extract_pdf_text(data):
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        with contextlib.suppress(Exception):
            pages.append(page.extract_text() or "")
    return "\n".join(pages).strip()


def _extract_docx_text(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        document_xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(document_xml)
    texts = []
    for element in root.iter():
        if element.tag.endswith("}t") and element.text:
            texts.append(element.text)
        elif element.tag.endswith("}p"):
            texts.append("\n")
    return " ".join(part for part in texts if part).replace("\n ", "\n").strip()


def _extract_document_payload(filename, data):
    lower_name = str(filename or "").lower()
    if lower_name.endswith(".pdf"):
        text = _extract_pdf_text(data)
        kind = "pdf"
    elif lower_name.endswith(".docx"):
        text = _extract_docx_text(data)
        kind = "docx"
    elif lower_name.endswith(".txt"):
        text = data.decode("utf-8", errors="ignore")
        kind = "txt"
    else:
        raise ValueError("Only PDF, DOCX, and TXT files are supported.")

    compact_text = " ".join(str(text or "").split())
    if not compact_text:
        raise ValueError("I could not read any text from that file.")

    chunks = _chunk_text(compact_text)
    preview = compact_text[:220]
    return {
        "id": str(uuid.uuid4()),
        "name": os.path.basename(filename or "document"),
        "kind": kind,
        "uploaded_at": _utc_now(),
        "char_count": len(compact_text),
        "chunk_count": len(chunks),
        "preview": preview,
        "chunks": chunks,
    }


def _session_document_context(session, query, max_chunks=4, max_chars=4200):
    documents = session.get("documents") or []
    if not documents:
        return None

    cache_key = _rag_context_cache_key(session, query, max_chunks, max_chars)
    cached = _get_rag_context_from_cache(cache_key)
    if cached is not None:
        return cached

    query_tokens = set(_tokenize_for_rag(query))
    query_text = str(query or "").lower()
    generic_doc_query = any(
        phrase in query_text
        for phrase in ["document", "pdf", "docx", "file", "attachment", "summarize", "summary"]
    )
    if not query_tokens and not generic_doc_query:
        return None

    scored_chunks = []
    per_document_best = []
    scan_limit_per_doc = 36
    for document in documents:
        doc_name = document.get("name", "Document")
        doc_best = None
        for index, chunk in enumerate((document.get("chunks") or [])[:scan_limit_per_doc]):
            chunk_tokens = _chunk_tokens_cached(chunk)
            overlap = len(query_tokens & chunk_tokens)
            if not overlap and not generic_doc_query:
                continue
            overlap_score = overlap / max(1, len(query_tokens)) if query_tokens else 0.05
            contains_query_phrase = 1.0 if query_text and query_text[:42] in chunk.lower() else 0.0
            score = overlap_score + (0.35 * contains_query_phrase)
            entry = (score, doc_name, index, chunk)
            scored_chunks.append(entry)
            if doc_best is None or entry[0] > doc_best[0]:
                doc_best = entry
        if doc_best is not None:
            per_document_best.append(doc_best)

    if not scored_chunks:
        _save_rag_context_cache(cache_key, None)
        return None

    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    per_document_best.sort(key=lambda item: item[0], reverse=True)

    selected_entries = []
    seen_pairs = set()
    for item in per_document_best[: min(3, max_chunks)]:
        pair = (item[1], item[2])
        if pair in seen_pairs:
            continue
        selected_entries.append(item)
        seen_pairs.add(pair)

    for item in scored_chunks:
        if len(selected_entries) >= max_chunks:
            break
        pair = (item[1], item[2])
        if pair in seen_pairs:
            continue
        selected_entries.append(item)
        seen_pairs.add(pair)

    selected_blocks = []
    used_chars = 0
    source_names = []
    for _, name, index, chunk in selected_entries:
        block = f"[Source: {name} | chunk {index + 1}]\n{chunk}"
        if used_chars + len(block) > max_chars and selected_blocks:
            break
        selected_blocks.append(block)
        used_chars += len(block)
        if name not in source_names:
            source_names.append(name)
        if len(selected_blocks) >= max_chunks:
            break

    if not selected_blocks:
        _save_rag_context_cache(cache_key, None)
        return None

    context = (
        "Use the attached document context below to answer the user's question. "
        "When using information from the documents, you MUST explicitly cite the source document name in your answer. "
        "For example: 'According to [Document Name], ...' or '... (Source: [Document Name])'. "
        f"Documents selected for this answer: {', '.join(source_names)}. "
        "If the document does not contain the answer, say that briefly.\n\n"
        + "\n\n".join(selected_blocks)
    )
    _save_rag_context_cache(cache_key, context)
    return context


def _session_title_from_message(text):
    cleaned = _compact_text(text)
    if not cleaned:
        return "New chat"
    return cleaned[:48]


def _ensure_session(session_id=None, title=None, create_new=False):
    global _chat_sessions, _session_order
    if session_id and session_id in _chat_sessions:
        session = _chat_sessions[session_id]
        session["updated_at"] = _utc_now()
        return session

    if not create_new and not session_id and _session_order:
        existing_id = _session_order[0]
        session = _chat_sessions.get(existing_id)
        if session:
            session["updated_at"] = _utc_now()
            return session

    new_id = session_id or str(uuid.uuid4())
    session = {
        "id": new_id,
        "title": title or "New chat",
        "messages": [],
        "documents": [],
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    _chat_sessions[new_id] = session
    remaining = [item for item in _session_order if item != new_id]
    _session_order = [new_id, *remaining]
    upsert_chat_session(new_id, title=session["title"], source="web-ui")
    _save_chat_state()
    return session


def _resolve_session(session_id=None, title=None, create_new=False):
    if session_id and session_id in _chat_sessions:
        return _ensure_session(session_id=session_id, title=title, create_new=create_new)

    if not session_id and _session_order:
        existing_id = _session_order[0]
        session = _chat_sessions.get(existing_id)
        if session:
            session["updated_at"] = _utc_now()
            return session

    return _ensure_session(session_id=session_id, title=title, create_new=create_new)


def _ordered_sessions():
    ordered = []
    for session_id in _session_order:
        session = _chat_sessions.get(session_id)
        if session:
            ordered.append(
                {
                    "id": session["id"],
                    "title": session["title"],
                    "created_at": session["created_at"],
                    "updated_at": session["updated_at"],
                    "message_count": len(session["messages"]),
                    "document_count": len(session.get("documents") or []),
                }
            )
    return ordered


def _delete_session(session_id):
    if session_id not in _chat_sessions:
        return False
    _chat_sessions.pop(session_id, None)
    global _session_order
    _session_order = [item for item in _session_order if item != session_id]
    if not _chat_sessions:
        _ensure_session()
    _save_chat_state()
    return True


def _update_session_title(session, fallback_message=None):
    if session["title"] == "New chat" and fallback_message:
        session["title"] = _session_title_from_message(fallback_message)
        _save_chat_state()


def _friendly_ai_error(error):
    message = _compact_text(error)
    lowered = message.lower()
    if "openai_api_key is missing" in lowered:
        return "OpenAI key missing. Create a .env file in the project root and set OPENAI_API_KEY=your_key."
    if "401" in lowered or "unauthorized" in lowered:
        return "OpenAI key invalid or expired. Update OPENAI_API_KEY in your .env file and restart the app."
    if "temporarily busy" in lowered or "rate limit reached" in lowered or "temporarily unavailable" in lowered:
        return message
    if "connection" in lowered or "timed out" in lowered:
        return "AI provider is not reachable right now. Check your internet connection and API base URL."
    return f"AI request failed: {message or 'Unknown error.'}"


def _tool_prompt():
    return (
        "If the user asks for live assistant actions like tasks, notes, reminders, events, weather, settings, "
        "or desktop/system actions, you may respond with exactly one line in this format: TOOL: <assistant command>. "
        "Only do this when a tool/action is genuinely better than a normal reply. "
        "If not needed, answer normally."
    )


def _active_chat_model() -> str:
    provider = _compact_text(_chat_settings.get("llm_provider")).lower() or DEFAULT_LLM_PROVIDER
    if provider == "ollama":
        return _compact_text(_chat_settings.get("ollama_model")) or DEFAULT_OLLAMA_MODEL
    return _compact_text(_chat_settings.get("model")) or DEFAULT_OPENAI_MODEL


def _effective_system_prompt(user_message="", mood_snapshot=None, context="casual"):
    provider = _compact_text(_chat_settings.get("llm_provider")).lower() or DEFAULT_LLM_PROVIDER
    provider_guidance = ""
    language_guidance = (
        "Understand Tanglish or mixed Tamil-English input, but always reply only in natural English unless the user explicitly asks for translation. "
    )
    emotion_guidance = (
        f"{build_emotion_prompt_context(user_message)} "
        if _compact_text(user_message)
        else ""
    )
    mood_guidance = (
        f"{build_mood_memory_context(mood_snapshot)} "
        if mood_snapshot or _compact_text(user_message)
        else ""
    )
    intelligence_guidance = (
        f"{build_intelligence_prompt_boost(user_message, context=context, emotion=(mood_snapshot or {}).get('last_mood', 'neutral'), mood=mood_snapshot) or ''} "
        if _compact_text(user_message)
        else ""
    )
    conversation_guidance = (
        "Talk like a smart, friendly real person. In normal chat, keep replies short, usually 1 or 2 sentences unless the user asks for more. "
        "Use natural language like hey, yeah, okay, or got it when it fits. Avoid robotic phrasing, bullet lists, and overly structured formatting in casual conversation. "
        "Match the user's mood and keep the flow natural. "
    )
    if provider == "ollama":
        provider_guidance = (
            "When the user asks a normal question, answer directly in plain language. "
            "Do not rewrite the user's request into a task or instruction block. "
            "Use TOOL only for clear assistant actions like opening apps, creating reminders, checking notes, or device control. "
            "If the user asks for an exact sentence, return only that sentence."
        )
    return (
        f"{_chat_settings['system_prompt']} "
        f"Tone: {_chat_settings['tone']}. Response style: {_chat_settings['response_style']}. "
        f"{conversation_guidance}"
        f"{language_guidance}"
        f"{emotion_guidance}"
        f"{mood_guidance}"
        f"{intelligence_guidance}"
        f"{provider_guidance} "
        f"{_tool_prompt() if _chat_settings.get('tool_mode') else ''}"
    ).strip()


def _build_chat_input(session, user_message, mood_snapshot=None, context="casual"):
    memory_context = build_semantic_memory_context(user_message)
    document_context = _session_document_context(session, user_message)
    emotion_context = build_emotion_prompt_context(user_message)
    mood_context = build_mood_memory_context(mood_snapshot)
    intelligence_context = build_intelligence_prompt_boost(
        user_message,
        context=context,
        emotion=(mood_snapshot or {}).get("last_mood", "neutral"),
        mood=mood_snapshot,
    )
    if not memory_context and not document_context:
        return f"{emotion_context}\n{mood_context}\n{intelligence_context or ''}\nUser question: {user_message}"

    sections = []
    if memory_context:
        sections.append(memory_context)
    if document_context:
        sections.append(document_context)
    combined_context = "\n\n".join(sections)

    guidance = (
        "Answer clearly using the provided context when relevant. Keep it natural and easy to read. "
        "If the attached document does not contain the answer, say that briefly."
        if document_context
        else "Answer clearly, keep it natural, and use the saved memory only when it helps the user."
    )
    return (
        f"{combined_context}\n\n"
        f"{emotion_context}\n"
        f"{mood_context}\n"
        f"{intelligence_context or ''}\n"
        f"User question: {user_message}\n"
        f"{guidance}"
    )


def _load_contact_preview(limit=6):
    if not os.path.exists(GOOGLE_CONTACTS_CACHE_PATH):
        return []
    try:
        with open(GOOGLE_CONTACTS_CACHE_PATH, "r", encoding="utf-8") as file:
            contacts = json.load(file)
    except Exception:
        return []

    preview = []
    seen = set()
    for contact in contacts:
        name = _compact_text(contact.get("display_name") or "")
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        preview.append(name)
        if len(preview) >= limit:
            break
    return preview


def _capture_command_reply(command):
    result = execute_command(
        command,
        installed_apps=_installed_apps,
        input_mode="text",
        source="web-api",
    )
    return result.messages or ["Command completed."]


def _is_risky_command(command):
    lowered = _compact_text(command).lower()
    risky_terms = [
        "delete ",
        "remove ",
        "shutdown",
        "restart",
        "format",
        "emergency protocol",
        "send emergency alert",
        "disable ",
        "clear ",
    ]
    return any(term in lowered for term in risky_terms)


def _create_confirmation(command, source="command"):
    confirmation_id = str(uuid.uuid4())
    _pending_confirmations[confirmation_id] = {
        "command": command,
        "source": source,
        "created_at": _utc_now(),
    }
    return confirmation_id


def _looks_like_tool_command(command):
    cleaned = _compact_text(command)
    lowered = cleaned.lower()
    if not cleaned:
        return False
    if len(cleaned) > 120:
        return False
    if any(phrase in lowered for phrase in ["this ensures", "to the user", "confirmation of service", "please confirm before"]):
        return False
    action_roots = (
        "add ", "create ", "open ", "close ", "start ", "stop ", "show ", "tell ",
        "set ", "enable ", "disable ", "clear ", "delete ", "remove ", "plan ",
        "search ", "scan ", "detect ", "count ", "watch ", "use ", "save ",
        "list ", "rename ", "export ", "summarize ", "read ", "what ", "is ",
    )
    return lowered.startswith(action_roots)


def _looks_like_direct_action_input(message):
    return looks_like_command_input(message)


def _execute_tool_command_for_chat(command, source="chat-tool"):
    if _is_risky_command(command):
        return (
            f"I can do that, but I need confirmation first: {command}",
            command,
            [],
            _create_confirmation(command, source=source),
        )

    tool_messages = _capture_command_reply(command)
    if not tool_messages:
        return "Command completed.", command, [], None
    if len(tool_messages) == 1:
        return tool_messages[0], command, tool_messages, None
    return " ".join(tool_messages), command, tool_messages, None


def _run_tool_aware_reply(history, user_message, raw_user_message=None, mood_snapshot=None, context="casual"):
    source_message = _compact_text(raw_user_message or user_message)
    model_name = _active_chat_model()
    if _looks_like_direct_action_input(source_message):
        command = source_message
        return _execute_tool_command_for_chat(command, source="chat-direct")

    first_pass = generate_chat_reply(
        history,
        user_message,
        model=model_name,
        system_prompt=_effective_system_prompt(source_message, mood_snapshot=mood_snapshot, context=context),
    )
    if _chat_settings.get("tool_mode") and first_pass.startswith("TOOL:"):
        command = _compact_text(first_pass.replace("TOOL:", "", 1))
        if not _looks_like_tool_command(command):
            return command or first_pass, None, [], None
        command_reply, tool_command, tool_messages, confirmation_id = _execute_tool_command_for_chat(
            command,
            source="chat-tool",
        )
        if confirmation_id:
            return command_reply, tool_command, tool_messages, confirmation_id
        tool_summary = "\n".join(tool_messages) or command_reply
        bridge_message = (
            f"User request: {user_message}\n"
            f"Tool command used: {command}\n"
            f"Tool result: {tool_summary}\n"
            "Now answer the user naturally using that result."
        )
        final_reply = generate_chat_reply(
            history,
            bridge_message,
            model=model_name,
            system_prompt=_effective_system_prompt(source_message, mood_snapshot=mood_snapshot, context=context),
        )
        return final_reply, command, tool_messages, None
    return first_pass, None, [], None


def _set_voice_state(activity=None, transcript=None, error=None):
    global _voice_activity, _voice_transcript, _voice_error
    if activity is not None:
        _voice_activity = activity
    if transcript is not None:
        _voice_transcript = transcript
    if error is not None:
        _voice_error = error


def _push_voice_messages(messages):
    global _voice_messages, _voice_last_reply
    cleaned = [_compact_text(item) for item in (messages or []) if _compact_text(item)]
    if not cleaned:
        return
    for item in reversed(cleaned):
        if item.startswith("Grandpa : "):
            _voice_last_reply = item.replace("Grandpa : ", "", 1)
            break
    _voice_messages = (_voice_messages + cleaned)[-12:]


def _set_voice_follow_up(seconds):
    global _voice_follow_up_until, _voice_state_label
    _voice_follow_up_until = max(0.0, seconds)
    _voice_state_label = "follow_up" if seconds > 0 else "sleeping"


def _voice_follow_up_remaining():
    return max(0, int(_voice_follow_up_until - datetime.datetime.now().timestamp()))


def _voice_duplicate_window_seconds():
    try:
        return max(0.5, float(get_setting("voice.duplicate_command_window_seconds", 4.0) or 4.0))
    except Exception:
        return 4.0


def _is_duplicate_voice_command(heard):
    normalized = normalize_phrase(heard)
    if not normalized or not _voice_last_command_key or not _voice_last_command_at_ts:
        return False
    if normalized != _voice_last_command_key:
        return False
    return (time.time() - _voice_last_command_at_ts) <= _voice_duplicate_window_seconds()


def _should_ack_wake():
    global _voice_last_wake_ack_at
    try:
        cooldown = max(0.0, float(get_setting("voice.wake_ack_cooldown_seconds", 2.5) or 2.5))
    except Exception:
        cooldown = 2.5
    now = time.time()
    if cooldown and _voice_last_wake_ack_at and (now - _voice_last_wake_ack_at) < cooldown:
        return False
    _voice_last_wake_ack_at = now
    return True


def _handle_voice_command(heard, follow_up_timeout, source="direct"):
    global _voice_state_label
    speaking_hold = max(0.0, min(1.0, float(get_setting("voice.speaking_state_hold_seconds", 0.3) or 0.3)))
    _mark_voice_command(heard, source)
    _set_voice_state(activity="Thinking", transcript=f"Heard: {heard}", error="")
    replies = _capture_command_reply(heard)
    preview = _compact_text(replies[0]) if replies else "Done."
    _voice_state_label = "speaking"
    _set_voice_state(activity="Speaking", transcript=f"Replying: {preview}", error="")
    if speaking_hold > 0:
        time.sleep(speaking_hold)
    _push_voice_messages([f"You : {heard}", *[f"Grandpa : {reply}" for reply in replies]])
    if continuous_conversation_enabled():
        _set_voice_follow_up(datetime.datetime.now().timestamp() + follow_up_timeout)
        _voice_state_label = "follow_up"
        _set_voice_state(activity="Follow-up", transcript="Listening for follow-up command...", error="")
    else:
        wake_word = _compact_text(get_setting("wake_word", "hey grandpa")) or "hey grandpa"
        _set_voice_follow_up(0.0)
        _voice_state_label = "sleeping"
        _set_voice_state(activity="Sleeping", transcript=f"Say {wake_word} to wake me.", error="")


def _voice_loop():
    global _voice_enabled, _voice_state_label
    wake_retry_until = 0.0
    while _voice_enabled:
        error_backoff = 0.8
        try:
            settings = _active_voice_settings()
            wake_word = _compact_text(get_setting("wake_word", "hey grandpa")) or "hey grandpa"
            follow_up_timeout = float(settings.get("follow_up_timeout_seconds", 12) or 12)
            wake_retry_window = float(settings.get("wake_retry_window_seconds", 6) or 6)
            wake_direct_fallback = bool(settings.get("wake_direct_fallback_enabled", True))
            post_wake_pause = max(0.0, min(1.0, float(settings.get("post_wake_pause_seconds", 0.35) or 0.35)))
            interrupt_follow_up_seconds = max(
                2.0, min(15.0, float(settings.get("interrupt_follow_up_seconds", 5) or 5))
            )
            interrupt_hold = max(0.0, min(1.0, float(get_setting("voice.interrupt_state_hold_seconds", 0.35) or 0.35)))
            error_backoff = max(0.1, min(3.0, float(settings.get("error_recovery_backoff_seconds", 0.8) or 0.8)))
            now_ts = datetime.datetime.now().timestamp()
            follow_up_active = _voice_follow_up_until > now_ts

            if follow_up_active:
                _voice_state_label = "follow_up"
                _set_voice_state(
                    activity="Follow-up",
                    transcript=f"Listening for follow-up... {_voice_follow_up_remaining()}s left",
                    error="",
                )
                heard = listen(for_wake_word=False, for_follow_up=True)
            else:
                _voice_state_label = "sleeping"
                _set_voice_state(activity="Sleeping", transcript=f"Say {wake_word} to wake me.", error="")
                heard = listen(for_wake_word=True)

            if not _voice_enabled:
                break
            if not heard:
                continue
            if follow_up_active:
                heard = sanitize_follow_up_command(heard)
                if not heard:
                    continue
            _mark_voice_heard(heard)

            if is_interrupt_phrase(heard):
                voice_speak_module.stop_speaking()
                _mark_voice_interrupt()
                _set_voice_follow_up(datetime.datetime.now().timestamp() + interrupt_follow_up_seconds)
                _voice_state_label = "interrupted"
                _set_voice_state(activity="Interrupted", transcript="Stopped speaking. Listening again.", error="")
                if interrupt_hold > 0:
                    time.sleep(interrupt_hold)
                continue

            if follow_up_active:
                if is_follow_up_keepalive_phrase(heard):
                    keep_alive_until = datetime.datetime.now().timestamp() + follow_up_keep_alive_seconds()
                    _set_voice_follow_up(keep_alive_until)
                    _voice_state_label = "follow_up"
                    _set_voice_state(activity="Follow-up", transcript="Keeping the conversation open.", error="")
                    continue
                if wake_word_detected(heard, wake_word):
                    trailing_follow_up = strip_wake_word(heard, wake_word)
                    if trailing_follow_up and not is_wake_only_phrase(heard, wake_word):
                        if _is_duplicate_voice_command(trailing_follow_up):
                            _mark_voice_ignored(trailing_follow_up, "duplicate")
                            _set_voice_follow_up(datetime.datetime.now().timestamp() + follow_up_timeout)
                            continue
                        _handle_voice_command(trailing_follow_up, follow_up_timeout, source="follow_up")
                    else:
                        _set_voice_follow_up(datetime.datetime.now().timestamp() + follow_up_timeout)
                        _voice_state_label = "awake"
                        _set_voice_state(activity="Awake", transcript="Listening for your command.", error="")
                    continue
                if _is_duplicate_voice_command(heard):
                    _mark_voice_ignored(heard, "duplicate")
                    _set_voice_follow_up(datetime.datetime.now().timestamp() + follow_up_timeout)
                    _set_voice_state(activity="Follow-up", transcript="Ignoring duplicate command. Listening again.", error="")
                    continue
                _handle_voice_command(heard, follow_up_timeout, source="follow_up")
                continue

            if wake_word_detected(heard, wake_word):
                trailing_command = strip_wake_word(heard, wake_word)
                wake_retry_until = datetime.datetime.now().timestamp() + wake_retry_window
                _mark_voice_wake(wake_retry_until)
                if trailing_command and not is_wake_only_phrase(heard, wake_word):
                    if _is_duplicate_voice_command(trailing_command):
                        _mark_voice_ignored(trailing_command, "duplicate")
                        continue
                    _handle_voice_command(trailing_command, follow_up_timeout, source="wake_inline")
                else:
                    _voice_diagnostics["wake_only_count"] += 1
                    _set_voice_follow_up(datetime.datetime.now().timestamp() + follow_up_timeout)
                    _voice_state_label = "awake"
                    _set_voice_state(activity="Awake", transcript="Wake word heard. Listening now.", error="")
                    if _should_ack_wake():
                        voice_speak_module.speak("Yes?")
                    if post_wake_pause > 0:
                        time.sleep(post_wake_pause)
                continue

            if wake_retry_until and datetime.datetime.now().timestamp() <= wake_retry_until and should_run_direct_fallback(heard):
                if _is_duplicate_voice_command(heard):
                    _mark_voice_ignored(heard, "duplicate")
                    continue
                _handle_voice_command(heard, follow_up_timeout, source="retry_window")
                continue

            if wake_direct_fallback and should_run_direct_fallback(heard):
                if _is_duplicate_voice_command(heard):
                    _mark_voice_ignored(heard, "duplicate")
                    continue
                _handle_voice_command(heard, follow_up_timeout, source="direct_fallback")
                continue
        except Exception as error:
            _voice_state_label = "error"
            _mark_voice_error(str(error))
            _set_voice_follow_up(0.0)
            _set_voice_state(activity="Error", transcript="Recovering voice listener...", error=str(error))
            time.sleep(error_backoff)
            _mark_voice_recovery()
            if _voice_enabled:
                wake_word = _compact_text(get_setting("wake_word", "hey grandpa")) or "hey grandpa"
                _voice_state_label = "sleeping"
                _set_voice_state(activity="Sleeping", transcript=f"Say {wake_word} to wake me.", error="")
    _set_voice_follow_up(0.0)
    _voice_state_label = "ready"
    _set_voice_state(activity="Ready", transcript="" if not _voice_enabled else _voice_transcript)


def _ensure_voice_thread():
    global _voice_thread
    if _voice_thread and _voice_thread.is_alive():
        return
    _voice_thread = threading.Thread(target=_voice_loop, daemon=True)
    _voice_thread.start()


def _voice_status_payload():
    wake_word = _compact_text(get_setting("wake_word", "hey grandpa")) or "hey grandpa"
    settings = _active_voice_settings()
    return {
        "enabled": _voice_enabled,
        "activity": _voice_activity,
        "state_label": _voice_state_label,
        "wake_word": wake_word,
        "voice_profile": current_voice_mode(),
        "stt": stt_backend_payload(),
        "tts": voice_speak_module.tts_backend_payload(),
        "follow_up_active": _voice_follow_up_until > datetime.datetime.now().timestamp(),
        "follow_up_remaining": _voice_follow_up_remaining(),
        "transcript": _voice_transcript,
        "error": _voice_error,
        "messages": _voice_messages[-8:],
        "last_reply": _voice_last_reply,
        "settings": settings,
        "diagnostics": _voice_diagnostics_payload(),
    }


def start_voice_api_mode():
    global _voice_enabled, _voice_state_label
    with _voice_lock:
        wake_word = _compact_text(get_setting("wake_word", "hey grandpa")) or "hey grandpa"
        _voice_enabled = True
        _voice_state_label = "sleeping"
        _set_voice_follow_up(0.0)
        _reset_voice_diagnostics()
        _set_voice_state(activity="Sleeping", transcript=f"Say {wake_word} to wake me.", error="")
        _ensure_voice_thread()
    return _voice_status_payload()


def stop_voice_api_mode():
    global _voice_enabled, _voice_state_label
    with _voice_lock:
        _voice_enabled = False
        _set_voice_follow_up(0.0)
        _voice_state_label = "ready"
        voice_speak_module.stop_speaking()
        _set_voice_state(activity="Ready", transcript="", error="")
    return _voice_status_payload()


def _build_ui_state(auth_context: dict | None = None):
    if not ASSISTANT_RUNTIME.status_payload().get("running"):
        ASSISTANT_RUNTIME.start()
    task_data = _safe_call(get_task_data, {"tasks": [], "reminders": []})
    event_data = _safe_call(get_event_data, {"events": []})
    tasks = task_data.get("tasks", [])
    reminders = task_data.get("reminders", [])
    events = event_data.get("events", [])
    pending_tasks = sum(1 for task in tasks if not task.get("completed"))
    overdue_count = 0
    due_today_count = 0
    upcoming_count = 0
    now = datetime.datetime.now()
    reminder_timeline = {"overdue": [], "today": [], "upcoming": []}

    for reminder in reminders:
        due_at = reminder.get("due_at")
        due_date = reminder.get("due_date")
        due_dt = None
        if due_at:
            try:
                due_dt = datetime.datetime.fromisoformat(due_at)
            except ValueError:
                due_dt = None
        if due_dt is None and due_date:
            try:
                due_dt = datetime.datetime.combine(
                    datetime.date.fromisoformat(due_date),
                    datetime.time(hour=9, minute=0),
                )
            except ValueError:
                due_dt = None
        if not due_dt:
            continue

        title = _compact_text(reminder.get("title") or reminder.get("text") or reminder.get("task") or "Reminder")
        timeline_label = f"{title} - {due_dt.strftime('%d %b %I:%M %p')}"
        if due_dt < now:
            overdue_count += 1
            reminder_timeline["overdue"].append(timeline_label)
        elif due_dt.date() == now.date():
            due_today_count += 1
            reminder_timeline["today"].append(timeline_label)
        elif due_dt.date() <= (now.date() + datetime.timedelta(days=7)):
            upcoming_count += 1
            reminder_timeline["upcoming"].append(timeline_label)

    upcoming_events = sorted(
        [event for event in events if event.get("date")],
        key=lambda item: (item.get("date", ""), item.get("time", "")),
    )
    next_event = upcoming_events[0]["title"] if upcoming_events else "No upcoming events."
    pending_task_titles = [
        _compact_text(task.get("title") or task.get("task") or "Untitled task")
        for task in tasks
        if not task.get("completed")
    ][:5]
    overdue_reminders = reminder_timeline["overdue"][:5]

    event_titles = []
    for event in upcoming_events[:5]:
        title = _compact_text(event.get("title") or "Untitled event")
        date_text = _compact_text(event.get("date") or "")
        time_text = _compact_text(event.get("time") or "")
        suffix = " ".join(part for part in [date_text, time_text] if part)
        event_titles.append(f"{title} - {suffix}".strip(" -"))

    note_summary = _safe_call(latest_note, "No saved notes yet.")
    recent_commands = _safe_call(lambda: get_recent_commands(limit=5), [])
    preferred_language = _safe_call(lambda: get_memory("preferences.language"), None) or "Not set"
    favorite_contact = _safe_call(lambda: get_memory("personal.relationships.favorite_contact"), None) or "Not set"
    wake_word = _safe_call(lambda: get_setting("wake_word", "hey grandpa"), "hey grandpa")
    voice_profile = _safe_call(lambda: get_setting("voice.mode", "normal"), "normal")
    contacts_preview = _safe_call(_load_contact_preview, [])
    aliases_summary = _safe_call(list_contact_aliases, "I do not have any saved contact aliases yet.")
    favorites_summary = _safe_call(list_favorite_contacts, "You do not have any favorite contacts yet.")
    recent_contact_changes = _safe_call(get_recent_contact_change_summary, "No recent Google contact changes.")
    focus_snapshot = _safe_call(
        lambda: get_planner_focus_snapshot(limit=5),
        {
            "summary": "Planner snapshot unavailable right now.",
            "focus_suggestions": [],
            "reminder_timeline": {"overdue": [], "today": [], "upcoming": []},
        },
    )
    notifications = []

    if overdue_count:
        notifications.append({"level": "warning", "text": f"You have {overdue_count} overdue reminder(s)."})
    if due_today_count:
        notifications.append({"level": "warning", "text": f"You have {due_today_count} reminder(s) due today."})
    if pending_tasks:
        notifications.append({"level": "info", "text": f"{pending_tasks} pending task(s) need attention."})
    if next_event and next_event != "No upcoming events.":
        notifications.append({"level": "info", "text": f"Next event: {next_event}"})
    if _voice_error:
        notifications.append({"level": "error", "text": f"Voice issue: {_compact_text(_voice_error)}"})

    focus_mode = _safe_call(lambda: get_setting("assistant.focus_mode_enabled", False), False)
    proactive_state = _proactive_state_payload(focus_mode)
    if not focus_mode:
        for item in proactive_state.get("suggestions", [])[:2]:
            notifications.append({"level": "suggestion", "text": item["text"]})

    automation_tick = _safe_call(
        lambda: run_due_automation_rules(force=False),
        {"checked": 0, "executed": [], "failed": [], "skipped": []},
    )
    for item in (automation_tick.get("executed") or [])[:2]:
        notifications.append(
            {
                "level": "info",
                "text": (
                    f"Automation ran: {item.get('rule', 'automation')} "
                    f"- {item.get('message', 'completed')}"
                ),
            }
        )

    nextgen_state = _safe_call(
        nextgen_status_snapshot,
        {
            "day_plan_summary": "No AI day plan generated yet.",
            "habits_count": 0,
            "goals_count": 0,
            "milestones_done": 0,
            "milestones_total": 0,
            "meetings_count": 0,
            "rag_docs_count": 0,
            "automation_total": 0,
            "automation_enabled": 0,
            "language_mode": "auto",
            "voice_mode": "normal",
            "mobile_enabled": False,
            "mobile_device": "",
            "highlights": [],
        },
    )
    doctor_state = collect_startup_diagnostics()
    semantic_memory_state = semantic_memory_status(prewarm=False)
    runtime_state = ASSISTANT_RUNTIME.status_payload()
    intelligence_state = intelligence_status_payload(runtime_state)
    proactive_conversation = intelligence_state.get("proactive_conversation", {})
    if proactive_conversation.get("suggestion") and not focus_mode:
        notifications.append({"level": "suggestion", "text": proactive_conversation["suggestion"]})
    hardware_state = _safe_call(
        DEVICE_MANAGER.get_status,
        {
            "ok": False,
            "device_count": 0,
            "devices": [],
            "recent_events": [],
            "capabilities": {"summary": "Hardware status unavailable."},
        },
    )
    mobile_state = _safe_call(
        MOBILE_COMPANION.status_payload,
        {
            "enabled": True,
            "pairing": {"active": False, "code": "", "requested_name": "", "expires_in_seconds": 0, "lan_addresses": []},
            "paired_devices": [],
            "paired_count": 0,
            "active_connections": 0,
            "event_history_count": 0,
            "notification_count": 0,
            "lan_addresses": [],
            "summary": "Mobile companion status unavailable.",
        },
    )
    if mobile_state.get("paired_count", 0) > 0:
        nextgen_state["mobile_enabled"] = True
        if not nextgen_state.get("mobile_device"):
            first_device = (mobile_state.get("paired_devices") or [{}])[0]
            nextgen_state["mobile_device"] = _compact_text(first_device.get("name"))
    auth_user = (auth_context or {}).get("user") if isinstance(auth_context, dict) else None
    auth_user_id = None
    try:
        auth_user_id = int(auth_user.get("id")) if auth_user and auth_user.get("id") is not None else None
    except Exception:
        auth_user_id = None
    auth_preferences = get_user_preferences(auth_user_id) if auth_user_id is not None else {}

    return {
        "overview": {
            "tasks": f"{pending_tasks} pending",
            "reminders": f"{overdue_count} overdue | {due_today_count} today",
            "weather": _safe_call(get_weather_report, "Weather unavailable right now."),
            "health": _safe_call(get_system_status, "Health unavailable right now."),
            "object_detection": _safe_call(get_latest_detection_summary, "No recent object detection results yet."),
        },
        "today": (
            f"Pending tasks: {pending_tasks} | Overdue reminders: {overdue_count} | "
            f"Due today: {due_today_count} | Next 7 days: {upcoming_count}"
        ),
        "next_event": next_event,
        "latest_note": note_summary,
        "recent_commands": recent_commands,
        "notifications": notifications[:6],
        "dashboard": {
            "tasks": pending_task_titles or ["No pending tasks."],
            "reminders": overdue_reminders or ["No overdue reminders."],
            "events": event_titles or ["No upcoming events."],
            "vision": [_safe_call(get_latest_detection_summary, "No recent object detection results yet.")],
            "focus_summary": focus_snapshot.get("summary") or "Planner snapshot unavailable.",
            "focus_suggestions": focus_snapshot.get("focus_suggestions") or [],
            "reminder_timeline": focus_snapshot.get("reminder_timeline") or reminder_timeline,
            "nextgen_highlights": nextgen_state.get("highlights") or [],
        },
        "memory": {
            "preferred_language": preferred_language,
            "favorite_contact": favorite_contact,
            "semantic": semantic_memory_state,
            "mood": mood_status_payload(),
        },
        "intelligence": intelligence_state,
        "settings": {
            "wake_word": wake_word,
            "voice_profile": voice_profile,
            "voice_popup_enabled": get_setting("voice.desktop_popup_enabled", True),
            "voice_chime_enabled": get_setting("voice.desktop_chime_enabled", True),
            "offline_mode": get_setting("assistant.offline_mode_enabled", False),
            "developer_mode": _safe_call(lambda: get_setting("assistant.developer_mode_enabled", False), False),
            "emergency_mode": _safe_call(lambda: get_setting("assistant.emergency_mode_enabled", False), False),
            "focus_mode": focus_mode,
        },
        "proactive": proactive_state,
        "contacts": {
            "favorite_contact": favorite_contact,
            "preview": contacts_preview or ["No synced contacts yet."],
            "aliases_summary": aliases_summary,
            "favorites_summary": favorites_summary,
            "recent_changes": recent_contact_changes,
        },
        "integrations": {
            "hardware": hardware_state,
            "mobile": mobile_state,
            "smart_home": _smart_home_status_payload(),
            "face_security": _face_security_payload(),
            "security": security_status_payload(DEVICE_MANAGER),
            "plugins": plugin_status_payload(),
        },
        "auth": {
            "authenticated": bool(auth_user),
            "user": auth_user,
            "bootstrap": auth_bootstrap_status(),
            "preferences": auth_preferences,
        },
        "runtime": runtime_state,
        "emergency": {
            "location": _safe_call(lambda: get_memory("personal.contact.address"), None)
            or _safe_call(lambda: get_memory("personal.location.current_location.city"), None)
            or "No saved location.",
            "contact": _safe_call(lambda: get_memory("personal.contact.emergency_contact.name"), None) or "Not set",
            "mode_enabled": _safe_call(lambda: get_setting("assistant.emergency_mode_enabled", False), False),
            "protocol_summary": "Alert, location share, and contact call shortcuts are ready.",
        },
        "startup": {
            "auto_launch_enabled": _safe_call(lambda: get_setting("startup.auto_launch_enabled", False), False),
            "tray_mode": _safe_call(lambda: get_setting("startup.tray_mode", False), False),
            "summary": _safe_call(startup_auto_launch_status, "Startup status unavailable right now."),
            "portable_setup_ready": os.path.exists(os.path.join(PROJECT_ROOT, "scripts", "windows", "setup_portable_desktop.cmd")),
            "react_ui_on_tray_enabled": _safe_call(lambda: get_setting("startup.react_ui_on_tray_enabled", False), False),
            "react_ui_on_tray_mode": _safe_call(lambda: get_setting("startup.react_ui_on_tray_mode", "browser"), "browser"),
            "react_frontend_ready": os.path.exists(os.path.join(PROJECT_ROOT, "scripts", "windows", "start_react_frontend.cmd")),
            "react_desktop_ready": os.path.exists(os.path.join(PROJECT_ROOT, "scripts", "windows", "start_react_electron.cmd")),
        },
        "doctor": doctor_state,
        "voice": _voice_status_payload(),
        "chat_settings": _chat_settings,
        "chat_sessions": _ordered_sessions()[:10],
        "object_watch": _safe_call(get_watch_status, {"active": False, "target": "", "summary": "No object watch is active."}),
        "object_detection": {
            "model_name": _safe_call(get_object_detection_model_name, "yolov8n.pt"),
            "small_object_mode": _safe_call(is_small_object_mode_enabled, False),
            "presets": _safe_call(get_object_detection_presets, []),
            "alert_profile": _safe_call(get_object_detection_alert_profile, "balanced"),
            "watch_alert_cooldown_seconds": _safe_call(get_watch_alert_cooldown_seconds, 8.0),
        },
        "object_history": _safe_call(get_detection_history, []),
        "object_watch_history": _safe_call(get_watch_event_history, []),
        "nextgen": nextgen_state,
        "automation": automation_tick,
    }


@app.get("/api/health")
def api_health():
    if not ASSISTANT_RUNTIME.status_payload().get("running"):
        ASSISTANT_RUNTIME.start()
    return {
        "ok": True,
        "service": "grandpa-assistant-api",
        "runtime": ASSISTANT_RUNTIME.status_payload(),
        "semantic_memory": semantic_memory_status(prewarm=False),
        "doctor": collect_startup_diagnostics(),
    }


@app.get("/api/doctor")
def api_doctor():
    return {
        "ok": True,
        "doctor": collect_startup_diagnostics(use_cache=False),
    }


@app.get("/api/ui-state")
def api_ui_state(request: Request):
    auth_context = _authenticated_app_context(request, required=False)
    if _web_ui_auth_required() and not auth_context:
        return {
            "ok": True,
            "state": {
                "auth": {
                    "authenticated": False,
                    "user": None,
                    "bootstrap": auth_bootstrap_status(),
                }
            },
        }
    return {"ok": True, "state": _build_ui_state(auth_context)}


@app.get("/api/auth/bootstrap-status")
def api_auth_bootstrap_status():
    return {"ok": True, "auth": auth_bootstrap_status()}


@app.get("/api/auth/status")
def api_auth_status(request: Request):
    context = _authenticated_app_context(request, required=False)
    return {
        "ok": True,
        "auth": app_auth_status_payload(),
        "current": context,
    }


@app.post("/api/auth/register")
def api_auth_register(request: Request, payload: AuthRegisterRequest):
    try:
        created = register_app_user(
            payload.username,
            payload.password,
            display_name=_compact_text(payload.display_name) or _compact_text(payload.username),
            role=_compact_text(payload.role) or "user",
        )
        session = login_app_user(
            payload.username,
            payload.password,
            user_agent=request.headers.get("user-agent", ""),
            device_name=_compact_text(payload.device_name) or "desktop-ui",
        )
        return {"ok": True, **created, **session}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/auth/login")
def api_auth_login(request: Request, payload: AuthLoginRequest):
    try:
        result = login_app_user(
            payload.username,
            payload.password,
            user_agent=request.headers.get("user-agent", ""),
            device_name=_compact_text(payload.device_name) or "desktop-ui",
        )
        return {"ok": True, **result, "bootstrap": auth_bootstrap_status()}
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@app.post("/api/auth/logout")
def api_auth_logout(request: Request):
    token = _extract_bearer_token(request.headers.get("authorization", ""))
    if not token:
        raise HTTPException(status_code=400, detail="Authorization token is required.")
    logout_app_token(token)
    return {"ok": True}


@app.get("/api/auth/me")
def api_auth_me(request: Request):
    context = _authenticated_app_context(request, required=True)
    return {"ok": True, **context}


@app.get("/api/auth/profile")
def api_auth_profile(request: Request):
    context = _authenticated_app_context(request, required=True)
    return {"ok": True, **_account_profile_payload(context)}


@app.post("/api/auth/profile")
def api_auth_update_profile(request: Request, payload: AuthProfileUpdateRequest):
    context = _authenticated_app_context(request, required=True)
    user = context.get("user") if context else None
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")

    user_id = int(user["id"])
    resolved_display_name = _compact_text(payload.display_name) or user.get("display_name") or user.get("username")
    updated_row = update_user_profile(user_id, display_name=resolved_display_name)
    current_preferences = get_user_preferences(user_id)
    current_preferences.update(_normalize_profile_preferences(payload))
    saved_preferences = update_user_preferences(user_id, current_preferences)
    updated_user = (
        {
            "id": updated_row.get("id"),
            "username": updated_row.get("username"),
            "display_name": updated_row.get("display_name"),
            "role": updated_row.get("role", "user"),
            "is_active": bool(updated_row.get("is_active", 1)),
            "created_at": updated_row.get("created_at", ""),
            "updated_at": updated_row.get("updated_at", ""),
            "last_login_at": updated_row.get("last_login_at", ""),
        }
        if updated_row
        else user
    )
    log_audit_event(
        "auth",
        "profile_updated",
        user_id=user_id,
        payload={"preferences": saved_preferences},
    )
    return {"ok": True, "user": updated_user, "preferences": saved_preferences}


@app.get("/api/auth/users")
def api_auth_users(request: Request):
    context = _authenticated_app_context(request, required=True)
    try:
        require_admin(context)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return {"ok": True, "users": app_auth_status_payload().get("users", [])}


@app.get("/api/auth/audit")
def api_auth_audit(request: Request, limit: int = 80):
    context = _authenticated_app_context(request, required=True)
    try:
        user = require_admin(context)
        return {"ok": True, "items": get_app_audit_log(limit=limit), "user": user}
    except PermissionError:
        user = context.get("user") if context else None
        user_id = int(user.get("id")) if user and user.get("id") is not None else None
        return {"ok": True, "items": get_app_audit_log(user_id=user_id, limit=limit), "user": user}


@app.get("/api/auth/chat-archive")
def api_auth_chat_archive(request: Request, session_id: str | None = None, limit: int = 120):
    context = _authenticated_app_context(request, required=True)
    user = context.get("user") if context else None
    user_id = int(user.get("id")) if user and user.get("id") is not None else None
    return {
        "ok": True,
        "items": list_chat_archive(session_id=session_id, user_id=user_id, limit=limit),
    }


@app.get("/api/memory/status")
def api_memory_status():
    return {
        "ok": True,
        "memory": semantic_memory_status(prewarm=False),
    }


@app.post("/api/memory/search")
def api_memory_search(request: ChatRequest):
    query = _compact_text(request.message)
    if not query:
        raise HTTPException(status_code=400, detail="Message is required.")
    return {
        "ok": True,
        "query": query,
        "results": search_semantic_memory(query, limit=5),
        "memory": semantic_memory_status(prewarm=True),
    }


@app.get("/api/voice/status")
def api_voice_status():
    return {"ok": True, "voice": _voice_status_payload()}


@app.get("/api/settings/startup")
def api_startup_status():
    return {"ok": True, "startup": _build_ui_state()["startup"]}


@app.post("/api/voice/start")
def api_voice_start():
    return {"ok": True, "voice": start_voice_api_mode()}


@app.post("/api/voice/stop")
def api_voice_stop():
    return {"ok": True, "voice": stop_voice_api_mode()}


@app.post("/api/settings/startup")
def api_update_startup(request: StartupSettingsRequest):
    try:
        if request.tray_mode is not None:
            update_setting("startup.tray_mode", bool(request.tray_mode))
        if request.auto_launch_enabled is True:
            message = enable_startup_auto_launch()
        elif request.auto_launch_enabled is False:
            message = disable_startup_auto_launch()
        else:
            message = startup_auto_launch_status()
        return {"ok": True, "message": message, "startup": _build_ui_state()["startup"]}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Startup settings error: {error}") from error


class FocusModeRequest(BaseModel):
    enabled: bool

@app.post("/api/settings/focus_mode")
def api_update_focus_mode(request: FocusModeRequest):
    try:
        update_setting("assistant.focus_mode_enabled", request.enabled)
        mode_str = "ON" if request.enabled else "OFF"
        return {"ok": True, "focus_mode": request.enabled, "state": _build_ui_state(), "message": f"Focus Mode turned {mode_str}."}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Focus settings error: {error}") from error



@app.post("/api/proactive/refresh")
def api_refresh_proactive():
    try:
        suggestions = generate_proactive_suggestions("default")
        return {
            "ok": True,
            "suggestions": suggestions,
            "state": _build_ui_state(),
            "message": "Proactive suggestions refreshed.",
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Proactive refresh error: {error}") from error


@app.post("/api/settings/portable-setup")
def api_portable_setup(request: PortableSetupRequest):
    action = _compact_text(request.action) or "desktop"
    script_path = os.path.join(PROJECT_ROOT, "scripts", "windows", "setup_portable_desktop.cmd")
    if not os.path.exists(script_path):
        raise HTTPException(status_code=404, detail="Portable setup helper not found.")
    try:
        args = [script_path]
        if action == "startup-on":
            args.append("/startup-on")
        elif action == "startup-off":
            args.append("/startup-off")
        subprocess.run(args, cwd=PROJECT_ROOT, check=True, shell=True)
        message = {
            "startup-on": "Portable app startup shortcut enabled.",
            "startup-off": "Portable app startup shortcut disabled.",
        }.get(action, "Portable app desktop shortcut created.")
        return {"ok": True, "message": message, "startup": _build_ui_state()["startup"]}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Portable setup error: {error}") from error


@app.post("/api/command")
def api_command(request: CommandRequest, http_request: Request = None):
    _enforce_app_auth(http_request)
    command = _compact_text(request.command)
    user_id = _authenticated_user_id(http_request)
    if request.confirmation_id:
        pending = _pending_confirmations.pop(request.confirmation_id, None)
        if not pending:
            raise HTTPException(status_code=404, detail="Confirmation expired or missing.")
        command = pending["command"]
    if not command:
        raise HTTPException(status_code=400, detail="Command is required.")
    if not request.confirmation_id and _is_risky_command(command):
        confirmation_id = _create_confirmation(command)
        return {
            "ok": True,
            "requires_confirmation": True,
            "confirmation_id": confirmation_id,
            "command": command,
            "messages": [f"Please confirm before I run: {command}"],
            "state": _build_ui_state(_authenticated_app_context(http_request, required=False)),
        }
    try:
        messages = _capture_command_reply(command)
        log_audit_event(
            "command",
            "executed",
            user_id=user_id,
            payload={"command": command, "message_count": len(messages)},
        )
        MOBILE_COMPANION.record_command_result(command, messages, source="desktop-api")
        return {
            "ok": True,
            "command": command,
            "messages": messages,
            "state": _build_ui_state(_authenticated_app_context(http_request, required=False)),
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Assistant error: {error}") from error


@app.get("/api/mobile/status")
def api_mobile_status(request: Request):
    _require_local_request(request)
    return {"ok": True, "mobile": MOBILE_COMPANION.status_payload()}


@app.post("/api/mobile/pairing/start")
def api_mobile_pairing_start(request: Request, payload: MobilePairStartRequest):
    _require_local_request(request)
    pairing = MOBILE_COMPANION.start_pairing(_compact_text(payload.device_name) or "Grandpa Mobile")
    return {"ok": True, "mobile": MOBILE_COMPANION.status_payload(), "pairing": pairing}


@app.post("/api/mobile/devices/revoke")
def api_mobile_revoke_device(request: Request, payload: MobileRevokeDeviceRequest):
    _require_local_request(request)
    ok, message = MOBILE_COMPANION.revoke_device(payload.device_id)
    if not ok:
        raise HTTPException(status_code=404, detail=message)
    return {"ok": True, "message": message, "mobile": MOBILE_COMPANION.status_payload()}


@app.post("/mobile/pairing/complete")
def mobile_pairing_complete(request: MobilePairCompleteRequest):
    try:
        result = MOBILE_COMPANION.complete_pairing(
            request.pair_code,
            request.device_name,
            platform=request.platform or "",
            app_version=request.app_version or "",
        )
        return {"ok": True, **result, "mobile": MOBILE_COMPANION.status_payload()}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/mobile/auth/token")
def mobile_auth_token(request: MobileTokenAuthRequest):
    device = _mobile_device_from_token(request.token)
    return {"ok": True, "device": device, "mobile": MOBILE_COMPANION.status_payload()}


@app.get("/mobile/me")
def mobile_me(request: Request):
    device = _mobile_device_from_request(request)
    return {"ok": True, "device": device}


@app.get("/mobile/status")
def mobile_status(request: Request):
    device = _mobile_device_from_request(request)
    return {
        "ok": True,
        "device": device,
        "mobile": MOBILE_COMPANION.status_payload(),
        "status": _mobile_runtime_snapshot(),
    }


@app.get("/mobile/dashboard")
def mobile_dashboard(request: Request):
    device = _mobile_device_from_request(request)
    return {"ok": True, "dashboard": _mobile_dashboard_payload(device)}


@app.get("/mobile/notifications")
def mobile_notifications(request: Request, limit: int = 20):
    device = _mobile_device_from_request(request)
    return {
        "ok": True,
        "device": device,
        "items": MOBILE_COMPANION.notifications(limit=limit, device_id=device.get("device_id", "")),
    }


@app.get("/mobile/chat/sessions")
def mobile_chat_sessions(request: Request):
    _mobile_device_from_request(request)
    return {"ok": True, "sessions": _ordered_sessions()}


@app.post("/mobile/chat")
def mobile_chat(request: Request, payload: MobileChatRequest):
    device = _mobile_device_from_request(request)
    result = chat_reply(ChatRequest(message=payload.message, session_id=payload.session_id))
    response = {"ok": True, "device": device, **result}
    response.update(_mobile_audio_reply(result.get("reply", ""), payload.include_audio))
    return response


@app.post("/mobile/command")
def mobile_command(request: Request, payload: MobileCommandRequest):
    device = _mobile_device_from_request(request)
    MOBILE_COMPANION.note_command(device.get("device_id", ""), payload.command)
    result = api_command(CommandRequest(command=payload.command, confirmation_id=payload.confirmation_id))
    if result.get("messages"):
        MOBILE_COMPANION.record_command_result(
            payload.command,
            result.get("messages") or [],
            source=device.get("name", "mobile"),
            target_device_ids=[device.get("device_id", "")],
        )
    if not payload.include_state:
        result = {key: value for key, value in result.items() if key != "state"}
    return {"ok": True, "device": device, **result}


@app.post("/mobile/voice/transcribe")
async def mobile_voice_transcribe(
    request: Request,
    file: UploadFile = File(...),
):
    _mobile_device_from_request(request)
    suffix = os.path.splitext(_compact_text(file.filename) or "voice.wav")[1] or ".wav"
    fd, temp_path = tempfile.mkstemp(prefix="mobile_voice_", suffix=suffix, dir=DATA_DIR)
    os.close(fd)
    try:
        with open(temp_path, "wb") as handle:
            handle.write(await file.read())
        transcript = _transcribe_mobile_audio_file(temp_path)
        return {"ok": True, "transcript": transcript}
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Could not transcribe audio: {error}") from error
    finally:
        with contextlib.suppress(OSError):
            os.remove(temp_path)


@app.post("/mobile/voice/chat")
async def mobile_voice_chat(
    request: Request,
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
    include_audio: bool = Form(default=True),
):
    device = _mobile_device_from_request(request)
    suffix = os.path.splitext(_compact_text(file.filename) or "voice.wav")[1] or ".wav"
    fd, temp_path = tempfile.mkstemp(prefix="mobile_voice_chat_", suffix=suffix, dir=DATA_DIR)
    os.close(fd)
    try:
        with open(temp_path, "wb") as handle:
            handle.write(await file.read())
        transcript = _transcribe_mobile_audio_file(temp_path)
        result = chat_reply(ChatRequest(message=transcript, session_id=session_id))
        response = {
            "ok": True,
            "device": device,
            "transcript": transcript,
            **result,
        }
        response.update(_mobile_audio_reply(result.get("reply", ""), include_audio))
        return response
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"Could not process mobile voice chat: {error}") from error
    finally:
        with contextlib.suppress(OSError):
            os.remove(temp_path)


@app.websocket("/mobile/ws")
async def mobile_websocket(websocket: WebSocket):
    token = _extract_bearer_token(websocket.query_params.get("token", ""))
    device = MOBILE_COMPANION.authenticate_token(token)
    if not device:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    device_id = device.get("device_id", "")
    MOBILE_COMPANION.note_connection(device_id, True)
    last_seq = 0
    await websocket.send_json(
        {
            "type": "ready",
            "device": device,
            "mobile": MOBILE_COMPANION.status_payload(),
            "dashboard": _mobile_dashboard_payload(device),
        }
    )

    try:
        while True:
            try:
                incoming = await asyncio.wait_for(websocket.receive_json(), timeout=0.8)
            except asyncio.TimeoutError:
                incoming = None

            if incoming:
                message_type = _compact_text(incoming.get("type")).lower()
                if message_type == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": _utc_now()})
                elif message_type == "status":
                    await websocket.send_json({"type": "status", "dashboard": _mobile_dashboard_payload(device)})
                elif message_type == "chat":
                    payload = MobileChatRequest(
                        message=_compact_text(incoming.get("message")),
                        session_id=_compact_text(incoming.get("session_id")) or None,
                        include_audio=bool(incoming.get("include_audio", False)),
                    )
                    result = chat_reply(ChatRequest(message=payload.message, session_id=payload.session_id))
                    if payload.include_audio:
                        result = {**result, **_mobile_audio_reply(result.get("reply", ""), True)}
                    await websocket.send_json({"type": "chat.result", "result": result})
                elif message_type == "command":
                    payload = MobileCommandRequest(
                        command=_compact_text(incoming.get("command")),
                        confirmation_id=_compact_text(incoming.get("confirmation_id")) or None,
                        include_state=bool(incoming.get("include_state", True)),
                    )
                    MOBILE_COMPANION.note_command(device_id, payload.command)
                    result = api_command(CommandRequest(command=payload.command, confirmation_id=payload.confirmation_id))
                    if result.get("messages"):
                        MOBILE_COMPANION.record_command_result(
                            payload.command,
                            result.get("messages") or [],
                            source=device.get("name", "mobile"),
                            target_device_ids=[device_id],
                        )
                    if not payload.include_state:
                        result = {key: value for key, value in result.items() if key != "state"}
                    await websocket.send_json({"type": "command.result", "result": result})

            for event in MOBILE_COMPANION.events_since(last_seq, device_id=device_id):
                await websocket.send_json({"type": "event", "event": event})
                last_seq = max(last_seq, int(event.get("seq", 0) or 0))
    except WebSocketDisconnect:
        pass
    finally:
        MOBILE_COMPANION.note_connection(device_id, False)


@app.get("/chat/settings")
def get_chat_settings(request: Request):
    _enforce_app_auth(request)
    return {"ok": True, "settings": {**_chat_settings, "active_model": _active_chat_model(), "llm_status": get_llm_status()}}


@app.post("/chat/settings")
def update_chat_settings(request: ChatSettingsRequest, http_request: Request):
    _enforce_app_auth(http_request)
    if request.llm_provider is not None:
        provider = _compact_text(request.llm_provider).lower()
        _chat_settings["llm_provider"] = provider if provider in {"auto", "openai", "ollama"} else DEFAULT_LLM_PROVIDER
    if request.model is not None:
        _chat_settings["model"] = _compact_text(request.model) or DEFAULT_OPENAI_MODEL
    if request.ollama_model is not None:
        _chat_settings["ollama_model"] = _compact_text(request.ollama_model) or DEFAULT_OLLAMA_MODEL
    if request.system_prompt is not None:
        _chat_settings["system_prompt"] = request.system_prompt.strip() or SYSTEM_PROMPT
    if request.tone is not None:
        _chat_settings["tone"] = _compact_text(request.tone) or "friendly"
    if request.response_style is not None:
        _chat_settings["response_style"] = _compact_text(request.response_style) or "balanced"
    if request.tool_mode is not None:
        _chat_settings["tool_mode"] = bool(request.tool_mode)
    _apply_runtime_chat_settings()
    _save_chat_state()
    return {"ok": True, "settings": {**_chat_settings, "active_model": _active_chat_model(), "llm_status": get_llm_status()}}


@app.get("/chat/sessions")
def get_sessions(request: Request):
    _enforce_app_auth(request)
    return {"ok": True, "sessions": _ordered_sessions()}


@app.post("/chat/sessions")
def create_session(request: SessionRequest, http_request: Request):
    _enforce_app_auth(http_request)
    session = _ensure_session(title=_compact_text(request.title) or "New chat", create_new=True)
    _save_chat_state()
    return {"ok": True, "session": session, "sessions": _ordered_sessions()}


@app.post("/chat/sessions/rename")
def rename_session(request: SessionUpdateRequest, http_request: Request):
    _enforce_app_auth(http_request)
    session = _chat_sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    session["title"] = _compact_text(request.title) or session["title"]
    session["updated_at"] = _utc_now()
    _save_chat_state()
    return {"ok": True, "session": session, "sessions": _ordered_sessions()}


@app.post("/chat/sessions/delete")
def delete_session(request: RegenerateRequest, http_request: Request):
    _enforce_app_auth(http_request)
    deleted = _delete_session(request.session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    current = _ordered_sessions()[0]
    return {"ok": True, "sessions": _ordered_sessions(), "current_session_id": current["id"]}


@app.get("/chat/history")
def chat_history(request: Request, session_id: str | None = None):
    _enforce_app_auth(request)
    session = _resolve_session(session_id=session_id)
    return {"ok": True, "session": session, "messages": session["messages"], "sessions": _ordered_sessions()}


@app.post("/chat/upload")
async def chat_upload(
    request: Request,
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
):
    _enforce_app_auth(request)
    session = _resolve_session(session_id=session_id)
    filename = _compact_text(file.filename) or "document"
    try:
        data = await file.read()
        document = _extract_document_payload(filename, data)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not read file: {error}") from error

    documents = _normalize_documents(session.get("documents"))
    documents = [item for item in documents if item.get("name") != document["name"]]
    documents.append(document)
    session["documents"] = documents
    session["updated_at"] = _utc_now()
    _save_chat_state()
    return {
        "ok": True,
        "document": {key: value for key, value in document.items() if key != "chunks"},
        "documents": [{key: value for key, value in item.items() if key != "chunks"} for item in documents],
        "session": session,
        "sessions": _ordered_sessions(),
    }


@app.post("/chat/upload/remove")
def chat_remove_upload(payload: RemoveDocumentRequest, request: Request):
    _enforce_app_auth(request)
    session = _resolve_session(session_id=payload.session_id)
    filename = _compact_text(payload.filename)
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required.")
        
    documents = _normalize_documents(session.get("documents"))
    original_count = len(documents)
    documents = [item for item in documents if item.get("name") != filename]
    
    if len(documents) == original_count:
        raise HTTPException(status_code=404, detail="Document not found in session.")
        
    session["documents"] = documents
    session["updated_at"] = _utc_now()
    _save_chat_state()
    return {
        "ok": True,
        "documents": [{key: value for key, value in item.items() if key != "chunks"} for item in documents],
        "session": session,
    }


@app.get("/chat/export")
def export_chat(request: Request, session_id: str):
    _enforce_app_auth(request)
    session = _chat_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    lines = [f"# {session['title']}", ""]
    for item in session["messages"]:
        role = "You" if item["role"] == "user" else "Grandpa"
        timestamp = item.get("created_at", "")
        lines.append(f"[{timestamp}] {role}: {item.get('content', '')}")
    return {
        "ok": True,
        "session": {
            "id": session["id"],
            "title": session["title"],
        },
        "content": "\n".join(lines).strip(),
        "filename": f"{session['title'].replace(' ', '_').lower() or 'chat'}.md",
    }


@app.post("/chat/reset")
def chat_reset(request: Request, session_id: str | None = None):
    _enforce_app_auth(request)
    session = _resolve_session(session_id=session_id)
    session["messages"] = []
    session["updated_at"] = _utc_now()
    _save_chat_state()
    return {"ok": True}


@app.post("/chat/cancel")
def chat_cancel(payload: CancelRequest, request: Request):
    _enforce_app_auth(request)
    _cancelled_streams.add(payload.session_id)
    return {"ok": True}


@app.post("/chat")
def chat_reply(request: ChatRequest, http_request: Request = None):
    message = _compact_text(request.message)
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")
    _enforce_app_auth(http_request)
    auth_context = _authenticated_app_context(http_request, required=False)
    user_id = _authenticated_user_id(http_request)
    prompt_guard = validate_prompt_text(message, source="web-api-chat")
    if not prompt_guard.get("allowed", True):
        log_audit_event(
            "chat",
            "blocked_prompt",
            user_id=user_id,
            payload={"message": message[:280]},
        )
        return {
            "ok": False,
            "reply": prompt_guard.get("message", "Unsafe prompt blocked."),
            "interaction_id": None,
            "mood": mood_status_payload(),
            "message": _history_item("assistant", prompt_guard.get("message", "Unsafe prompt blocked.")),
        }

    session = _resolve_session(session_id=request.session_id)
    mood_snapshot = record_mood_from_analysis(message, analyze_emotion(message), source="web-api-chat")
    runtime_observation = ASSISTANT_RUNTIME.observe_user_message(
        message,
        source="web-api-chat",
        emotion={"emotion": mood_snapshot.get("last_mood", "neutral")},
        mood=mood_snapshot,
    )
    context = runtime_observation.get("context", "casual")
    observe_user_turn(
        message,
        context=context,
        emotion=mood_snapshot.get("last_mood", "neutral"),
        mood=mood_snapshot.get("last_mood", "neutral"),
        source="web-api-chat",
    )
    _update_session_title(session, message)
    user_item = _history_item("user", message)
    session["messages"].append(user_item)
    session["messages"] = _trim_messages(session["messages"])
    session["updated_at"] = _utc_now()
    _save_chat_state()
    append_chat_message(
        session["id"],
        "user",
        message,
        user_id=user_id,
        source="web-chat",
        emotion=mood_snapshot.get("last_mood", "neutral"),
        metadata={"context": context},
    )
    MOBILE_COMPANION.record_chat_message("user", message, session_id=session["id"], source="desktop-chat")
    prompt_message = _build_chat_input(session, message, mood_snapshot=mood_snapshot, context=context)

    try:
        if _looks_like_direct_action_input(message):
            direct_reply, tool_command, tool_messages, confirmation_id = _execute_tool_command_for_chat(
                _compact_text(message),
                source="chat-direct",
            )
            assistant_item = _history_item(
                "assistant",
                direct_reply.strip() or "I could not generate a reply right now.",
            )
            if tool_command:
                assistant_item["tool"] = {"command": tool_command, "messages": tool_messages}
            if confirmation_id:
                assistant_item["confirmation_id"] = confirmation_id
            session["messages"].append(assistant_item)
            session["messages"] = _trim_messages(session["messages"])
            session["updated_at"] = _utc_now()
            _save_chat_state()
            append_chat_message(
                session["id"],
                "assistant",
                assistant_item["content"],
                user_id=user_id,
                source="web-chat",
                emotion=mood_snapshot.get("last_mood", "neutral"),
                metadata={"route": "tool-direct"},
            )
            MOBILE_COMPANION.record_chat_message(
                "assistant",
                assistant_item["content"],
                session_id=session["id"],
                source="desktop-chat",
            )
            ASSISTANT_RUNTIME.observe_assistant_reply(assistant_item["content"], source="web-api-chat")
            interaction = record_assistant_turn(
                message,
                assistant_item["content"],
                context=context,
                emotion=mood_snapshot.get("last_mood", "neutral"),
                mood=mood_snapshot.get("last_mood", "neutral"),
                source="web-api-chat",
                route="tool-direct",
                model="command-router",
            )
            log_audit_event(
                "chat",
                "assistant_reply",
                user_id=user_id,
                payload={"session_id": session["id"], "route": "tool-direct", "interaction_id": interaction.get("id")},
            )
            return {
                "ok": True,
                "reply": assistant_item["content"],
                "interaction_id": interaction.get("id"),
                "mood": mood_snapshot,
                "message": assistant_item,
                "messages": session["messages"],
                "session": session,
            }

        reply, tool_command, tool_messages, confirmation_id = _run_tool_aware_reply(
            session["messages"][:-1],
            prompt_message,
            raw_user_message=message,
            mood_snapshot=mood_snapshot,
            context=context,
        )
        assistant_item = _history_item("assistant", reply)
        if tool_command:
            assistant_item["tool"] = {"command": tool_command, "messages": tool_messages}
        if confirmation_id:
            assistant_item["confirmation_id"] = confirmation_id
        session["messages"].append(assistant_item)
        session["messages"] = _trim_messages(session["messages"])
        session["updated_at"] = _utc_now()
        _save_chat_state()
        append_chat_message(
            session["id"],
            "assistant",
            reply,
            user_id=user_id,
            source="web-chat",
            emotion=mood_snapshot.get("last_mood", "neutral"),
            metadata={"route": "chat", "model": _active_chat_model()},
        )
        MOBILE_COMPANION.record_chat_message("assistant", reply, session_id=session["id"], source="desktop-chat")
        ASSISTANT_RUNTIME.observe_assistant_reply(reply, source="web-api-chat")
        interaction = record_assistant_turn(
            message,
            reply,
            context=context,
            emotion=mood_snapshot.get("last_mood", "neutral"),
            mood=mood_snapshot.get("last_mood", "neutral"),
            source="web-api-chat",
            route="chat",
            model=_active_chat_model(),
        )
        log_audit_event(
            "chat",
            "assistant_reply",
            user_id=user_id,
            payload={"session_id": session["id"], "route": "chat", "interaction_id": interaction.get("id")},
        )
        return {"ok": True, "reply": reply, "interaction_id": interaction.get("id"), "mood": mood_snapshot, "message": assistant_item, "messages": session["messages"], "session": session}
    except Exception as error:
        record_system_error("web-api-chat", str(error), metadata={"context": context})
        raise HTTPException(status_code=500, detail=_friendly_ai_error(error)) from error


@app.post("/chat/regenerate")
def regenerate_reply(request: RegenerateRequest, http_request: Request):
    _enforce_app_auth(http_request)
    session = _chat_sessions.get(request.session_id)
    if not session or not session["messages"]:
        raise HTTPException(status_code=404, detail="Session not found.")

    messages = session["messages"]
    while messages and messages[-1]["role"] == "assistant":
        messages.pop()
    if not messages or messages[-1]["role"] != "user":
        raise HTTPException(status_code=400, detail="No user message available to regenerate.")

    last_user_message = messages[-1]["content"]
    current_mood_snapshot = mood_status_payload()
    prompt_message = _build_chat_input(session, last_user_message, mood_snapshot=current_mood_snapshot)
    try:
        if _looks_like_direct_action_input(last_user_message):
            direct_reply, tool_command, tool_messages, confirmation_id = _execute_tool_command_for_chat(
                _compact_text(last_user_message),
                source="chat-direct-regenerate",
            )
            assistant_item = _history_item(
                "assistant",
                direct_reply.strip() or "I could not generate a reply right now.",
            )
            if tool_command:
                assistant_item["tool"] = {"command": tool_command, "messages": tool_messages}
            if confirmation_id:
                assistant_item["confirmation_id"] = confirmation_id
            messages.append(assistant_item)
            session["messages"] = _trim_messages(messages)
            session["updated_at"] = _utc_now()
            _save_chat_state()
            return {"ok": True, "message": assistant_item, "session": session}

        reply, tool_command, tool_messages, confirmation_id = _run_tool_aware_reply(
            messages[:-1],
            prompt_message,
            raw_user_message=last_user_message,
            mood_snapshot=current_mood_snapshot,
        )
        assistant_item = _history_item("assistant", reply)
        if tool_command:
            assistant_item["tool"] = {"command": tool_command, "messages": tool_messages}
        if confirmation_id:
            assistant_item["confirmation_id"] = confirmation_id
        messages.append(assistant_item)
        session["messages"] = _trim_messages(messages)
        session["updated_at"] = _utc_now()
        _save_chat_state()
        return {"ok": True, "mood": current_mood_snapshot, "message": assistant_item, "session": session}
    except Exception as error:
        raise HTTPException(status_code=500, detail=_friendly_ai_error(error)) from error


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, http_request: Request = None):
    message = _compact_text(request.message)
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")
    _enforce_app_auth(http_request)
    user_id = _authenticated_user_id(http_request)
    prompt_guard = validate_prompt_text(message, source="web-api-stream")
    if not prompt_guard.get("allowed", True):
        async def blocked_stream():
            yield f"data: {json.dumps({'type': 'delta', 'content': prompt_guard.get('message', 'Unsafe prompt blocked.')})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': prompt_guard.get('message', 'Unsafe prompt blocked.'), 'interaction_id': None})}\n\n"

        return StreamingResponse(blocked_stream(), media_type="text/event-stream")

    session = _resolve_session(session_id=request.session_id)
    mood_snapshot = record_mood_from_analysis(message, analyze_emotion(message), source="web-api-stream")
    runtime_observation = ASSISTANT_RUNTIME.observe_user_message(
        message,
        source="web-api-stream",
        emotion={"emotion": mood_snapshot.get("last_mood", "neutral")},
        mood=mood_snapshot,
    )
    context = runtime_observation.get("context", "casual")
    observe_user_turn(
        message,
        context=context,
        emotion=mood_snapshot.get("last_mood", "neutral"),
        mood=mood_snapshot.get("last_mood", "neutral"),
        source="web-api-stream",
    )
    _update_session_title(session, message)
    session_id = session["id"]
    if session_id in _cancelled_streams:
        _cancelled_streams.discard(session_id)

    user_item = _history_item("user", message)
    session["messages"].append(user_item)
    session["messages"] = _trim_messages(session["messages"])
    session["updated_at"] = _utc_now()
    _save_chat_state()
    append_chat_message(
        session_id,
        "user",
        message,
        user_id=user_id,
        source="web-stream",
        emotion=mood_snapshot.get("last_mood", "neutral"),
        metadata={"context": context},
    )
    MOBILE_COMPANION.record_chat_message("user", message, session_id=session_id, source="desktop-stream")
    history_snapshot = list(session["messages"][:-1])
    prompt_message = _build_chat_input(session, message, mood_snapshot=mood_snapshot, context=context)

    async def event_stream():
        full_reply = ""
        confirmation_id = None
        try:
            yield (
                "data: "
                + json.dumps(
                    {
                        "type": "mood",
                        "mood": mood_snapshot,
                        "session": {"id": session["id"], "title": session["title"]},
                    }
                )
                + "\n\n"
            )
            if _looks_like_direct_action_input(message):
                direct_reply, tool_command, tool_messages, confirmation_id = _execute_tool_command_for_chat(
                    _compact_text(message),
                    source="chat-direct-stream",
                )
                assistant_item = _history_item(
                    "assistant",
                    direct_reply.strip() or "I could not generate a reply right now.",
                )
                if tool_command:
                    assistant_item["tool"] = {"command": tool_command, "messages": tool_messages}
                if confirmation_id:
                    assistant_item["confirmation_id"] = confirmation_id
                session["messages"].append(assistant_item)
                session["messages"] = _trim_messages(session["messages"])
                session["updated_at"] = _utc_now()
                _save_chat_state()
                append_chat_message(
                    session["id"],
                    "assistant",
                    assistant_item["content"],
                    user_id=user_id,
                    source="web-stream",
                    emotion=mood_snapshot.get("last_mood", "neutral"),
                    metadata={"route": "tool-direct"},
                )
                MOBILE_COMPANION.record_chat_message(
                    "assistant",
                    assistant_item["content"],
                    session_id=session["id"],
                    source="desktop-stream",
                )
                ASSISTANT_RUNTIME.observe_assistant_reply(assistant_item["content"], source="web-api-stream")
                interaction = record_assistant_turn(
                    message,
                    assistant_item["content"],
                    context=context,
                    emotion=mood_snapshot.get("last_mood", "neutral"),
                    mood=mood_snapshot.get("last_mood", "neutral"),
                    source="web-api-stream",
                    route="tool-direct",
                    model="command-router",
                )
                log_audit_event(
                    "chat",
                    "assistant_stream_reply",
                    user_id=user_id,
                    payload={"session_id": session["id"], "route": "tool-direct", "interaction_id": interaction.get("id")},
                )
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "done",
                            "message": assistant_item,
                            "interaction_id": interaction.get("id"),
                            "session": {"id": session["id"], "title": session["title"]},
                        }
                    )
                    + "\n\n"
                )
                return

            for chunk in stream_chat_reply(
                history_snapshot,
                prompt_message,
                model=_active_chat_model(),
                system_prompt=_effective_system_prompt(message, mood_snapshot=mood_snapshot, context=context),
            ):
                if session_id in _cancelled_streams:
                    _cancelled_streams.discard(session_id)
                    yield f"data: {json.dumps({'type': 'cancelled'})}\n\n"
                    return
                full_reply += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk, 'session_id': session_id})}\n\n"

            tool_command = None
            tool_messages = []
            stripped = full_reply.strip()
            if _chat_settings.get("tool_mode") and stripped.startswith("TOOL:"):
                tool_command = _compact_text(stripped.replace("TOOL:", "", 1))
                if _is_risky_command(tool_command):
                    confirmation_id = _create_confirmation(tool_command, source="chat-tool")
                    full_reply = f"I can do that, but I need confirmation first: {tool_command}"
                else:
                    tool_messages = _capture_command_reply(tool_command)
                    bridge_message = (
                        f"User request: {message}\nTool command used: {tool_command}\nTool result: {' '.join(tool_messages)}\n"
                        "Now answer the user naturally using that result."
                    )
                    full_reply = generate_chat_reply(
                        history_snapshot,
                        bridge_message,
                        model=_active_chat_model(),
                        system_prompt=_effective_system_prompt(message, mood_snapshot=mood_snapshot, context=context),
                    )

            assistant_item = _history_item("assistant", full_reply.strip() or "I could not generate a reply right now.")
            if tool_command:
                assistant_item["tool"] = {"command": tool_command, "messages": tool_messages}
            if confirmation_id:
                assistant_item["confirmation_id"] = confirmation_id
            session["messages"].append(assistant_item)
            session["messages"] = _trim_messages(session["messages"])
            session["updated_at"] = _utc_now()
            _save_chat_state()
            append_chat_message(
                session["id"],
                "assistant",
                assistant_item["content"],
                user_id=user_id,
                source="web-stream",
                emotion=mood_snapshot.get("last_mood", "neutral"),
                metadata={"route": "chat-stream", "model": _active_chat_model()},
            )
            MOBILE_COMPANION.record_chat_message(
                "assistant",
                assistant_item["content"],
                session_id=session["id"],
                source="desktop-stream",
            )
            ASSISTANT_RUNTIME.observe_assistant_reply(assistant_item["content"], source="web-api-stream")
            interaction = record_assistant_turn(
                message,
                assistant_item["content"],
                context=context,
                emotion=mood_snapshot.get("last_mood", "neutral"),
                mood=mood_snapshot.get("last_mood", "neutral"),
                source="web-api-stream",
                route="chat-stream",
                model=_active_chat_model(),
            )
            log_audit_event(
                "chat",
                "assistant_stream_reply",
                user_id=user_id,
                payload={"session_id": session["id"], "route": "chat-stream", "interaction_id": interaction.get("id")},
            )
            yield f"data: {json.dumps({'type': 'done', 'message': assistant_item, 'interaction_id': interaction.get('id'), 'session': {'id': session['id'], 'title': session['title']}})}\n\n"
        except Exception as error:
            record_system_error("web-api-stream", str(error), metadata={"context": context})
            yield f"data: {json.dumps({'type': 'error', 'error': _friendly_ai_error(error)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _initialize_web_runtime() -> None:
    _load_chat_state()
    _ensure_session()
    ASSISTANT_RUNTIME.start()
    DEVICE_MANAGER.start()


def _shutdown_web_runtime() -> None:
    DEVICE_MANAGER.stop()


@app.on_event("startup")
def _on_web_api_startup() -> None:
    _initialize_web_runtime()


@app.on_event("shutdown")
def _on_web_api_shutdown() -> None:
    _shutdown_web_runtime()


def start_web_api(installed_apps, host="127.0.0.1", port=8765):
    global _server, _server_thread, _installed_apps
    _installed_apps = installed_apps or {}
    _initialize_web_runtime()
    if _server_thread and _server_thread.is_alive():
        return

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    _server = uvicorn.Server(config)
    _server_thread = threading.Thread(target=_server.run, daemon=True)
    _server_thread.start()
