from datetime import datetime
import json
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from llm_client import generate_chat_reply, stream_chat_reply
from offline_multi_model import (
    OfflineAssistantError,
    generate_offline_reply,
    get_ollama_status,
    list_installed_models,
)


app = FastAPI(title="Grandpa Assistant Chat API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


CHAT_HISTORY: list[dict] = []


class ChatRequest(BaseModel):
    message: str


class AskRequest(BaseModel):
    prompt: str
    mode: str | None = "auto"


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


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "grandpa-assistant-fastapi",
        "offline_assistant": get_ollama_status(),
    }


@app.get("/models")
def get_models() -> dict:
    try:
        return {
            "ok": True,
            "models": list_installed_models(),
        }
    except OfflineAssistantError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/ask")
def ask(request: AskRequest) -> dict:
    try:
        result = generate_offline_reply(request.prompt, mode=request.mode)
    except OfflineAssistantError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return {
        "ok": True,
        **result,
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
        reply = generate_chat_reply(CHAT_HISTORY, message)
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
        try:
            for chunk in stream_chat_reply(CHAT_HISTORY[:-1], message):
                full_reply += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            assistant_item = _history_item("assistant", full_reply.strip() or "I could not generate a reply right now.")
            CHAT_HISTORY.append(assistant_item)
            _trim_history()
            yield f"data: {json.dumps({'type': 'done', 'message': assistant_item})}\n\n"
        except Exception as error:
            yield f"data: {json.dumps({'type': 'error', 'error': f'AI request failed: {error}'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
