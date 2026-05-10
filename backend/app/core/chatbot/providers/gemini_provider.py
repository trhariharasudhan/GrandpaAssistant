from __future__ import annotations

import requests

from .base import ProviderResult


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, base_url: str, timeout_seconds: float):
        self.api_key = (api_key or "").strip()
        self.model = model or "gemini-1.5-flash"
        self.base_url = (base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        self.timeout_seconds = float(timeout_seconds or 30)

    def generate(self, prompt: str) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(False, "", self.name, self.model, "GEMINI_API_KEY is missing.")
        try:
            response = requests.post(
                f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}",
                json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            )
            return ProviderResult(bool(text), text, self.name, self.model, "" if text else "Gemini returned an empty response.")
        except Exception as error:
            return ProviderResult(False, "", self.name, self.model, str(error))
