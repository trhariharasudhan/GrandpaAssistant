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
from startup_diagnostics import collect_startup_diagnostics
from utils.config import get_last_settings_validation, load_settings
from voice.speak import autoconfigure_piper_model, piper_setup_payload


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


class BaseEnvelope(BaseModel):
    ok: bool


class DoctorResponse(BaseEnvelope):
    doctor: dict[str, Any]


class HealthResponse(BaseEnvelope):
    service: str
    offline_assistant: dict[str, Any]
    hardware: dict[str, Any]
    iot: dict[str, Any]
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


class IoTValidationResponse(BaseEnvelope):
    validation: dict[str, Any]


class AskResponse(BaseEnvelope):
    prompt: str
    mode: str
    route: str
    model: str
    response: str
    hardware_context_used: bool
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


def _chat_prompt_with_memory(message: str) -> str:
    memory_context = build_semantic_memory_context(message)
    if not memory_context:
        return message
    return (
        f"{memory_context}\n\n"
        f"User question: {message}\n"
        "Answer naturally. Use the saved memory only when it helps with the user's question."
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
    return {
        "ok": True,
        "service": "grandpa-assistant-fastapi",
        "offline_assistant": get_ollama_status(),
        "hardware": DEVICE_MANAGER.get_status(),
        "iot": DEVICE_MANAGER.get_iot_status(),
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


@app.get("/doctor", response_model=DoctorResponse)
def doctor() -> dict:
    return {
        "ok": True,
        "doctor": collect_startup_diagnostics(use_cache=False),
    }


@app.on_event("startup")
def startup_device_monitor() -> None:
    ensure_log_dir()
    load_settings()
    DEVICE_MANAGER.start()


@app.on_event("shutdown")
def shutdown_device_monitor() -> None:
    DEVICE_MANAGER.stop()


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
def get_status() -> dict:
    return {
        "ok": True,
        "assistant": {
            "service": "grandpa-assistant-fastapi",
            "offline_assistant": get_ollama_status(),
            "hardware": DEVICE_MANAGER.get_status(),
            "iot": DEVICE_MANAGER.get_iot_status(),
            "semantic_memory": semantic_memory_status(prewarm=False),
        },
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
def ask(request: AskRequest) -> dict:
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    iot_resolution = resolve_iot_control_command(prompt)
    if iot_resolution.get("matched"):
        control_result = execute_iot_control(prompt, confirm=False)
        return {
            "ok": bool(control_result.get("ok")),
            "prompt": prompt,
            "mode": request.mode or "auto",
            "route": "iot-control",
            "model": "iot-controller",
            "response": control_result.get("message", ""),
            "hardware": DEVICE_MANAGER.get_status(),
            "iot": DEVICE_MANAGER.get_iot_status(),
            "iot_control": control_result,
            "hardware_context_used": True,
        }

    local_response = DEVICE_MANAGER.local_response(prompt)
    if local_response:
        return {
            "ok": True,
            "prompt": prompt,
            "mode": request.mode or "auto",
            "route": "hardware-local",
            "model": "device-manager",
            "response": local_response,
            "hardware": DEVICE_MANAGER.get_status(),
            "hardware_context_used": True,
        }

    effective_prompt, hardware_context = _hardware_aware_prompt(prompt)
    routing = select_route(prompt, mode=request.mode)
    try:
        result = generate_offline_reply(effective_prompt, mode=routing["route"])
    except OfflineAssistantError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return {
        "ok": True,
        "prompt": prompt,
        "mode": routing["mode"],
        "route": result["route"],
        "model": result["model"],
        "response": result["response"],
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
def chat(request: ChatRequest) -> dict:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")

    try:
        user_item = _history_item("user", message)
        reply = generate_chat_reply(CHAT_HISTORY, _chat_prompt_with_memory(message))
        assistant_item = _history_item("assistant", reply)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"AI request failed: {error}") from error

    CHAT_HISTORY.extend([user_item, assistant_item])
    _trim_history()
    return {"ok": True, "reply": reply, "message": assistant_item, "messages": CHAT_HISTORY}


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")

    user_item = _history_item("user", message)
    CHAT_HISTORY.append(user_item)
    _trim_history()

    async def event_stream() -> AsyncGenerator[str, None]:
        full_reply = ""
        prompt_message = _chat_prompt_with_memory(message)
        try:
            for chunk in stream_chat_reply(CHAT_HISTORY[:-1], prompt_message):
                full_reply += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            assistant_item = _history_item("assistant", full_reply.strip() or "I could not generate a reply right now.")
            CHAT_HISTORY.append(assistant_item)
            _trim_history()
            yield f"data: {json.dumps({'type': 'done', 'message': assistant_item})}\n\n"
        except Exception as error:
            yield f"data: {json.dumps({'type': 'error', 'error': f'AI request failed: {error}'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
