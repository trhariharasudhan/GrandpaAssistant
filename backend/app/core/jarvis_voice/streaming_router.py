from __future__ import annotations

import time
from typing import Any, Callable, Iterable

from .conversation_state import ConversationStateManager
from .settings import JarvisVoiceSettings


def _compact_text(value: Any, limit: int = 4000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


ChatHandler = Callable[..., dict[str, Any]]


class StreamingVoiceRouter:
    def __init__(
        self,
        settings: JarvisVoiceSettings,
        state_manager: ConversationStateManager,
        *,
        chat_handler: ChatHandler | None = None,
    ) -> None:
        self.settings = settings
        self.state_manager = state_manager
        self.chat_handler = chat_handler

    def route_text(self, text: str, *, session_id: str = "jarvis-voice", source: str = "voice") -> dict[str, Any]:
        message = _compact_text(text)
        if not message:
            return {"ok": False, "reply": "I did not hear a command.", "intent": "", "tool": "", "source": source}
        handler = self.chat_handler
        if handler is None:
            from core import chat_service

            handler = chat_service.build_chat_reply
        result = handler(message, session_id=session_id, channel="voice")
        if not isinstance(result, dict):
            result = {"ok": True, "reply": _compact_text(result)}
        reply = _compact_text(result.get("reply"), self.settings.max_reply_chars_for_voice)
        debug = result.get("debug") if isinstance(result.get("debug"), dict) else {}
        tool = _compact_text(debug.get("selected_tool") or result.get("tool") or "")
        self.state_manager.update_turn(
            session_id,
            transcript=message,
            reply=reply,
            intent=_compact_text(result.get("intent")),
            tool=tool,
            language=self.settings.language,
            emotion_hint=self.detect_emotion_hint(message, reply),
        )
        return {
            "ok": bool(result.get("ok", True)),
            "reply": reply,
            "intent": _compact_text(result.get("intent")),
            "tool": tool,
            "source": source,
            "chat": {
                "route": _compact_text(result.get("route")),
                "provider": _compact_text(result.get("provider")),
                "requires_confirmation": bool(result.get("requires_confirmation", False)),
                "missing_details": list(result.get("missing_details") or []),
            },
        }

    def stream_text(self, text: str, *, session_id: str = "jarvis-voice", source: str = "voice") -> Iterable[dict[str, Any]]:
        start = time.perf_counter()
        yield {"type": "start", "source": source, "session_id": session_id}
        result = self.route_text(text, session_id=session_id, source=source)
        reply = _compact_text(result.get("reply"))
        if self.settings.streaming_enabled and reply:
            for token in reply.split():
                yield {"type": "token", "text": token + " "}
        yield {
            "type": "done",
            "ok": bool(result.get("ok")),
            "reply": reply,
            "intent": result.get("intent", ""),
            "tool": result.get("tool", ""),
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        }

    def detect_emotion_hint(self, message: str, reply: str = "") -> str:
        if not self.settings.emotion_aware:
            return "neutral"
        text = f"{message} {reply}".lower()
        if any(token in text for token in ("thanks", "great", "happy", "super", "awesome")):
            return "warm"
        if any(token in text for token in ("urgent", "angry", "annoyed", "late", "emergency")):
            return "calm"
        if any(token in text for token in ("sad", "tired", "worried", "stress")):
            return "gentle"
        return "neutral"
