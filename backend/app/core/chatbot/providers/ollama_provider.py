from __future__ import annotations

import requests

from .base import ProviderResult


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str, base_url: str, timeout_seconds: float):
        self.model = model or "llama3:8b"
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.timeout_seconds = float(timeout_seconds or 120)

    def generate(self, prompt: str) -> ProviderResult:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            text = (response.json().get("response") or "").strip()
            return ProviderResult(bool(text), text, self.name, self.model, "" if text else "Ollama returned an empty response.")
        except Exception as error:
            return ProviderResult(False, "", self.name, self.model, str(error))
