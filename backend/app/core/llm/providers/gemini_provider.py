from __future__ import annotations

import os
from collections.abc import Iterable

import requests

from ..base import LLMRequest, LLMResponse


DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_REQUEST_TIMEOUT_SECONDS = 30.0


def _env_float(name: str, default: float) -> float:
    try:
        return max(0.1, float(str(os.getenv(name, default)).strip()))
    except Exception:
        return default


class GeminiLLMProvider:
    name = "gemini"

    def __init__(self, api_key: str = "", model: str | None = None, base_url: str | None = None, timeout_seconds: float | None = None) -> None:
        self.api_key = (api_key or "").strip()
        self.model = model or DEFAULT_GEMINI_MODEL
        self.base_url = (base_url or DEFAULT_GEMINI_BASE_URL).rstrip("/")
        self.timeout_seconds = float(timeout_seconds or DEFAULT_GEMINI_REQUEST_TIMEOUT_SECONDS)

    @classmethod
    def from_environment(cls) -> "GeminiLLMProvider":
        return cls(
            api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", ""),
            model=os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
            base_url=os.getenv("GEMINI_BASE_URL", DEFAULT_GEMINI_BASE_URL),
            timeout_seconds=_env_float("GEMINI_REQUEST_TIMEOUT_SECONDS", DEFAULT_GEMINI_REQUEST_TIMEOUT_SECONDS),
        )

    def _contents(self, request: LLMRequest) -> list[dict]:
        prompt = request.prompt
        if request.system_prompt:
            prompt = f"{request.system_prompt}\n\n{prompt}"
        return [{"role": "user", "parts": [{"text": prompt}]}]

    def _endpoint(self) -> str:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is missing.")
        return f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

    def generate(self, request: LLMRequest) -> LLMResponse:
        active_model = request.model or self.model
        original_model = self.model
        self.model = active_model
        try:
            response = requests.post(
                self._endpoint(),
                json={"contents": self._contents(request)},
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
            return LLMResponse(bool(text), text, self.name, active_model, "" if text else "Gemini returned an empty response.")
        except Exception as error:
            return LLMResponse(False, "", self.name, active_model, str(error))
        finally:
            self.model = original_model

    def stream_generate(self, request: LLMRequest) -> Iterable[str]:
        result = self.generate(request)
        if not result.ok:
            raise RuntimeError(result.error or "Gemini request failed.")
        yield result.text

    def health_check(self) -> dict:
        return {"ok": bool(self.api_key), "provider": self.name, "model": self.model, "base_url": self.base_url}

    def model_info(self) -> dict:
        return {"provider": self.name, "model": self.model, "base_url": self.base_url, "streaming": False, "memory": "prompt"}
