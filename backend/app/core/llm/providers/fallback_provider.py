from __future__ import annotations

from collections.abc import Iterable

from ..base import LLMRequest, LLMResponse


class FallbackLLMProvider:
    name = "fallback"

    def __init__(self, model: str = "rules") -> None:
        self.model = model or "rules"

    def generate(self, request: LLMRequest) -> LLMResponse:
        lowered = request.prompt.lower()
        if "latest" in lowered or "current event" in lowered or "2026" in lowered:
            text = "I may need live search for latest info. I can still help if you provide the source or details."
        else:
            text = (
                "I couldn't reach an AI model right now. "
                "Try the fallback local intents, or switch to Ollama/OpenAI/Gemini when ready."
            )
        return LLMResponse(True, text, self.name, self.model)

    def stream_generate(self, request: LLMRequest) -> Iterable[str]:
        yield self.generate(request).text

    def health_check(self) -> dict:
        return {"ok": True, "provider": self.name, "model": self.model, "fallback": True}

    def model_info(self) -> dict:
        return {"provider": self.name, "model": self.model, "streaming": True, "memory": "prompt-only"}
