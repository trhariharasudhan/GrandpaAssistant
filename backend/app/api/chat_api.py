from datetime import datetime
import json
import os
import time
from typing import Any
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from api_logging import ensure_log_dir, log_api_event, new_request_id, request_summary
from agents.runtime import ASSISTANT_RUNTIME
from cognition.context_engine import contextual_recall_payload
from cognition.graph_engine import build_knowledge_graph
from cognition.hub import (
    build_intelligence_prompt_boost,
    intelligence_status_payload,
    observe_user_turn,
    quick_decision_payload,
    record_assistant_turn,
    submit_response_feedback,
)
from cognition.insight_engine import generate_user_insights
from cognition.recovery_engine import record_system_error, recovery_status_payload
from cognition.sync_engine import configure_sync, export_sync_payload, import_sync_payload, sync_status_payload
from cognition.workflow_engine import create_workflow, run_workflow, workflow_status_payload
from cognition.learning_engine import learning_status_payload
from device_manager import DEVICE_MANAGER
from brain.semantic_memory import (
    build_semantic_memory_context,
    search_semantic_memory,
    semantic_memory_status,
)
from iot_control import execute_iot_control, get_iot_action_history, resolve_iot_control_command
from iot_registry import validate_iot_config
from llm_client import generate_chat_reply, stream_chat_reply
from offline_multi_model import (
    OfflineAssistantError,
    generate_offline_reply,
    get_ollama_status,
    list_installed_models,
    select_route,
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
)
from productivity_store import get_user_preferences, update_user_preferences
from startup_diagnostics import collect_startup_diagnostics
from utils.config import get_last_settings_validation, get_setting, load_settings
from utils.emotion import analyze_emotion, build_emotion_prompt_context
from utils.mood_memory import build_mood_memory_context, mood_status_payload, record_mood_from_analysis, reset_mood_memory
from voice.speak import (
    autoconfigure_custom_voice_sample,
    autoconfigure_piper_model,
    custom_voice_setup_payload,
    piper_setup_payload,
)
from plugin_system import plugin_status_payload, reload_plugins, set_plugin_enabled
from security.auth_manager import (
    auth_status_payload,
    disable_admin_mode,
    disable_lockdown,
    enable_admin_mode,
    enable_lockdown,
    set_security_pin,
    verify_face_identity,
    verify_security_pin,
    verify_user_voice,
)
from security.device_monitor import device_security_status_payload, trust_device
from security.hub import security_logs_payload, security_status_payload, validate_prompt_text
from security.state import append_security_activity


app = FastAPI(title="Grandpa Assistant Chat API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


CHAT_HISTORY: list[dict] = []
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
IOT_MOCK_STATE_PATH = os.path.join(PROJECT_ROOT, "backend", "data", "iot_mock_state.json")


class ChatRequest(BaseModel):
    message: str


class AskRequest(BaseModel):
    prompt: str
    mode: str | None = "auto"


class SemanticMemorySearchRequest(BaseModel):
    query: str
    limit: int | None = 5


class IoTKnowledgeRequest(BaseModel):
    query: str


class IoTControlRequest(BaseModel):
    command: str
    confirm: bool | None = False


class GoalPlanRequest(BaseModel):
    goal: str
    steps: list[str] | None = None


class ThinkingModeRequest(BaseModel):
    mode: str = "adaptive"


class AutonomousModeRequest(BaseModel):
    enabled: bool


class PluginToggleRequest(BaseModel):
    name: str
    enabled: bool


class FeedbackRequest(BaseModel):
    interaction_id: str
    reaction: str
    note: str | None = ""


class DecisionRequest(BaseModel):
    question: str
    options: list[str] | None = None


class WorkflowCreateRequest(BaseModel):
    name: str
    commands: list[str]
    description: str | None = ""


class WorkflowRunRequest(BaseModel):
    name: str
    execute: bool | None = True


class SyncConfigRequest(BaseModel):
    enabled: bool | None = None
    api_base_url: str | None = None


class SyncImportRequest(BaseModel):
    payload: dict[str, Any]


class SecurityPinRequest(BaseModel):
    pin: str
    admin: bool | None = False


class DeviceTrustRequest(BaseModel):
    device: str


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


class BaseEnvelope(BaseModel):
    ok: bool


class DoctorResponse(BaseEnvelope):
    doctor: dict[str, Any]


class HealthResponse(BaseEnvelope):
    service: str
    offline_assistant: dict[str, Any]
    hardware: dict[str, Any]
    iot: dict[str, Any]
    security: dict[str, Any]
    runtime: dict[str, Any]
    semantic_memory: dict[str, Any]
    doctor: dict[str, Any]


class DevicesResponse(BaseEnvelope):
    devices: list[dict[str, Any]]
    recent_events: list[dict[str, Any]]


class DeviceRescanResponse(DevicesResponse):
    status: dict[str, Any]


class StatusResponse(BaseEnvelope):
    assistant: dict[str, Any]


class SettingsValidationResponse(BaseEnvelope):
    validation: dict[str, Any]


class PiperSetupResponse(BaseEnvelope):
    piper: dict[str, Any]
    message: str | None = None


class CustomVoiceSetupResponse(BaseEnvelope):
    custom_voice: dict[str, Any]
    message: str | None = None


class IoTValidationResponse(BaseEnvelope):
    validation: dict[str, Any]


class SecurityStatusResponse(BaseEnvelope):
    security: dict[str, Any]


class AskResponse(BaseEnvelope):
    prompt: str
    mode: str
    route: str
    model: str
    response: str
    hardware_context_used: bool
    interaction_id: str | None = None
    emotion: dict[str, Any] | None = None
    mood: dict[str, Any] | None = None
    hardware: dict[str, Any] | None = None
    iot: dict[str, Any] | None = None
    iot_control: dict[str, Any] | None = None


def _hardware_aware_prompt(message: str) -> tuple[str, str | None]:
    hardware_context = DEVICE_MANAGER.build_prompt_context(message)
    if not hardware_context:
        return message, None
    return (
        f"{hardware_context}\n\n"
        f"User question: {message}\n"
        "Answer clearly. Use the hardware context only when it is relevant to the request.",
        hardware_context,
    )


def _utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _extract_bearer_token(authorization_value: str) -> str:
    value = str(authorization_value or "").strip()
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


def _authenticated_user_id(request: Request | None) -> int | None:
    payload = _authenticated_app_context(request, required=False)
    user = (payload or {}).get("user") if payload else None
    try:
        return int(user.get("id")) if user and user.get("id") is not None else None
    except Exception:
        return None


def _normalize_profile_preferences(payload: AuthProfileUpdateRequest) -> dict[str, Any]:
    preferences = {}
    if payload.preferred_language is not None:
        preferences["preferred_language"] = str(payload.preferred_language or "").strip() or "en-US"
    if payload.response_style is not None:
        preferences["response_style"] = str(payload.response_style or "").strip() or "balanced"
    if payload.tone is not None:
        preferences["tone"] = str(payload.tone or "").strip() or "friendly"
    if payload.theme is not None:
        preferences["theme"] = str(payload.theme or "").strip() or "system"
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
    return {
        "user": user,
        "preferences": get_user_preferences(user_id) if user_id is not None else {},
    }


def _api_auth_required() -> bool:
    return bool(get_setting("auth.enabled", True) and get_setting("auth.ui_login_required", True))


def _enforce_api_auth(request: Request | None) -> dict | None:
    if request is None:
        return None
    return _authenticated_app_context(request, required=_api_auth_required())


def _history_item(role: str, content: str) -> dict:
    return {
        "id": f"{role}-{datetime.utcnow().timestamp()}",
        "role": role,
        "content": content,
        "created_at": _utc_now(),
    }


def _trim_history() -> None:
    global CHAT_HISTORY
    CHAT_HISTORY = CHAT_HISTORY[-60:]


def _chat_prompt_with_memory(message: str, mood_snapshot: dict | None = None, context: str = "casual") -> str:
    memory_context = build_semantic_memory_context(message)
    emotion_context = build_emotion_prompt_context(message)
    mood_context = build_mood_memory_context(mood_snapshot)
    intelligence_context = build_intelligence_prompt_boost(
        message,
        context=context,
        emotion=(mood_snapshot or {}).get("last_mood", "neutral"),
        mood=mood_snapshot,
    )
    if not memory_context:
        return (
            f"User question: {message}\n"
            f"{emotion_context}\n"
            f"{mood_context}\n"
            f"{intelligence_context or ''}\n"
            "Reply in natural English only. Talk like a smart, friendly real person. "
            "Keep casual chat short and natural, usually 1 or 2 sentences unless the user asks for more. "
            "Understand Tanglish input, but do not answer in Tanglish."
        )
    return (
        f"{memory_context}\n\n"
        f"User question: {message}\n"
        f"{emotion_context}\n"
        f"{mood_context}\n"
        f"{intelligence_context or ''}\n"
        "Answer naturally in English only. Talk like a smart, friendly real person. "
        "Use the saved memory only when it helps with the user's question. "
        "Keep casual chat short and natural, usually 1 or 2 sentences unless the user asks for more. "
        "Understand Tanglish input, but do not answer in Tanglish."
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = new_request_id()
    request.state.request_id = request_id
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as error:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        log_api_event(
            "request_failed",
            level="error",
            request_id=request_id,
            duration_ms=duration_ms,
            error=str(error),
            **request_summary(request),
        )
        raise

    response.headers["X-Request-Id"] = request_id
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    log_api_event(
        "request_completed",
        level="info",
        request_id=request_id,
        status_code=response.status_code,
        duration_ms=duration_ms,
        **request_summary(request),
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", new_request_id())
    detail = str(error.detail)
    if int(error.status_code) >= 500:
        record_system_error(
            "chat-api-http",
            f"{request.method} {request.url.path}: {detail}",
            metadata={"status_code": error.status_code},
        )
    log_api_event(
        "http_exception",
        level="warning",
        request_id=request_id,
        status_code=error.status_code,
        detail=detail,
        **request_summary(request),
    )
    return JSONResponse(
        status_code=error.status_code,
        content={"ok": False, "error": detail, "request_id": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", new_request_id())
    log_api_event(
        "validation_exception",
        level="warning",
        request_id=request_id,
        status_code=422,
        errors=error.errors(),
        **request_summary(request),
    )
    return JSONResponse(
        status_code=422,
        content={"ok": False, "error": "Request validation failed.", "details": error.errors(), "request_id": request_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, error: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", new_request_id())
    record_system_error(
        "chat-api-unhandled",
        f"{request.method} {request.url.path}: {error}",
        metadata={"path": str(request.url.path)},
    )
    log_api_event(
        "unhandled_exception",
        level="error",
        request_id=request_id,
        status_code=500,
        error=str(error),
        **request_summary(request),
    )
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": "Internal assistant error.", "request_id": request_id},
    )


@app.get("/health", response_model=HealthResponse)
def health() -> dict:
    _ensure_runtime_ready()
    return {
        "ok": True,
        "service": "grandpa-assistant-fastapi",
        "offline_assistant": get_ollama_status(),
        "hardware": DEVICE_MANAGER.get_status(),
        "iot": DEVICE_MANAGER.get_iot_status(),
        "security": security_status_payload(DEVICE_MANAGER),
        "runtime": ASSISTANT_RUNTIME.status_payload(),
        "semantic_memory": semantic_memory_status(prewarm=False),
        "doctor": collect_startup_diagnostics(),
    }


def _load_local_json(path: str) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _save_local_json(path: str, payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)


def _ensure_runtime_ready() -> None:
    runtime_payload = ASSISTANT_RUNTIME.status_payload()
    if not runtime_payload.get("running"):
        ASSISTANT_RUNTIME.start()
    elif not ASSISTANT_RUNTIME.agent_statuses():
        ASSISTANT_RUNTIME.refresh_all()


@app.get("/doctor", response_model=DoctorResponse)
def doctor() -> dict:
    return {
        "ok": True,
        "doctor": collect_startup_diagnostics(use_cache=False),
    }


@app.get("/auth/bootstrap-status")
def auth_bootstrap() -> dict:
    return {"ok": True, "auth": auth_bootstrap_status()}


@app.get("/auth/status")
def auth_status(request: Request) -> dict:
    return {
        "ok": True,
        "auth": app_auth_status_payload(),
        "current": _authenticated_app_context(request, required=False),
    }


@app.post("/auth/register")
def auth_register(http_request: Request, request: AuthRegisterRequest) -> dict:
    try:
        created = register_app_user(
            request.username,
            request.password,
            display_name=(request.display_name or request.username),
            role=request.role or "user",
        )
        session = login_app_user(
            request.username,
            request.password,
            user_agent=http_request.headers.get("user-agent", ""),
            device_name=request.device_name or "chat-api",
        )
        return {"ok": True, **created, **session}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/auth/login")
def auth_login(http_request: Request, request: AuthLoginRequest) -> dict:
    try:
        session = login_app_user(
            request.username,
            request.password,
            user_agent=http_request.headers.get("user-agent", ""),
            device_name=request.device_name or "chat-api",
        )
        return {"ok": True, **session, "bootstrap": auth_bootstrap_status()}
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@app.post("/auth/logout")
def auth_logout(request: Request) -> dict:
    token = _extract_bearer_token(request.headers.get("authorization", ""))
    if not token:
        raise HTTPException(status_code=400, detail="Authorization token is required.")
    logout_app_token(token)
    return {"ok": True}


@app.get("/auth/me")
def auth_me(request: Request) -> dict:
    return {"ok": True, **_authenticated_app_context(request, required=True)}


@app.get("/auth/profile")
def auth_profile(request: Request) -> dict:
    context = _authenticated_app_context(request, required=True)
    return {"ok": True, **_account_profile_payload(context)}


@app.post("/auth/profile")
def auth_update_profile(request: Request, payload: AuthProfileUpdateRequest) -> dict:
    context = _authenticated_app_context(request, required=True)
    user = (context or {}).get("user") if context else None
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required.")

    user_id = int(user["id"])
    resolved_display_name = str(payload.display_name or "").strip() or user.get("display_name") or user.get("username")
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


@app.get("/auth/users")
def auth_users(request: Request) -> dict:
    context = _authenticated_app_context(request, required=True)
    try:
        require_admin(context)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return {"ok": True, "users": app_auth_status_payload().get("users", [])}


@app.get("/auth/audit")
def auth_audit(request: Request, limit: int = 80) -> dict:
    context = _authenticated_app_context(request, required=True)
    try:
        user = require_admin(context)
        return {"ok": True, "items": get_app_audit_log(limit=limit), "user": user}
    except PermissionError:
        user = (context or {}).get("user") if context else None
        user_id = int(user.get("id")) if user and user.get("id") is not None else None
        return {"ok": True, "items": get_app_audit_log(user_id=user_id, limit=limit), "user": user}


@app.get("/auth/chat-archive")
def auth_chat_archive(request: Request, limit: int = 120) -> dict:
    context = _authenticated_app_context(request, required=True)
    user = (context or {}).get("user") if context else None
    user_id = int(user.get("id")) if user and user.get("id") is not None else None
    return {"ok": True, "items": list_chat_archive(session_id="chat-api-default", user_id=user_id, limit=limit)}


@app.on_event("startup")
def startup_device_monitor() -> None:
    ensure_log_dir()
    load_settings()
    DEVICE_MANAGER.start()
    ASSISTANT_RUNTIME.start()


@app.on_event("shutdown")
def shutdown_device_monitor() -> None:
    DEVICE_MANAGER.stop()
    ASSISTANT_RUNTIME.stop()


@app.get("/models")
def get_models() -> dict:
    try:
        return {
            "ok": True,
            "models": list_installed_models(),
        }
    except OfflineAssistantError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/devices", response_model=DevicesResponse)
def get_devices() -> dict:
    return {
        "ok": True,
        "devices": DEVICE_MANAGER.get_devices(),
        "recent_events": DEVICE_MANAGER.get_recent_events(limit=10),
    }


@app.post("/devices/rescan", response_model=DeviceRescanResponse)
def rescan_devices() -> dict:
    status = DEVICE_MANAGER.refresh(emit_events=True)
    return {
        "ok": True,
        "status": status,
        "devices": status.get("devices", []),
        "recent_events": status.get("recent_events", []),
    }


@app.get("/settings/validation", response_model=SettingsValidationResponse)
def get_settings_validation() -> dict:
    load_settings()
    return {
        "ok": True,
        "validation": get_last_settings_validation(),
    }


@app.get("/voice/piper/status", response_model=PiperSetupResponse)
def get_piper_status() -> dict:
    return {
        "ok": True,
        "piper": piper_setup_payload(),
        "message": None,
    }


@app.post("/voice/piper/autoconfigure", response_model=PiperSetupResponse)
def autoconfigure_piper() -> dict:
    ok, message = autoconfigure_piper_model()
    return {
        "ok": bool(ok),
        "piper": piper_setup_payload(),
        "message": message,
    }


@app.get("/voice/custom/status", response_model=CustomVoiceSetupResponse)
def get_custom_voice_status() -> dict:
    return {
        "ok": True,
        "custom_voice": custom_voice_setup_payload(),
        "message": None,
    }


@app.post("/voice/custom/autoconfigure", response_model=CustomVoiceSetupResponse)
def autoconfigure_custom_voice() -> dict:
    ok, message = autoconfigure_custom_voice_sample()
    return {
        "ok": bool(ok),
        "custom_voice": custom_voice_setup_payload(),
        "message": message,
    }


@app.get("/iot/devices")
def get_iot_devices() -> dict:
    iot_status = DEVICE_MANAGER.get_iot_status()
    return {
        "ok": True,
        "summary": iot_status["summary"],
        "devices": iot_status["discovered_devices"],
        "configured": iot_status["configured"],
    }


@app.get("/iot/status")
def get_iot_status() -> dict:
    return {
        "ok": True,
        "iot": DEVICE_MANAGER.get_iot_status(),
    }


@app.get("/iot/validate", response_model=IoTValidationResponse)
def get_iot_validation() -> dict:
    return {
        "ok": True,
        "validation": validate_iot_config(test_connectivity=True),
    }


@app.get("/iot/history")
def get_iot_history() -> dict:
    return {
        "ok": True,
        "history": get_iot_action_history(limit=20),
    }


@app.post("/iot/knowledge")
def iot_knowledge(request: IoTKnowledgeRequest) -> dict:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required.")

    response = DEVICE_MANAGER.local_response(query)
    if not response:
        effective_prompt, _ = _hardware_aware_prompt(query)
        try:
            result = generate_offline_reply(effective_prompt, mode="general")
            response = result["response"]
            model = result["model"]
            route = result["route"]
        except OfflineAssistantError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
    else:
        model = "iot-registry"
        route = "hardware-local"

    return {
        "ok": True,
        "query": query,
        "response": response,
        "model": model,
        "route": route,
        "iot": DEVICE_MANAGER.get_iot_status(),
    }


@app.post("/iot/control")
def iot_control(request: IoTControlRequest) -> dict:
    command = request.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="Command is required.")

    result = execute_iot_control(command, confirm=bool(request.confirm))
    return {
        "ok": bool(result.get("ok")),
        "executed": bool(result.get("executed")),
        "requires_confirmation": bool(result.get("requires_confirmation")) and not bool(request.confirm),
        "message": result.get("message", ""),
        "control": result,
        "iot": DEVICE_MANAGER.get_iot_status(),
        "history": get_iot_action_history(limit=12),
    }


@app.post("/iot/mock/{device_name}/{action}")
def iot_mock_action(device_name: str, action: str) -> dict:
    state = _load_local_json(IOT_MOCK_STATE_PATH)
    devices = state.get("devices") if isinstance(state.get("devices"), dict) else {}
    device_key = device_name.strip().lower()
    action_key = action.strip().lower()
    devices[device_key] = {
        "state": action_key,
        "updated_at": _utc_now(),
    }
    state["devices"] = devices
    state["updated_at"] = _utc_now()
    _save_local_json(IOT_MOCK_STATE_PATH, state)
    return {
        "ok": True,
        "device": device_key,
        "action": action_key,
        "state": devices[device_key],
        "message": f"{device_key} set to {action_key}.",
    }


@app.get("/iot/mock/status")
def iot_mock_status() -> dict:
    state = _load_local_json(IOT_MOCK_STATE_PATH)
    devices = state.get("devices") if isinstance(state.get("devices"), dict) else {}
    return {
        "ok": True,
        "updated_at": state.get("updated_at", ""),
        "devices": devices,
    }


@app.get("/status", response_model=StatusResponse)
def get_status(request: Request) -> dict:
    _ensure_runtime_ready()
    return {
        "ok": True,
        "assistant": {
            "service": "grandpa-assistant-fastapi",
            "offline_assistant": get_ollama_status(),
            "hardware": DEVICE_MANAGER.get_status(),
            "iot": DEVICE_MANAGER.get_iot_status(),
            "security": security_status_payload(DEVICE_MANAGER),
            "mood": mood_status_payload(),
            "runtime": ASSISTANT_RUNTIME.status_payload(),
            "intelligence": intelligence_status_payload(ASSISTANT_RUNTIME.status_payload()),
            "semantic_memory": semantic_memory_status(prewarm=False),
            "auth": {
                "bootstrap": auth_bootstrap_status(),
                "current": _authenticated_app_context(request, required=False),
            },
        },
    }


@app.get("/security/status", response_model=SecurityStatusResponse)
def get_security_status() -> dict:
    return {
        "ok": True,
        "security": security_status_payload(DEVICE_MANAGER),
    }


@app.get("/security/logs")
def get_security_logs(limit: int = 50) -> dict:
    return {
        "ok": True,
        "logs": security_logs_payload(limit=limit),
    }


@app.post("/security/pin")
def configure_security_pin(request: SecurityPinRequest) -> dict:
    ok, message = set_security_pin(request.pin)
    return {
        "ok": bool(ok),
        "message": message,
        "auth": auth_status_payload(),
    }


@app.post("/security/auth/pin")
def authenticate_with_pin(request: SecurityPinRequest) -> dict:
    ok, message = verify_security_pin(request.pin, admin=bool(request.admin))
    return {
        "ok": bool(ok),
        "message": message,
        "auth": auth_status_payload(),
    }


@app.post("/security/auth/face")
def authenticate_with_face() -> dict:
    ok, message = verify_face_identity()
    return {
        "ok": bool(ok),
        "message": message,
        "auth": auth_status_payload(),
    }


@app.post("/security/auth/voice")
def authenticate_with_voice() -> dict:
    ok, message, score = verify_user_voice()
    return {
        "ok": bool(ok),
        "message": message,
        "score": score,
        "auth": auth_status_payload(),
    }


@app.post("/security/admin-mode")
def set_security_admin_mode(request: AutonomousModeRequest) -> dict:
    ok, message = enable_admin_mode() if request.enabled else disable_admin_mode()
    return {
        "ok": bool(ok),
        "message": message,
        "auth": auth_status_payload(),
    }


@app.post("/security/lockdown")
def set_security_lockdown(request: AutonomousModeRequest) -> dict:
    ok, message = enable_lockdown("api request") if request.enabled else disable_lockdown()
    return {
        "ok": bool(ok),
        "message": message,
        "auth": auth_status_payload(),
    }


@app.get("/security/devices")
def get_security_devices() -> dict:
    security_status_payload(DEVICE_MANAGER)
    return {
        "ok": True,
        "devices": device_security_status_payload(),
    }


@app.post("/security/devices/trust")
def post_trust_device(request: DeviceTrustRequest) -> dict:
    ok, message = trust_device(request.device)
    return {
        "ok": bool(ok),
        "message": message,
        "devices": device_security_status_payload(),
    }


@app.get("/runtime")
def get_runtime_status() -> dict:
    _ensure_runtime_ready()
    return {
        "ok": True,
        "runtime": ASSISTANT_RUNTIME.status_payload(),
    }


@app.post("/runtime/thinking-mode")
def set_runtime_thinking_mode(request: ThinkingModeRequest) -> dict:
    _ensure_runtime_ready()
    return {
        "ok": True,
        "runtime": ASSISTANT_RUNTIME.set_thinking_mode(request.mode),
    }


@app.post("/runtime/autonomous-mode")
def set_runtime_autonomous_mode(request: AutonomousModeRequest) -> dict:
    _ensure_runtime_ready()
    return {
        "ok": True,
        "runtime": ASSISTANT_RUNTIME.set_autonomous_mode(request.enabled),
    }


@app.get("/agents")
def get_agent_statuses() -> dict:
    _ensure_runtime_ready()
    return {
        "ok": True,
        "agents": ASSISTANT_RUNTIME.agent_statuses(),
    }


@app.get("/agents/bus")
def get_agent_bus_events(limit: int = 25) -> dict:
    _ensure_runtime_ready()
    return {
        "ok": True,
        "bus": ASSISTANT_RUNTIME.bus.stats(),
        "events": ASSISTANT_RUNTIME.recent_bus_events(limit=limit),
    }


@app.get("/goals")
def get_runtime_goals() -> dict:
    _ensure_runtime_ready()
    return {
        "ok": True,
        "goals": ASSISTANT_RUNTIME.goals(),
    }


@app.post("/goals")
def create_runtime_goal(request: GoalPlanRequest) -> dict:
    _ensure_runtime_ready()
    goal = request.goal.strip()
    if not goal:
        raise HTTPException(status_code=400, detail="Goal is required.")
    created = ASSISTANT_RUNTIME.create_goal(goal, steps=request.steps or None, source="api")
    return {
        "ok": True,
        "goal": created,
        "goals": ASSISTANT_RUNTIME.goals(),
    }


@app.get("/plugins")
def get_plugins_status() -> dict:
    _ensure_runtime_ready()
    payload = plugin_status_payload()
    ASSISTANT_RUNTIME.state.replace_plugins(payload)
    return {
        "ok": True,
        "plugins": payload,
    }


@app.post("/plugins/reload")
def reload_plugin_registry() -> dict:
    _ensure_runtime_ready()
    payload = plugin_status_payload()
    reload_plugins()
    payload = plugin_status_payload()
    ASSISTANT_RUNTIME.state.replace_plugins(payload)
    ASSISTANT_RUNTIME.refresh_all()
    return {
        "ok": True,
        "plugins": payload,
    }


@app.post("/plugins/toggle")
def toggle_plugin(request: PluginToggleRequest) -> dict:
    _ensure_runtime_ready()
    success, message = set_plugin_enabled(request.name.strip(), request.enabled)
    if not success:
        raise HTTPException(status_code=404, detail=message)
    payload = plugin_status_payload()
    ASSISTANT_RUNTIME.state.replace_plugins(payload)
    ASSISTANT_RUNTIME.refresh_all()
    return {
        "ok": True,
        "message": message,
        "plugins": payload,
    }


@app.get("/intelligence/status")
def get_intelligence_status() -> dict:
    _ensure_runtime_ready()
    return {
        "ok": True,
        "intelligence": intelligence_status_payload(ASSISTANT_RUNTIME.status_payload()),
    }


@app.get("/learning/status")
def get_learning_status() -> dict:
    return {
        "ok": True,
        "learning": learning_status_payload(),
    }


@app.get("/insights")
def get_user_insights() -> dict:
    return {
        "ok": True,
        "insights": generate_user_insights(),
    }


@app.post("/feedback")
def submit_feedback_api(request: FeedbackRequest) -> dict:
    updated = submit_response_feedback(request.interaction_id, request.reaction, note=request.note or "", source="api")
    if not updated:
        raise HTTPException(status_code=404, detail="Interaction not found.")
    return {
        "ok": True,
        "feedback": updated,
        "learning": intelligence_status_payload(ASSISTANT_RUNTIME.status_payload()).get("learning", {}),
    }


@app.get("/memory/contextual-recall")
def get_contextual_recall(query: str, context: str = "casual", limit: int = 3) -> dict:
    clean_query = query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query is required.")
    return {
        "ok": True,
        "recall": contextual_recall_payload(clean_query, context=context, limit=limit),
    }


@app.post("/decision")
def make_decision(request: DecisionRequest) -> dict:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")
    return {
        "ok": True,
        "decision": quick_decision_payload(question, options=request.options),
    }


@app.get("/knowledge-graph")
def get_knowledge_graph(limit: int = 120) -> dict:
    return {
        "ok": True,
        "graph": build_knowledge_graph(limit=limit),
    }


@app.get("/workflows")
def get_workflows() -> dict:
    return {
        "ok": True,
        "workflows": workflow_status_payload(),
    }


@app.post("/workflows")
def create_workflow_api(request: WorkflowCreateRequest) -> dict:
    created = create_workflow(request.name, request.commands, description=request.description or "")
    if not created:
        raise HTTPException(status_code=400, detail="Workflow name and commands are required.")
    return {
        "ok": True,
        "workflow": created,
        "workflows": workflow_status_payload(),
    }


@app.post("/workflows/run")
def run_workflow_api(request: WorkflowRunRequest) -> dict:
    result = run_workflow(request.name, execute=bool(request.execute))
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("message", "Workflow not found."))
    return {
        "ok": True,
        **result,
    }


@app.get("/recovery")
def get_recovery_status() -> dict:
    return {
        "ok": True,
        "recovery": recovery_status_payload(),
    }


@app.get("/sync/status")
def get_sync_status() -> dict:
    return {
        "ok": True,
        "sync": sync_status_payload(),
    }


@app.post("/sync/config")
def configure_sync_api(request: SyncConfigRequest) -> dict:
    return {
        "ok": True,
        "sync": configure_sync(enabled=request.enabled, api_base_url=request.api_base_url),
    }


@app.get("/sync/export")
def export_sync_state() -> dict:
    return {
        "ok": True,
        "sync": export_sync_payload(),
    }


@app.post("/sync/import")
def import_sync_state(request: SyncImportRequest) -> dict:
    return {
        "ok": True,
        "sync": import_sync_payload(request.payload),
    }


@app.get("/proactive/conversation")
def get_proactive_conversation() -> dict:
    _ensure_runtime_ready()
    return {
        "ok": True,
        "proactive": intelligence_status_payload(ASSISTANT_RUNTIME.status_payload()).get("proactive_conversation", {}),
    }


@app.get("/mood")
def get_mood_status() -> dict:
    return {
        "ok": True,
        "mood": mood_status_payload(),
    }


@app.post("/mood/reset")
def reset_mood_status() -> dict:
    return {
        "ok": True,
        "mood": reset_mood_memory(),
    }


@app.get("/memory/status")
def get_memory_status() -> dict:
    return {
        "ok": True,
        "memory": semantic_memory_status(prewarm=False),
    }


@app.post("/memory/search")
def search_memory_endpoint(request: SemanticMemorySearchRequest) -> dict:
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required.")

    return {
        "ok": True,
        "query": query,
        "results": search_semantic_memory(query, limit=request.limit),
        "memory": semantic_memory_status(prewarm=True),
    }


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, http_request: Request = None) -> dict:
    _ensure_runtime_ready()
    _enforce_api_auth(http_request)
    user_id = _authenticated_user_id(http_request)
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")
    prompt_guard = validate_prompt_text(prompt, source="chat-api-ask")
    if not prompt_guard.get("allowed", True):
        append_security_activity(
            "assistant_response",
            source="chat-api-ask",
            message="Prompt blocked before LLM execution.",
            command=prompt,
            response=prompt_guard.get("message", "Unsafe prompt blocked."),
        )
        append_chat_message(
            "ask-api",
            "assistant",
            prompt_guard.get("message", "Unsafe prompt blocked."),
            user_id=user_id,
            source="chat-api-ask",
            metadata={"route": "security-block"},
        )
        return {
            "ok": False,
            "prompt": prompt,
            "mode": request.mode or "auto",
            "route": "security-block",
            "model": "security-layer",
            "response": prompt_guard.get("message", "Unsafe prompt blocked."),
            "interaction_id": None,
            "emotion": None,
            "mood": mood_status_payload(),
            "hardware": DEVICE_MANAGER.get_status(),
            "hardware_context_used": False,
        }
    append_chat_message(
        "ask-api",
        "user",
        prompt,
        user_id=user_id,
        source="chat-api-ask",
        metadata={"mode": request.mode or "auto"},
    )
    emotion = analyze_emotion(prompt)
    mood = record_mood_from_analysis(prompt, emotion, source="chat-api-ask")
    runtime_observation = ASSISTANT_RUNTIME.observe_user_message(prompt, source="chat-api-ask", emotion=emotion, mood=mood)
    context = runtime_observation.get("context", "casual")
    observe_user_turn(
        prompt,
        context=context,
        emotion=emotion.get("emotion", "neutral"),
        mood=mood.get("last_mood", "neutral"),
        source="chat-api-ask",
    )

    iot_resolution = resolve_iot_control_command(prompt)
    if iot_resolution.get("matched"):
        control_result = execute_iot_control(prompt, confirm=False)
        ASSISTANT_RUNTIME.observe_assistant_reply(control_result.get("message", ""), source="chat-api-ask")
        interaction = record_assistant_turn(
            prompt,
            control_result.get("message", ""),
            context=context,
            emotion=emotion.get("emotion", "neutral"),
            mood=mood.get("last_mood", "neutral"),
            source="chat-api-ask",
            route="iot-control",
            model="iot-controller",
        )
        append_chat_message(
            "ask-api",
            "assistant",
            control_result.get("message", ""),
            user_id=user_id,
            source="chat-api-ask",
            emotion=emotion.get("emotion", "neutral"),
            metadata={"route": "iot-control", "model": "iot-controller"},
        )
        return {
            "ok": bool(control_result.get("ok")),
            "prompt": prompt,
            "mode": request.mode or "auto",
            "route": "iot-control",
            "model": "iot-controller",
            "response": control_result.get("message", ""),
            "interaction_id": interaction.get("id"),
            "emotion": emotion,
            "mood": mood,
            "hardware": DEVICE_MANAGER.get_status(),
            "iot": DEVICE_MANAGER.get_iot_status(),
            "iot_control": control_result,
            "hardware_context_used": True,
        }

    local_response = DEVICE_MANAGER.local_response(prompt)
    if local_response:
        append_security_activity(
            "assistant_response",
            source="chat-api-ask",
            message="Local device response returned.",
            command=prompt,
            response=local_response,
        )
        ASSISTANT_RUNTIME.observe_assistant_reply(local_response, source="chat-api-ask")
        interaction = record_assistant_turn(
            prompt,
            local_response,
            context=context,
            emotion=emotion.get("emotion", "neutral"),
            mood=mood.get("last_mood", "neutral"),
            source="chat-api-ask",
            route="hardware-local",
            model="device-manager",
        )
        append_chat_message(
            "ask-api",
            "assistant",
            local_response,
            user_id=user_id,
            source="chat-api-ask",
            emotion=emotion.get("emotion", "neutral"),
            metadata={"route": "hardware-local", "model": "device-manager"},
        )
        return {
            "ok": True,
            "prompt": prompt,
            "mode": request.mode or "auto",
            "route": "hardware-local",
            "model": "device-manager",
            "response": local_response,
            "interaction_id": interaction.get("id"),
            "emotion": emotion,
            "mood": mood,
            "hardware": DEVICE_MANAGER.get_status(),
            "hardware_context_used": True,
        }

    effective_prompt, hardware_context = _hardware_aware_prompt(prompt)
    routing = select_route(prompt, mode=request.mode)
    try:
        result = generate_offline_reply(effective_prompt, mode=routing["route"])
    except OfflineAssistantError as error:
        record_system_error("chat-api-ask", str(error), metadata={"route": routing.get("route", "")})
        raise HTTPException(status_code=503, detail=str(error)) from error
    ASSISTANT_RUNTIME.observe_assistant_reply(result["response"], source="chat-api-ask")
    interaction = record_assistant_turn(
        prompt,
        result["response"],
        context=context,
        emotion=emotion.get("emotion", "neutral"),
        mood=mood.get("last_mood", "neutral"),
        source="chat-api-ask",
        route=result["route"],
        model=result["model"],
    )
    append_security_activity(
        "assistant_response",
        source="chat-api-ask",
        message="LLM response returned.",
        command=prompt,
        response=result["response"],
    )
    append_chat_message(
        "ask-api",
        "assistant",
        result["response"],
        user_id=user_id,
        source="chat-api-ask",
        emotion=emotion.get("emotion", "neutral"),
        metadata={"route": result["route"], "model": result["model"]},
    )
    log_audit_event(
        "chat",
        "ask_reply",
        user_id=user_id,
        payload={"route": result["route"], "model": result["model"]},
    )

    return {
        "ok": True,
        "prompt": prompt,
        "mode": routing["mode"],
        "route": result["route"],
        "model": result["model"],
        "response": result["response"],
        "interaction_id": interaction.get("id"),
        "emotion": emotion,
        "mood": mood,
        "hardware": DEVICE_MANAGER.get_status(),
        "hardware_context_used": hardware_context is not None,
    }


@app.get("/chat/history")
def get_chat_history() -> dict:
    return {"ok": True, "messages": CHAT_HISTORY}


@app.post("/chat/reset")
def reset_chat() -> dict:
    CHAT_HISTORY.clear()
    return {"ok": True}


@app.post("/chat")
def chat(request: ChatRequest, http_request: Request = None) -> dict:
    _ensure_runtime_ready()
    _enforce_api_auth(http_request)
    user_id = _authenticated_user_id(http_request)
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")
    prompt_guard = validate_prompt_text(message, source="chat-api-chat")
    if not prompt_guard.get("allowed", True):
        assistant_item = _history_item("assistant", prompt_guard.get("message", "Unsafe prompt blocked."))
        CHAT_HISTORY.append(_history_item("user", message))
        CHAT_HISTORY.append(assistant_item)
        _trim_history()
        append_security_activity(
            "assistant_response",
            source="chat-api-chat",
            message="Prompt blocked before LLM execution.",
            command=message,
            response=assistant_item["content"],
        )
        return {
            "ok": False,
            "reply": assistant_item["content"],
            "messages": CHAT_HISTORY,
            "emotion": analyze_emotion(message),
            "mood": mood_status_payload(),
            "interaction_id": None,
        }
    emotion = analyze_emotion(message)
    mood = record_mood_from_analysis(message, emotion, source="chat-api-chat")
    runtime_observation = ASSISTANT_RUNTIME.observe_user_message(message, source="chat-api-chat", emotion=emotion, mood=mood)
    context = runtime_observation.get("context", "casual")
    observe_user_turn(
        message,
        context=context,
        emotion=emotion.get("emotion", "neutral"),
        mood=mood.get("last_mood", "neutral"),
        source="chat-api-chat",
    )

    try:
        user_item = _history_item("user", message)
        append_chat_message(
            "chat-api-default",
            "user",
            message,
            user_id=user_id,
            source="chat-api-chat",
            emotion=emotion.get("emotion", "neutral"),
            metadata={"context": context},
        )
        reply = generate_chat_reply(CHAT_HISTORY, _chat_prompt_with_memory(message, mood_snapshot=mood, context=context))
        assistant_item = _history_item("assistant", reply)
    except Exception as error:
        record_system_error("chat-api-chat", str(error), metadata={"context": context})
        raise HTTPException(status_code=500, detail=f"AI request failed: {error}") from error

    CHAT_HISTORY.extend([user_item, assistant_item])
    _trim_history()
    ASSISTANT_RUNTIME.observe_assistant_reply(reply, source="chat-api-chat")
    interaction = record_assistant_turn(
        message,
        reply,
        context=context,
        emotion=emotion.get("emotion", "neutral"),
        mood=mood.get("last_mood", "neutral"),
        source="chat-api-chat",
        route="chat",
        model="chat-provider",
    )
    append_security_activity(
        "assistant_response",
        source="chat-api-chat",
        message="Chat reply returned.",
        command=message,
        response=reply,
    )
    append_chat_message(
        "chat-api-default",
        "assistant",
        reply,
        user_id=user_id,
        source="chat-api-chat",
        emotion=emotion.get("emotion", "neutral"),
        metadata={"route": "chat", "model": "chat-provider"},
    )
    log_audit_event(
        "chat",
        "chat_reply",
        user_id=user_id,
        payload={"interaction_id": interaction.get("id")},
    )
    return {"ok": True, "reply": reply, "interaction_id": interaction.get("id"), "emotion": emotion, "mood": mood, "message": assistant_item, "messages": CHAT_HISTORY}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, http_request: Request = None) -> StreamingResponse:
    _ensure_runtime_ready()
    _enforce_api_auth(http_request)
    user_id = _authenticated_user_id(http_request)
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")
    prompt_guard = validate_prompt_text(message, source="chat-api-stream")
    if not prompt_guard.get("allowed", True):
        async def blocked_stream() -> AsyncGenerator[str, None]:
            yield f"data: {json.dumps({'type': 'delta', 'content': prompt_guard.get('message', 'Unsafe prompt blocked.')})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': prompt_guard.get('message', 'Unsafe prompt blocked.'), 'interaction_id': None})}\n\n"

        return StreamingResponse(blocked_stream(), media_type="text/event-stream")
    emotion = analyze_emotion(message)
    mood = record_mood_from_analysis(message, emotion, source="chat-api-stream")
    runtime_observation = ASSISTANT_RUNTIME.observe_user_message(message, source="chat-api-stream", emotion=emotion, mood=mood)
    context = runtime_observation.get("context", "casual")
    observe_user_turn(
        message,
        context=context,
        emotion=emotion.get("emotion", "neutral"),
        mood=mood.get("last_mood", "neutral"),
        source="chat-api-stream",
    )

    user_item = _history_item("user", message)
    CHAT_HISTORY.append(user_item)
    _trim_history()
    append_chat_message(
        "chat-api-default",
        "user",
        message,
        user_id=user_id,
        source="chat-api-stream",
        emotion=emotion.get("emotion", "neutral"),
        metadata={"context": context},
    )

    async def event_stream() -> AsyncGenerator[str, None]:
        full_reply = ""
        prompt_message = _chat_prompt_with_memory(message, mood_snapshot=mood, context=context)
        try:
            yield f"data: {json.dumps({'type': 'emotion', 'emotion': emotion})}\n\n"
            yield f"data: {json.dumps({'type': 'mood', 'mood': mood})}\n\n"
            for chunk in stream_chat_reply(CHAT_HISTORY[:-1], prompt_message):
                full_reply += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            assistant_item = _history_item("assistant", full_reply.strip() or "I could not generate a reply right now.")
            CHAT_HISTORY.append(assistant_item)
            _trim_history()
            append_chat_message(
                "chat-api-default",
                "assistant",
                assistant_item["content"],
                user_id=user_id,
                source="chat-api-stream",
                emotion=emotion.get("emotion", "neutral"),
                metadata={"route": "chat-stream", "model": "chat-provider"},
            )
            ASSISTANT_RUNTIME.observe_assistant_reply(assistant_item["content"], source="chat-api-stream")
            interaction = record_assistant_turn(
                message,
                assistant_item["content"],
                context=context,
                emotion=emotion.get("emotion", "neutral"),
                mood=mood.get("last_mood", "neutral"),
                source="chat-api-stream",
                route="chat-stream",
                model="chat-provider",
            )
            log_audit_event(
                "chat",
                "chat_stream_reply",
                user_id=user_id,
                payload={"interaction_id": interaction.get("id")},
            )
            yield f"data: {json.dumps({'type': 'done', 'message': assistant_item, 'interaction_id': interaction.get('id')})}\n\n"
        except Exception as error:
            record_system_error("chat-api-stream", str(error), metadata={"context": context})
            yield f"data: {json.dumps({'type': 'error', 'error': f'AI request failed: {error}'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
