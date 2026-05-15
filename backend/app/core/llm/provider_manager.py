from __future__ import annotations

import os
from collections.abc import Iterable

from .base import LLMRequest, LLMResponse
from .providers.fallback_provider import FallbackLLMProvider
from .providers.gemini_provider import GeminiLLMProvider
from .providers.ollama_provider import OllamaLLMProvider
from .providers.openai_provider import OpenAILLMProvider
from .registry import LLMProviderRegistry


LLM_PROVIDER_ENV = "LLM_PROVIDER"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"


class LLMProviderManager:
    def __init__(self, registry: LLMProviderRegistry | None = None) -> None:
        self.registry = registry or LLMProviderRegistry()

    @classmethod
    def from_environment(cls) -> "LLMProviderManager":
        registry = LLMProviderRegistry()
        registry.register("openai", lambda: OpenAILLMProvider.from_environment())
        registry.register("gemini", lambda: GeminiLLMProvider.from_environment())
        registry.register("ollama", lambda: OllamaLLMProvider.from_environment())
        registry.register("fallback", lambda: FallbackLLMProvider())
        return cls(registry)

    def resolve_provider_name(self, requested: str | None = None) -> str:
        provider = str(requested or os.getenv(LLM_PROVIDER_ENV, "auto")).strip().lower() or "auto"
        if provider in {"openai", "gemini", "ollama", "fallback"}:
            return provider
        if os.getenv(OPENAI_API_KEY_ENV, "").strip():
            return "openai"
        if os.getenv(GEMINI_API_KEY_ENV, "").strip() or os.getenv(GOOGLE_API_KEY_ENV, "").strip():
            return "gemini"
        return "ollama"

    def fallback_chain(self, requested: str | None = None) -> list[str]:
        provider = self.resolve_provider_name(requested)
        if provider == "openai":
            return ["openai", "ollama"]
        if provider == "gemini":
            return ["gemini", "ollama"]
        if provider == "ollama":
            return ["ollama"]
        if provider == "fallback":
            return ["fallback"]
        return ["ollama", "fallback"]

    def generate(self, request: LLMRequest, provider: str | None = None) -> LLMResponse:
        last_error = ""
        for provider_name in self.fallback_chain(provider):
            selected = self.registry.get(provider_name)
            result = selected.generate(request)
            if result.ok:
                return result
            last_error = result.error or last_error
        return LLMResponse(False, "", self.resolve_provider_name(provider), request.model or "", last_error or "LLM request failed.")

    def stream_generate(self, request: LLMRequest, provider: str | None = None) -> Iterable[str]:
        provider_name = self.resolve_provider_name(provider)
        selected = self.registry.get(provider_name)
        yielded = False
        try:
            for chunk in selected.stream_generate(request):
                yielded = True
                yield chunk
            return
        except Exception as first_error:
            if yielded or provider_name == "ollama":
                raise first_error
            if provider_name in {"openai", "gemini"}:
                yield from self.registry.get("ollama").stream_generate(request)
                return
            raise first_error

    def health_check(self, provider: str | None = None) -> dict:
        provider_name = self.resolve_provider_name(provider)
        return self.registry.health_check(provider_name)

    def model_info(self, provider: str | None = None) -> dict:
        provider_name = self.resolve_provider_name(provider)
        return self.registry.get(provider_name).model_info()


_DEFAULT_MANAGER: LLMProviderManager | None = None


def get_default_provider_manager() -> LLMProviderManager:
    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is None:
        _DEFAULT_MANAGER = LLMProviderManager.from_environment()
    return _DEFAULT_MANAGER
