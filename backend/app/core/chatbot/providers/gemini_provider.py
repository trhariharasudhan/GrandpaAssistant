from core.llm.base import LLMRequest
from core.llm.providers.gemini_provider import GeminiLLMProvider
from .base import ProviderResult


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, base_url: str, timeout_seconds: float):
        self.api_key = (api_key or "").strip()
        self.model = model or "gemini-1.5-flash"
        self.base_url = (base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        self.timeout_seconds = float(timeout_seconds or 30)

    def generate(self, prompt: str) -> ProviderResult:
        provider = GeminiLLMProvider(self.api_key, self.model, self.base_url, self.timeout_seconds)
        result = provider.generate(LLMRequest(prompt=prompt, model=self.model))
        return ProviderResult(result.ok, result.text, result.provider, result.model, result.error)
