from __future__ import annotations

import requests

from .base import ProviderResult


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str, timeout_seconds: float):
        self.api_key = (api_key or "").strip()
        self.model = model or "gpt-4.1-mini"
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.timeout_seconds = float(timeout_seconds or 30)

    def generate(self, prompt: str) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(False, "", self.name, self.model, "OPENAI_API_KEY is missing.")
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            return ProviderResult(bool(text), text, self.name, self.model, "" if text else "OpenAI returned an empty response.")
        except Exception as error:
            return ProviderResult(False, "", self.name, self.model, str(error))
