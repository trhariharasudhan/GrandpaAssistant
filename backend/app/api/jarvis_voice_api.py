from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel


router = APIRouter(prefix="/api/jarvis", tags=["jarvis-voice"])


def _compact_text(value, limit: int = 1000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


class JarvisSettingsRequest(BaseModel):
    enabled: bool | None = None
    wake_words: list[str] | None = None
    continuous_listening: bool | None = None
    push_to_talk_enabled: bool | None = None
    stt_backend: str | None = None
    tts_backend: str | None = None
    fallback_tts_backend: str | None = None
    voice_profile: str | None = None
    language: str | None = None
    multilingual: bool | None = None
    vad_enabled: bool | None = None
    noise_suppression_enabled: bool | None = None
    auto_mute: bool | None = None
    interruptible: bool | None = None
    streaming_enabled: bool | None = None
    emotion_aware: bool | None = None
    listen_timeout_seconds: float | None = None
    idle_sleep_seconds: float | None = None
    response_latency_target_ms: int | None = None
    max_reply_chars_for_voice: int | None = None


class JarvisPushToTalkRequest(BaseModel):
    transcript: str | None = None
    session_id: str | None = None


class JarvisMuteRequest(BaseModel):
    muted: bool
    session_id: str | None = None


def _jarvis_manager():
    from core.jarvis_voice.manager import get_global_voice_manager

    return get_global_voice_manager()


@router.get("/status")
def jarvis_status():
    return {"ok": True, "jarvis": _jarvis_manager().status()}


@router.post("/start")
def jarvis_start():
    from core.jarvis_voice.manager import start_global_voice_manager

    return start_global_voice_manager()


@router.post("/stop")
def jarvis_stop():
    from core.jarvis_voice.manager import stop_global_voice_manager

    return stop_global_voice_manager()


@router.post("/interrupt")
def jarvis_interrupt(request: JarvisPushToTalkRequest | None = None):
    session_id = _compact_text((request.session_id if request else "") or "jarvis-voice")
    return _jarvis_manager().interrupt(session_id=session_id)


@router.post("/mute")
def jarvis_mute(request: JarvisMuteRequest):
    return _jarvis_manager().set_muted(bool(request.muted), session_id=_compact_text(request.session_id) or "jarvis-voice")


@router.get("/settings")
def jarvis_settings():
    from core.jarvis_voice.settings import voice_settings_status

    return {"ok": True, "settings": voice_settings_status()}


@router.post("/settings")
def jarvis_update_settings(request: JarvisSettingsRequest):
    updates = {key: value for key, value in request.model_dump().items() if value is not None}
    return {"ok": True, "jarvis": _jarvis_manager().update_settings(updates)}


@router.post("/push-to-talk")
def jarvis_push_to_talk(request: JarvisPushToTalkRequest):
    session_id = _compact_text(request.session_id) or "jarvis-ptt"
    return _jarvis_manager().push_to_talk(request.transcript, session_id=session_id)


@router.websocket("/ws")
async def jarvis_websocket(websocket: WebSocket):
    await websocket.accept()
    manager = _jarvis_manager()
    await websocket.send_json({"type": "status", "jarvis": manager.status()})
    try:
        while True:
            payload = await websocket.receive_json()
            if not isinstance(payload, dict):
                await websocket.send_json({"type": "error", "error": "Expected a JSON object."})
                continue
            event_type = _compact_text(payload.get("type"))
            session_id = _compact_text(payload.get("session_id")) or "jarvis-ws"
            if event_type == "status":
                await websocket.send_json({"type": "status", "jarvis": manager.status()})
                continue
            if event_type == "interrupt":
                await websocket.send_json({"type": "interrupt", **manager.interrupt(session_id=session_id)})
                continue
            if event_type == "mute":
                await websocket.send_json({"type": "mute", **manager.set_muted(bool(payload.get("muted")), session_id=session_id)})
                continue
            transcript = _compact_text(payload.get("transcript"))
            if event_type == "push_to_talk":
                result = manager.push_to_talk(transcript, session_id=session_id)
                await websocket.send_json({"type": "done", **result})
                continue
            if event_type in {"transcript", "command", ""}:
                for event in manager.stream_transcript(transcript, session_id=session_id, source="websocket"):
                    await websocket.send_json(event)
                continue
            await websocket.send_json({"type": "error", "error": f"Unsupported Jarvis websocket event: {event_type}"})
    except WebSocketDisconnect:
        return
