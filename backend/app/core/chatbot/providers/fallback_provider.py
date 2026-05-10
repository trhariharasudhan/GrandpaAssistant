from __future__ import annotations

import re

from .base import ProviderResult


class FallbackProvider:
    name = "fallback"

    def __init__(self, model: str = "rules"):
        self.model = model or "rules"

    def generate(self, prompt: str) -> ProviderResult:
        lowered = prompt.lower()
        if "latest" in lowered or "current event" in lowered or "2026" in lowered:
            text = "I may need live search for latest info. I can still help if you provide the source or details."
        else:
            text = (
                "I couldn't reach an AI model right now. "
                "Try the fallback local intents, or switch to Ollama/OpenAI/Gemini when ready."
            )
        return ProviderResult(ok=True, text=text, provider=self.name, model=self.model)
