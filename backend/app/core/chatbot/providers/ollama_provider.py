from core.llm.base import LLMRequest
from core.llm.providers.ollama_provider import OllamaLLMProvider
from .base import ProviderResult


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str, base_url: str, timeout_seconds: float):
        self.model = model or "llama3:8b"
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.timeout_seconds = float(timeout_seconds or 120)

    def generate(self, prompt: str) -> ProviderResult:
        provider = OllamaLLMProvider(self.model, self.base_url, self.timeout_seconds)
        result = provider.generate(LLMRequest(prompt=prompt, model=self.model))
        return ProviderResult(result.ok, result.text, result.provider, result.model, result.error)
