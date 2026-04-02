import contextlib
import datetime
import importlib.util
import io
import json
import os
import subprocess
import threading
import time
import uuid
import zipfile
from xml.etree import ElementTree

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pypdf import PdfReader
from pydantic import BaseModel
import uvicorn

import core.command_router as command_router_module
from brain.database import get_recent_commands
from brain.memory_engine import get_memory
from core.command_router import process_command
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
from modules.event_module import get_event_data
from modules.google_contacts_module import CACHE_PATH as GOOGLE_CONTACTS_CACHE_PATH
from modules.google_contacts_module import (
    get_recent_contact_change_summary,
    list_contact_aliases,
    list_favorite_contacts,
)
from modules.health_module import get_system_status
from modules.notes_module import latest_note
from modules.startup_module import (
    disable_startup_auto_launch,
    enable_startup_auto_launch,
    startup_auto_launch_status,
)
from modules.task_module import get_task_data
from modules.weather_module import get_weather_report
from utils.config import get_setting, update_setting
from vision.object_detection import (
    get_detection_history,
    get_latest_detection_summary,
    get_object_detection_model_name,
    get_object_detection_presets,
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
    current_voice_mode,
    is_interrupt_phrase,
    listen,
    looks_like_direct_command,
    strip_wake_word,
    wake_word_detected,
)
import voice.speak as voice_speak_module


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
load_env_file(os.path.join(PROJECT_ROOT, ".env"))
DATA_DIR = os.path.join(PROJECT_ROOT, "backend", "data")
CHAT_STATE_PATH = os.path.join(DATA_DIR, "chat_state.json")

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
_voice_diagnostics = {
    "wake_detection_count": 0,
    "wake_only_count": 0,
    "command_count": 0,
    "follow_up_command_count": 0,
    "retry_window_command_count": 0,
    "direct_fallback_count": 0,
    "interrupt_count": 0,
    "error_count": 0,
    "last_heard_phrase": "",
    "last_heard_at": "",
    "last_processed_command": "",
    "last_command_at": "",
    "last_wake_at": "",
    "last_interrupt_at": "",
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
    "tone": "friendly",
    "response_style": "balanced",
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


def _compact_text(value):
    return " ".join(str(value or "").split()).strip()


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _save_chat_state():
    _ensure_data_dir()
    payload = {
        "settings": _chat_settings,
        "session_order": _session_order,
        "sessions": _chat_sessions,
    }
    try:
        with open(CHAT_STATE_PATH, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
    except Exception:
        return


def _apply_runtime_chat_settings():
    os.environ[LLM_PROVIDER_ENV] = _compact_text(_chat_settings.get("llm_provider")) or DEFAULT_LLM_PROVIDER
    os.environ[OPENAI_MODEL_ENV] = _compact_text(_chat_settings.get("model")) or DEFAULT_OPENAI_MODEL
    os.environ[OLLAMA_MODEL_ENV] = _compact_text(_chat_settings.get("ollama_model")) or DEFAULT_OLLAMA_MODEL


def _load_chat_state():
    global _chat_settings, _chat_sessions, _session_order
    _ensure_data_dir()
    if not os.path.exists(CHAT_STATE_PATH):
        return
    try:
        with open(CHAT_STATE_PATH, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:
        return

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


def _safe_call(callback, fallback):
    try:
        value = callback()
    except Exception:
        return fallback
    return fallback if value is None else value


def _local_now_label():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _reset_voice_diagnostics():
    global _voice_diagnostics
    _voice_diagnostics = {
        "wake_detection_count": 0,
        "wake_only_count": 0,
        "command_count": 0,
        "follow_up_command_count": 0,
        "retry_window_command_count": 0,
        "direct_fallback_count": 0,
        "interrupt_count": 0,
        "error_count": 0,
        "last_heard_phrase": "",
        "last_heard_at": "",
        "last_processed_command": "",
        "last_command_at": "",
        "last_wake_at": "",
        "last_interrupt_at": "",
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
    global _voice_diagnostics
    source = _compact_text(source) or "direct"
    _voice_diagnostics["command_count"] += 1
    _voice_diagnostics["last_processed_command"] = _compact_text(heard)
    _voice_diagnostics["last_command_at"] = _local_now_label()
    if source == "follow_up":
        _voice_diagnostics["follow_up_command_count"] += 1
    elif source == "retry_window":
        _voice_diagnostics["retry_window_command_count"] += 1
    elif source == "direct_fallback":
        _voice_diagnostics["direct_fallback_count"] += 1


def _mark_voice_interrupt():
    global _voice_diagnostics
    _voice_diagnostics["interrupt_count"] += 1
    _voice_diagnostics["last_interrupt_at"] = _local_now_label()


def _mark_voice_error(message):
    global _voice_diagnostics
    _voice_diagnostics["error_count"] += 1
    _voice_diagnostics["last_error_at"] = _local_now_label()
    _voice_diagnostics["last_error_message"] = _compact_text(message)


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
    credentials_path = os.path.join(DATA_DIR, "iot_credentials.json")
    creds = _load_local_json(credentials_path)
    if not creds:
        return {
            "configured": False,
            "enabled": False,
            "device_count": 0,
            "sample_commands": [],
            "placeholder_count": 0,
            "summary": "Smart Home is not configured yet.",
        }

    webhooks = creds.get("webhooks") or {}
    sample_commands = list(webhooks.keys())[:4]
    placeholder_count = 0
    for config in webhooks.values():
        url = str((config or {}).get("url") or "")
        if "YOUR_KEY_HERE" in url or "YOUR_HOME_ASSISTANT_WEBHOOK_ID" in url:
            placeholder_count += 1

    enabled = bool(creds.get("enabled"))
    summary_parts = [
        f"Smart Home is {'enabled' if enabled else 'disabled'} with {len(webhooks)} configured command(s)."
    ]
    if sample_commands:
        summary_parts.append("Try " + " | ".join(sample_commands[:3]) + ".")
    elif enabled:
        summary_parts.append("Add webhook commands to start controlling devices.")
    if placeholder_count:
        summary_parts.append(f"{placeholder_count} command(s) still use placeholder keys.")

    return {
        "configured": True,
        "enabled": enabled,
        "device_count": len(webhooks),
        "sample_commands": sample_commands,
        "placeholder_count": placeholder_count,
        "summary": " ".join(summary_parts),
    }


def _face_security_payload():
    profile_path = os.path.join(DATA_DIR, "face_profile.json")
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

    query_tokens = set(_tokenize_for_rag(query))
    query_text = str(query or "").lower()
    generic_doc_query = any(
        phrase in query_text
        for phrase in ["document", "pdf", "docx", "file", "attachment", "summarize", "summary"]
    )
    if not query_tokens and not generic_doc_query:
        return None

    scored_chunks = []
    for document in documents:
        for index, chunk in enumerate(document.get("chunks") or []):
            chunk_tokens = set(_tokenize_for_rag(chunk))
            overlap = len(query_tokens & chunk_tokens)
            if not overlap and not generic_doc_query:
                continue
            score = overlap / max(1, len(query_tokens)) if query_tokens else 0.05
            scored_chunks.append((score, document.get("name", "Document"), index, chunk))

    if not scored_chunks:
        return None

    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    selected = []
    used_chars = 0
    for _, name, index, chunk in scored_chunks[: max_chunks * 2]:
        block = f"[Source: {name} | chunk {index + 1}]\n{chunk}"
        if used_chars + len(block) > max_chars and selected:
            break
        selected.append(block)
        used_chars += len(block)
        if len(selected) >= max_chunks:
            break

    if not selected:
        return None

    return (
        "Use the attached document context below to answer the user's question. "
        "When using information from the documents, you MUST explicitly cite the source document name in your answer. "
        "For example: 'According to [Document Name], ...' or '... (Source: [Document Name])'. "
        "If the document does not contain the answer, say that briefly.\n\n"
        + "\n\n".join(selected)
    )


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


def _effective_system_prompt():
    provider = _compact_text(_chat_settings.get("llm_provider")).lower() or DEFAULT_LLM_PROVIDER
    provider_guidance = ""
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
        f"{provider_guidance} "
        f"{_tool_prompt() if _chat_settings.get('tool_mode') else ''}"
    ).strip()


def _build_chat_input(session, user_message):
    document_context = _session_document_context(session, user_message)
    if not document_context:
        return user_message
    return (
        f"{document_context}\n\n"
        f"User question: {user_message}\n"
        "Answer clearly using the document context when relevant. "
        "If the document does not contain the answer, say that briefly."
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
    spoken_messages = []
    original_router_speak = command_router_module.speak
    original_voice_speak = voice_speak_module.speak
    buffer = io.StringIO()

    def capture_speak(text, *args, **kwargs):
        cleaned = _compact_text(text)
        if cleaned:
            spoken_messages.append(cleaned)

    command_router_module.speak = capture_speak
    voice_speak_module.speak = capture_speak
    try:
        with contextlib.redirect_stdout(buffer):
            process_command((command or "").lower().strip(), _installed_apps, input_mode="text")
    finally:
        command_router_module.speak = original_router_speak
        voice_speak_module.speak = original_voice_speak

    if spoken_messages:
        return spoken_messages

    output = _compact_text(buffer.getvalue())
    if output:
        return [output]
    return ["Command completed."]


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


def _run_tool_aware_reply(history, user_message):
    first_pass = generate_chat_reply(
        history,
        user_message,
        model=_chat_settings["model"],
        system_prompt=_effective_system_prompt(),
    )
    if _chat_settings.get("tool_mode") and first_pass.startswith("TOOL:"):
        command = _compact_text(first_pass.replace("TOOL:", "", 1))
        if not _looks_like_tool_command(command):
            return command or first_pass, None, [], None
        if _is_risky_command(command):
            return (
                f"I can do that, but I need confirmation first: {command}",
                command,
                [],
                _create_confirmation(command, source="chat-tool"),
            )
        tool_messages = _capture_command_reply(command)
        tool_summary = "\n".join(tool_messages)
        bridge_message = (
            f"User request: {user_message}\n"
            f"Tool command used: {command}\n"
            f"Tool result: {tool_summary}\n"
            "Now answer the user naturally using that result."
        )
        final_reply = generate_chat_reply(
            history,
            bridge_message,
            model=_chat_settings["model"],
            system_prompt=_chat_settings["system_prompt"],
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
    _set_voice_follow_up(datetime.datetime.now().timestamp() + follow_up_timeout)
    _voice_state_label = "follow_up"
    _set_voice_state(activity="Follow-up", transcript="Listening for follow-up command...", error="")


def _voice_loop():
    global _voice_enabled, _voice_state_label
    wake_retry_until = 0.0
    while _voice_enabled:
        try:
            settings = _active_voice_settings()
            wake_word = _compact_text(get_setting("wake_word", "hey grandpa")) or "hey grandpa"
            follow_up_timeout = float(settings.get("follow_up_timeout_seconds", 12) or 12)
            wake_retry_window = float(settings.get("wake_retry_window_seconds", 6) or 6)
            wake_direct_fallback = bool(settings.get("wake_direct_fallback_enabled", True))
            post_wake_pause = max(0.0, min(1.0, float(settings.get("post_wake_pause_seconds", 0.35) or 0.35)))
            interrupt_hold = max(0.0, min(1.0, float(get_setting("voice.interrupt_state_hold_seconds", 0.35) or 0.35)))
            now_ts = datetime.datetime.now().timestamp()
            follow_up_active = _voice_follow_up_until > now_ts

            if follow_up_active:
                _voice_state_label = "follow_up"
                _set_voice_state(
                    activity="Follow-up",
                    transcript=f"Listening for follow-up... {_voice_follow_up_remaining()}s left",
                    error="",
                )
                heard = listen(for_wake_word=False)
            else:
                _voice_state_label = "sleeping"
                _set_voice_state(activity="Sleeping", transcript=f"Say {wake_word} to wake me.", error="")
                heard = listen(for_wake_word=True)

            if not _voice_enabled:
                break
            if not heard:
                continue
            _mark_voice_heard(heard)

            if is_interrupt_phrase(heard):
                voice_speak_module.stop_speaking()
                _mark_voice_interrupt()
                _set_voice_follow_up(datetime.datetime.now().timestamp() + 4)
                _voice_state_label = "interrupted"
                _set_voice_state(activity="Interrupted", transcript="Stopped speaking. Listening again.", error="")
                if interrupt_hold > 0:
                    time.sleep(interrupt_hold)
                continue

            if follow_up_active:
                _handle_voice_command(heard, follow_up_timeout, source="follow_up")
                continue

            if wake_word_detected(heard, wake_word):
                trailing_command = strip_wake_word(heard, wake_word)
                wake_retry_until = datetime.datetime.now().timestamp() + wake_retry_window
                _mark_voice_wake(wake_retry_until)
                if trailing_command:
                    _handle_voice_command(trailing_command, follow_up_timeout, source="wake_inline")
                else:
                    _voice_diagnostics["wake_only_count"] += 1
                    _set_voice_follow_up(datetime.datetime.now().timestamp() + follow_up_timeout)
                    _voice_state_label = "awake"
                    _set_voice_state(activity="Awake", transcript="Wake word heard. Listening now.", error="")
                    voice_speak_module.speak("Yes?")
                    if post_wake_pause > 0:
                        time.sleep(post_wake_pause)
                continue

            if wake_retry_until and datetime.datetime.now().timestamp() <= wake_retry_until and looks_like_direct_command(heard):
                _handle_voice_command(heard, follow_up_timeout, source="retry_window")
                continue

            if wake_direct_fallback and looks_like_direct_command(heard):
                _handle_voice_command(heard, follow_up_timeout, source="direct_fallback")
                continue
        except Exception as error:
            _voice_state_label = "error"
            _mark_voice_error(str(error))
            _set_voice_state(activity="Error", error=str(error))
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


def _build_ui_state():
    task_data = _safe_call(get_task_data, {"tasks": [], "reminders": []})
    event_data = _safe_call(get_event_data, {"events": []})
    tasks = task_data.get("tasks", [])
    reminders = task_data.get("reminders", [])
    events = event_data.get("events", [])
    pending_tasks = sum(1 for task in tasks if not task.get("completed"))
    overdue_count = 0
    now = datetime.datetime.now()

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
        if due_dt and due_dt < now:
            overdue_count += 1

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
    overdue_reminders = []

    for reminder in reminders:
        title = _compact_text(reminder.get("title") or reminder.get("text") or reminder.get("task") or "Reminder")
        due_label = reminder.get("due_at") or reminder.get("due_date") or ""
        if title and due_label:
            overdue_reminders.append(f"{title} - {due_label}")
        elif title:
            overdue_reminders.append(title)
        if len(overdue_reminders) >= 5:
            break

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
    notifications = []

    if overdue_count:
        notifications.append({"level": "warning", "text": f"You have {overdue_count} overdue reminder(s)."})
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


    return {
        "overview": {
            "tasks": f"{pending_tasks} pending",
            "reminders": f"{overdue_count} overdue",
            "weather": _safe_call(get_weather_report, "Weather unavailable right now."),
            "health": _safe_call(get_system_status, "Health unavailable right now."),
            "object_detection": _safe_call(get_latest_detection_summary, "No recent object detection results yet."),
        },
        "today": f"Pending tasks: {pending_tasks} | Overdue reminders: {overdue_count}",
        "next_event": next_event,
        "latest_note": note_summary,
        "recent_commands": recent_commands,
        "notifications": notifications[:6],
        "dashboard": {
            "tasks": pending_task_titles or ["No pending tasks."],
            "reminders": overdue_reminders or ["No overdue reminders."],
            "events": event_titles or ["No upcoming events."],
            "vision": [_safe_call(get_latest_detection_summary, "No recent object detection results yet.")],
        },
        "memory": {
            "preferred_language": preferred_language,
            "favorite_contact": favorite_contact,
        },
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
            "smart_home": _smart_home_status_payload(),
            "face_security": _face_security_payload(),
        },
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
        "voice": _voice_status_payload(),
        "chat_settings": _chat_settings,
        "chat_sessions": _ordered_sessions()[:10],
        "object_watch": _safe_call(get_watch_status, {"active": False, "target": "", "summary": "No object watch is active."}),
        "object_detection": {
            "model_name": _safe_call(get_object_detection_model_name, "yolov8n.pt"),
            "small_object_mode": _safe_call(is_small_object_mode_enabled, False),
            "presets": _safe_call(get_object_detection_presets, []),
        },
        "object_history": _safe_call(get_detection_history, []),
        "object_watch_history": _safe_call(get_watch_event_history, []),
    }


@app.get("/api/health")
def api_health():
    return {"ok": True, "service": "grandpa-assistant-api"}


@app.get("/api/ui-state")
def api_ui_state():
    return {"ok": True, "state": _build_ui_state()}


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
def api_command(request: CommandRequest):
    command = _compact_text(request.command)
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
            "state": _build_ui_state(),
        }
    try:
        messages = _capture_command_reply(command)
        return {"ok": True, "command": command, "messages": messages, "state": _build_ui_state()}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Assistant error: {error}") from error


@app.get("/chat/settings")
def get_chat_settings():
    return {"ok": True, "settings": {**_chat_settings, "llm_status": get_llm_status()}}


@app.post("/chat/settings")
def update_chat_settings(request: ChatSettingsRequest):
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
    return {"ok": True, "settings": {**_chat_settings, "llm_status": get_llm_status()}}


@app.get("/chat/sessions")
def get_sessions():
    return {"ok": True, "sessions": _ordered_sessions()}


@app.post("/chat/sessions")
def create_session(request: SessionRequest):
    session = _ensure_session(title=_compact_text(request.title) or "New chat", create_new=True)
    _save_chat_state()
    return {"ok": True, "session": session, "sessions": _ordered_sessions()}


@app.post("/chat/sessions/rename")
def rename_session(request: SessionUpdateRequest):
    session = _chat_sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    session["title"] = _compact_text(request.title) or session["title"]
    session["updated_at"] = _utc_now()
    _save_chat_state()
    return {"ok": True, "session": session, "sessions": _ordered_sessions()}


@app.post("/chat/sessions/delete")
def delete_session(request: RegenerateRequest):
    deleted = _delete_session(request.session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    current = _ordered_sessions()[0]
    return {"ok": True, "sessions": _ordered_sessions(), "current_session_id": current["id"]}


@app.get("/chat/history")
def chat_history(session_id: str | None = None):
    session = _resolve_session(session_id=session_id)
    return {"ok": True, "session": session, "messages": session["messages"], "sessions": _ordered_sessions()}


@app.post("/chat/upload")
async def chat_upload(
    file: UploadFile = File(...),
    session_id: str | None = Form(default=None),
):
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
def chat_remove_upload(request: RemoveDocumentRequest):
    session = _resolve_session(session_id=request.session_id)
    filename = _compact_text(request.filename)
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
def export_chat(session_id: str):
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
def chat_reset(session_id: str | None = None):
    session = _resolve_session(session_id=session_id)
    session["messages"] = []
    session["updated_at"] = _utc_now()
    _save_chat_state()
    return {"ok": True}


@app.post("/chat/cancel")
def chat_cancel(request: CancelRequest):
    _cancelled_streams.add(request.session_id)
    return {"ok": True}


@app.post("/chat")
def chat_reply(request: ChatRequest):
    message = _compact_text(request.message)
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")

    session = _resolve_session(session_id=request.session_id)
    _update_session_title(session, message)
    user_item = _history_item("user", message)
    session["messages"].append(user_item)
    session["messages"] = _trim_messages(session["messages"])
    session["updated_at"] = _utc_now()
    _save_chat_state()
    prompt_message = _build_chat_input(session, message)

    try:
        reply, tool_command, tool_messages, confirmation_id = _run_tool_aware_reply(session["messages"][:-1], prompt_message)
        assistant_item = _history_item("assistant", reply)
        if tool_command:
            assistant_item["tool"] = {"command": tool_command, "messages": tool_messages}
        if confirmation_id:
            assistant_item["confirmation_id"] = confirmation_id
        session["messages"].append(assistant_item)
        session["messages"] = _trim_messages(session["messages"])
        session["updated_at"] = _utc_now()
        _save_chat_state()
        return {"ok": True, "reply": reply, "message": assistant_item, "messages": session["messages"], "session": session}
    except Exception as error:
        raise HTTPException(status_code=500, detail=_friendly_ai_error(error)) from error


@app.post("/chat/regenerate")
def regenerate_reply(request: RegenerateRequest):
    session = _chat_sessions.get(request.session_id)
    if not session or not session["messages"]:
        raise HTTPException(status_code=404, detail="Session not found.")

    messages = session["messages"]
    while messages and messages[-1]["role"] == "assistant":
        messages.pop()
    if not messages or messages[-1]["role"] != "user":
        raise HTTPException(status_code=400, detail="No user message available to regenerate.")

    last_user_message = messages[-1]["content"]
    prompt_message = _build_chat_input(session, last_user_message)
    try:
        reply, tool_command, tool_messages, confirmation_id = _run_tool_aware_reply(messages[:-1], prompt_message)
        assistant_item = _history_item("assistant", reply)
        if tool_command:
            assistant_item["tool"] = {"command": tool_command, "messages": tool_messages}
        if confirmation_id:
            assistant_item["confirmation_id"] = confirmation_id
        messages.append(assistant_item)
        session["messages"] = _trim_messages(messages)
        session["updated_at"] = _utc_now()
        _save_chat_state()
        return {"ok": True, "message": assistant_item, "session": session}
    except Exception as error:
        raise HTTPException(status_code=500, detail=_friendly_ai_error(error)) from error


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    message = _compact_text(request.message)
    if not message:
        raise HTTPException(status_code=400, detail="Message is required.")

    session = _resolve_session(session_id=request.session_id)
    _update_session_title(session, message)
    session_id = session["id"]
    if session_id in _cancelled_streams:
        _cancelled_streams.discard(session_id)

    user_item = _history_item("user", message)
    session["messages"].append(user_item)
    session["messages"] = _trim_messages(session["messages"])
    session["updated_at"] = _utc_now()
    _save_chat_state()
    history_snapshot = list(session["messages"][:-1])
    prompt_message = _build_chat_input(session, message)

    async def event_stream():
        full_reply = ""
        confirmation_id = None
        try:
            for chunk in stream_chat_reply(
                history_snapshot,
                prompt_message,
                model=_chat_settings["model"],
                system_prompt=_effective_system_prompt(),
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
                        model=_chat_settings["model"],
                        system_prompt=_chat_settings["system_prompt"],
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
            yield f"data: {json.dumps({'type': 'done', 'message': assistant_item, 'session': {'id': session['id'], 'title': session['title']}})}\n\n"
        except Exception as error:
            yield f"data: {json.dumps({'type': 'error', 'error': _friendly_ai_error(error)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def start_web_api(installed_apps, host="127.0.0.1", port=8765):
    global _server, _server_thread, _installed_apps
    _installed_apps = installed_apps or {}
    _load_chat_state()
    _ensure_session()
    if _server_thread and _server_thread.is_alive():
        return

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    _server = uvicorn.Server(config)
    _server_thread = threading.Thread(target=_server.run, daemon=True)
    _server_thread.start()
