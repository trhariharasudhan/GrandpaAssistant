from __future__ import annotations

import datetime
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

try:
    from app.integrations.n8n_client import send_n8n_message
except ImportError:  # pragma: no cover - import shape differs in direct scripts
    from backend.app.integrations.n8n_client import send_n8n_message

from llm_client import generate_chat_reply
from local_knowledge import answer_if_confident
from core.chat_context import (
    build_chat_memory_context,
    default_chat_provider,
    project_context_enabled_for_chat,
    resolve_chat_prompt_mode,
    runtime_prompts_enabled_for_chat,
)
from core.prompt_memory_context import build_safe_memory_context
from core.runtime_prompt_adapter import TRUE_VALUES, get_runtime_system_prompt_with_metadata

try:
    from core.personal_assistant import (
        clear_personal_assistant_contexts_for_tests,
        handle_personal_assistant_message,
        reset_conversation_context,
    )
except ImportError:  # pragma: no cover - compatibility with older runtime bundles
    def clear_personal_assistant_contexts_for_tests() -> None:
        return None

    def reset_conversation_context(session_id: str | None = None) -> None:
        return None

    def handle_personal_assistant_message(message: str, *, session_id: str | None = None, include_debug: bool = False) -> dict[str, Any]:
        return {"handled": False}

try:
    from project_knowledge.project_context_adapter import build_project_context_for_prompt
except ImportError:  # pragma: no cover - project knowledge package may be absent in older deployments
    build_project_context_for_prompt = None


FALLBACK_REPLY = "I couldn't get an answer right now. Please try again."
MAX_SESSION_MESSAGES = 20
PERSONAL_ASSISTANT_DEBUG_ENV = "GRANDPA_ASSISTANT_DEBUG"
logger = logging.getLogger(__name__)


Provider = Callable[..., str]
CommandExecutor = Callable[[str], list[str]]


@dataclass
class ChatSession:
    session_id: str
    messages: list[dict[str, str]] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: _utc_now())


_sessions: dict[str, ChatSession] = {}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _personal_assistant_debug_enabled() -> bool:
    return os.getenv(PERSONAL_ASSISTANT_DEBUG_ENV, "").strip().lower() in TRUE_VALUES


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
    normalized = _normalize_session_id(session_id)
    _sessions.pop(normalized, None)
    reset_conversation_context(normalized)


def clear_all_chat_sessions_for_tests() -> None:
    _sessions.clear()
    clear_personal_assistant_contexts_for_tests()


def _trim_session(session: ChatSession) -> None:
    session.messages = session.messages[-MAX_SESSION_MESSAGES:]
    session.updated_at = _utc_now()


def _append_turn(session: ChatSession, user_message: str, assistant_reply: str) -> None:
    session.messages.append({"role": "user", "content": user_message})
    session.messages.append({"role": "assistant", "content": assistant_reply})
    _trim_session(session)


def _is_reset_command(message: str) -> bool:
    return compact_text(message).lower() in {"reset chat", "clear conversation", "clear chat"}


def _is_screen_read_request(message: str) -> bool:
    normalized = compact_text(message).lower()
    return normalized in {
        "what is on my screen",
        "what's on my screen",
        "read this error",
        "analyze this page",
        "what does this popup say",
        "read screen",
    }


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


def _build_legacy_system_prompt() -> str:
    today = datetime.datetime.now().strftime("%B %d, %Y")
    return (
        "You are GrandpaAssistant in a normal chat conversation. "
        "Answer the user's current message directly and briefly. "
        "Use prior turns only for clear follow-up questions. "
        "Do not reuse or replay an unrelated earlier answer. "
        f"Current date: {today}."
    )


def resolve_chat_system_prompt(legacy_prompt: str, user_message: str | None = None, memory_context=None) -> str:
    prompt, _metadata = resolve_chat_system_prompt_with_metadata(legacy_prompt, user_message=user_message, memory_context=memory_context)
    return prompt


def resolve_chat_system_prompt_with_metadata(legacy_prompt: str, user_message: str | None = None, memory_context=None) -> tuple[str, dict]:
    try:
        mode = resolve_chat_prompt_mode(user_message)
    except Exception as error:  # pragma: no cover - defensive fallback
        logger.warning("Prompt mode resolution failed: %s", error)
        mode = "default"
    if mode not in {"default", "coding", "planning"}:
        mode = "default"
    safe_memory_context = build_safe_memory_context(memory_context)
    project_context_text = ""
    project_context_included = False
    project_context_result_count = 0
    if runtime_prompts_enabled_for_chat() and project_context_enabled_for_chat(user_message) and build_project_context_for_prompt is not None:
        try:
            project_context = build_project_context_for_prompt(project_root=_project_root(), user_message=user_message or "", limit=5)
            if project_context.get("enabled") and not project_context.get("error"):
                project_context_text = str(project_context.get("context_text") or "")
                summary = project_context.get("summary") if isinstance(project_context.get("summary"), dict) else {}
                project_context_result_count = int(summary.get("result_count") or 0)
                project_context_included = bool(project_context_text and project_context_result_count)
        except Exception as error:  # pragma: no cover - defensive integration boundary
            logger.warning("Project context build failed: %s", error)
    return get_runtime_system_prompt_with_metadata(
        mode=mode,
        fallback_prompt=legacy_prompt,
        memory_context=safe_memory_context or None,
        extra_context=project_context_text or None,
        use_runtime_prompts=runtime_prompts_enabled_for_chat(),
        project_context_included=project_context_included,
        project_context_result_count=project_context_result_count,
    )


def _build_system_prompt(user_message: str | None = None, memory_context=None) -> str:
    return resolve_chat_system_prompt(_build_legacy_system_prompt(), user_message=user_message, memory_context=memory_context)


def _build_system_prompt_with_metadata(user_message: str | None = None, memory_context=None) -> tuple[str, dict]:
    return resolve_chat_system_prompt_with_metadata(_build_legacy_system_prompt(), user_message=user_message, memory_context=memory_context)


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


def _call_provider(
    provider: Provider,
    history: list[dict[str, str]],
    message: str,
    *,
    memory_context: str | None = None,
) -> str:
    system_prompt = _build_system_prompt(message, memory_context=memory_context or None)
    try:
        return provider(history, message, system_prompt=system_prompt)
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
            if _is_screen_read_request(user_message):
                session = get_chat_session(normalized_session_id)
                history = list(session.messages[-MAX_SESSION_MESSAGES:])
                context_turns = len(history) // 2
                debug_enabled = _personal_assistant_debug_enabled()
                assistant_action = handle_personal_assistant_message(user_message, session_id=normalized_session_id, include_debug=debug_enabled)
                if assistant_action.get("handled"):
                    reply = _sanitize_reply(assistant_action.get("reply", ""), user_message)
                    _append_turn(session, user_message, reply)
                    payload = {
                        "ok": bool(assistant_action.get("ok", True)),
                        "reply": reply,
                        "route": assistant_action.get("route", "personal-assistant"),
                        "session_id": normalized_session_id,
                        "provider": "personal-assistant",
                        "context_turns": context_turns,
                        "intent": assistant_action.get("intent", ""),
                        "executed": bool(assistant_action.get("executed", False)),
                        "requires_confirmation": bool(assistant_action.get("requires_confirmation", False)),
                        "missing_details": assistant_action.get("missing_details", []),
                        "missing_adapter": assistant_action.get("missing_adapter", ""),
                        "messages": list(session.messages),
                    }
                    if debug_enabled and isinstance(assistant_action.get("debug"), dict):
                        payload["debug"] = assistant_action["debug"]
                    return payload
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

    debug_enabled = _personal_assistant_debug_enabled()
    assistant_action = handle_personal_assistant_message(user_message, session_id=normalized_session_id, include_debug=debug_enabled)
    if assistant_action.get("handled"):
        provider_name = "personal-assistant"
        reply = _sanitize_reply(assistant_action.get("reply", ""), user_message)
        _append_turn(session, user_message, reply)
        logger.info(
            "chat_service route=%s session_id=%s context_turns=%s provider=%s intent=%s",
            "personal-assistant",
            normalized_session_id,
            context_turns,
            provider_name,
            assistant_action.get("intent", ""),
        )
        payload = {
            "ok": bool(assistant_action.get("ok", True)),
            "reply": reply,
            "route": assistant_action.get("route", "personal-assistant"),
            "session_id": normalized_session_id,
            "provider": provider_name,
            "context_turns": context_turns,
            "intent": assistant_action.get("intent", ""),
            "executed": bool(assistant_action.get("executed", False)),
            "requires_confirmation": bool(assistant_action.get("requires_confirmation", False)),
            "missing_details": assistant_action.get("missing_details", []),
            "missing_adapter": assistant_action.get("missing_adapter", ""),
            "messages": list(session.messages),
        }
        if debug_enabled and isinstance(assistant_action.get("debug"), dict):
            payload["debug"] = assistant_action["debug"]
        return payload

    memory_context = ""
    local_answer = answer_if_confident(user_message)
    if local_answer:
        provider_name = "local-knowledge"
        reply = _sanitize_reply(local_answer, user_message)
    else:
        memory_context = build_chat_memory_context(user_message)
        active_provider = provider or default_chat_provider
        provider_name = getattr(active_provider, "__name__", "chat-provider")
        try:
            raw_reply = _call_provider(active_provider, history, user_message, memory_context=memory_context)
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
    payload = {
        "ok": reply != FALLBACK_REPLY,
        "reply": reply,
        "route": route,
        "session_id": normalized_session_id,
        "provider": provider_name,
        "context_turns": context_turns,
        "messages": list(session.messages),
    }
    if debug_enabled:
        from core.chat_context import chat_enhancement_status

        payload["chat_enhancements"] = chat_enhancement_status()
        if memory_context:
            payload["memory_context_included"] = True
    return payload
