from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


def _compact_text(value: Any, limit: int = 500) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


@dataclass
class VoiceConversationState:
    session_id: str
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_transcript: str = ""
    last_reply: str = ""
    last_intent: str = ""
    last_tool: str = ""
    language: str = "auto"
    emotion_hint: str = "neutral"
    muted: bool = False
    interrupted: bool = False
    turn_count: int = 0


class ConversationStateManager:
    def __init__(self) -> None:
        self._states: dict[str, VoiceConversationState] = {}

    def get(self, session_id: str | None = None) -> VoiceConversationState:
        key = _compact_text(session_id, 120) or "voice-" + uuid.uuid4().hex[:8]
        if key not in self._states:
            self._states[key] = VoiceConversationState(session_id=key)
        return self._states[key]

    def update_turn(
        self,
        session_id: str,
        *,
        transcript: str,
        reply: str,
        intent: str = "",
        tool: str = "",
        language: str = "auto",
        emotion_hint: str = "neutral",
    ) -> VoiceConversationState:
        state = self.get(session_id)
        state.updated_at = time.time()
        state.last_transcript = _compact_text(transcript)
        state.last_reply = _compact_text(reply)
        state.last_intent = _compact_text(intent, 120)
        state.last_tool = _compact_text(tool, 120)
        state.language = _compact_text(language, 40) or state.language
        state.emotion_hint = _compact_text(emotion_hint, 40) or "neutral"
        state.turn_count += 1
        state.interrupted = False
        return state

    def mark_interrupted(self, session_id: str) -> None:
        state = self.get(session_id)
        state.interrupted = True
        state.updated_at = time.time()

    def set_muted(self, session_id: str, muted: bool) -> None:
        state = self.get(session_id)
        state.muted = bool(muted)
        state.updated_at = time.time()

    def snapshot(self, session_id: str | None = None) -> dict[str, Any]:
        state = self.get(session_id)
        return {
            "session_id": state.session_id,
            "turn_count": state.turn_count,
            "last_intent": state.last_intent,
            "last_tool": state.last_tool,
            "language": state.language,
            "emotion_hint": state.emotion_hint,
            "muted": state.muted,
            "interrupted": state.interrupted,
            "updated_at": state.updated_at,
            "has_last_transcript": bool(state.last_transcript),
            "has_last_reply": bool(state.last_reply),
        }
