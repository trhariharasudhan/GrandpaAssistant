from __future__ import annotations

import datetime
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

try:
    from app.integrations.n8n_client import send_n8n_message
except ImportError:  # pragma: no cover - import shape differs in direct scripts
    from backend.app.integrations.n8n_client import send_n8n_message

from llm_client import generate_chat_reply
from local_knowledge import answer_if_confident


FALLBACK_REPLY = "I couldn't get an answer right now. Please try again."
MAX_SESSION_MESSAGES = 20
logger = logging.getLogger(__name__)


Provider = Callable[..., str]
CommandExecutor = Callable[[str], list[str]]


@dataclass
class ChatSession:
    session_id: str
    messages: list[dict[str, str]] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: _utc_now())


_sessions: dict[str, ChatSession] = {}


def _utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_session_id(session_id: str | None) -> str:
    cleaned = compact_text(session_id)
    return cleaned or "default"


def get_chat_session(session_id: str | None = None) -> ChatSession:
    normalized = _normalize_session_id(session_id)
    session = _sessions.get(normalized)
    if session is None:
        session = ChatSession(session_id=normalized)
        _sessions[normalized] = session
    return session


def reset_chat_session(session_id: str | None = None) -> None:
    _sessions.pop(_normalize_session_id(session_id), None)


def clear_all_chat_sessions_for_tests() -> None:
    _sessions.clear()


def _trim_session(session: ChatSession) -> None:
    session.messages = session.messages[-MAX_SESSION_MESSAGES:]
    session.updated_at = _utc_now()


def _append_turn(session: ChatSession, user_message: str, assistant_reply: str) -> None:
    session.messages.append({"role": "user", "content": user_message})
    session.messages.append({"role": "assistant", "content": assistant_reply})
    _trim_session(session)


def _is_reset_command(message: str) -> bool:
    return compact_text(message).lower() in {"reset chat", "clear conversation", "clear chat"}


def detect_explicit_chat_route(message: str) -> dict[str, Any]:
    normalized = compact_text(message).lower()
    if not normalized:
        return {"route": "empty"}
    if _is_reset_command(normalized):
        return {"route": "reset"}
    automation_patterns = [
        r"^(?:run automation|trigger n8n|send to n8n|automate|grandpa automate)\b\s*(.*)$",
    ]
    for pattern in automation_patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            task = compact_text(re.sub(pattern, r"\1", message, flags=re.IGNORECASE))
            return {"route": "automation", "task": task or message}
    ui_patterns = [
        r"^(?:what is on my screen|analyze my screen|explain this error)\b",
        r"^find on screen\s+.+",
        r"^plan screen action\s+.+",
        r"^where is .+ button\b",
        r"^(?:click|type into|press)\s+.+",
    ]
    if any(re.match(pattern, normalized, flags=re.IGNORECASE) for pattern in ui_patterns):
        return {"route": "ui", "task": message}
    return {"route": "chat"}


def _build_system_prompt() -> str:
    today = datetime.datetime.now().strftime("%B %d, %Y")
    return (
        "You are GrandpaAssistant in a normal chat conversation. "
        "Answer the user's current message directly and briefly. "
        "Use prior turns only for clear follow-up questions. "
        "Do not reuse or replay an unrelated earlier answer. "
        f"Current date: {today}."
    )


def _sanitize_reply(reply: str, user_message: str) -> str:
    cleaned = compact_text(reply)
    normalized_user = compact_text(user_message).lower().strip(" ?!.")
    normalized_reply = cleaned.lower().strip(" ?!.")
    echo_forms = {
        normalized_user,
        f"user question: {normalized_user}",
        f"user: {normalized_user}",
        f"question: {normalized_user}",
    }
    if not cleaned or normalized_reply in echo_forms:
        return FALLBACK_REPLY
    return cleaned


def _tokens(text: str) -> set[str]:
    return {part for part in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(part) > 2}


def _looks_like_stale_replay(user_message: str, reply: str, history: list[dict[str, str]]) -> bool:
    cleaned_reply = compact_text(reply).lower()
    if not cleaned_reply:
        return True
    previous_assistant = [
        compact_text(item.get("content", "")).lower()
        for item in history
        if item.get("role") == "assistant"
    ]
    if cleaned_reply in previous_assistant:
        previous_user = next(
            (
                compact_text(item.get("content", ""))
                for item in reversed(history)
                if item.get("role") == "user"
            ),
            "",
        )
        if previous_user and previous_user.lower() != compact_text(user_message).lower():
            return True
    current_tokens = _tokens(user_message)
    reply_tokens = _tokens(reply)
    if current_tokens and reply_tokens and not current_tokens.intersection(reply_tokens):
        stale_topic_markers = {"python", "javascript", "programming", "code"}
        if reply_tokens.intersection(stale_topic_markers):
            return True
    return False


def _call_provider(provider: Provider, history: list[dict[str, str]], message: str) -> str:
    try:
        return provider(history, message, system_prompt=_build_system_prompt())
    except TypeError:
        return provider(history, message)


def build_chat_reply(
    message: str,
    *,
    session_id: str | None = None,
    provider: Provider | None = None,
    command_executor: CommandExecutor | None = None,
    channel: str = "text",
) -> dict[str, Any]:
    user_message = compact_text(message)
    normalized_session_id = _normalize_session_id(session_id)
    route_info = detect_explicit_chat_route(user_message)
    route = route_info["route"]
    provider_name = "none"
    context_turns = 0

    if route == "reset":
        reset_chat_session(normalized_session_id)
        reply = "Conversation cleared."
        logger.info("chat_service route=%s session_id=%s context_turns=0 provider=%s", route, normalized_session_id, provider_name)
        return {"ok": True, "reply": reply, "route": route, "session_id": normalized_session_id, "provider": provider_name}

    if route == "automation":
        task = route_info.get("task") or user_message
        result = send_n8n_message(task, channel=channel, raw_command=user_message)
        reply = "Automation sent to n8n successfully." if result.get("ok") else "n8n automation is not available right now."
        logger.info("chat_service route=%s session_id=%s context_turns=0 provider=n8n", route, normalized_session_id)
        return {
            "ok": bool(result.get("ok")),
            "reply": reply,
            "route": route,
            "session_id": normalized_session_id,
            "provider": "n8n",
            "automation": result,
        }

    if route == "ui":
        if command_executor is None:
            reply = "I can analyze the screen from the desktop runtime, but this chat path cannot access UI tools right now."
            return {"ok": False, "reply": reply, "route": route, "session_id": normalized_session_id, "provider": provider_name}
        messages = command_executor(user_message)
        reply = compact_text(" ".join(messages)) or "I could not analyze the screen right now."
        logger.info("chat_service route=%s session_id=%s context_turns=0 provider=command_executor", route, normalized_session_id)
        return {
            "ok": True,
            "reply": reply,
            "route": route,
            "session_id": normalized_session_id,
            "provider": "command-executor",
            "messages": messages,
        }

    session = get_chat_session(normalized_session_id)
    history = list(session.messages[-MAX_SESSION_MESSAGES:])
    context_turns = len(history) // 2

    local_answer = answer_if_confident(user_message)
    if local_answer:
        provider_name = "local-knowledge"
        reply = _sanitize_reply(local_answer, user_message)
    else:
        active_provider = provider or generate_chat_reply
        provider_name = getattr(active_provider, "__name__", "chat-provider")
        try:
            raw_reply = _call_provider(active_provider, history, user_message)
            reply = _sanitize_reply(raw_reply, user_message)
            if reply == FALLBACK_REPLY or _looks_like_stale_replay(user_message, reply, history):
                reply = FALLBACK_REPLY
                provider_name = f"{provider_name}-sanitized"
        except Exception as error:
            logger.warning("chat_service provider failed for session_id=%s: %s", normalized_session_id, error)
            reply = FALLBACK_REPLY
            provider_name = f"{provider_name}-failed"

    _append_turn(session, user_message, reply)
    logger.info(
        "chat_service route=%s session_id=%s context_turns=%s provider=%s",
        route,
        normalized_session_id,
        context_turns,
        provider_name,
    )
    return {
        "ok": reply != FALLBACK_REPLY,
        "reply": reply,
        "route": route,
        "session_id": normalized_session_id,
        "provider": provider_name,
        "context_turns": context_turns,
        "messages": list(session.messages),
    }
