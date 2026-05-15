from core.llm.base import LLMRequest
from core.llm.providers.fallback_provider import FallbackLLMProvider
from .base import ProviderResult


class FallbackProvider:
    name = "fallback"

    def __init__(self, model: str = "rules"):
        self.model = model or "rules"

    def generate(self, prompt: str) -> ProviderResult:
        result = FallbackLLMProvider(self.model).generate(LLMRequest(prompt=prompt, model=self.model))
        return ProviderResult(result.ok, result.text, result.provider, result.model, result.error)
