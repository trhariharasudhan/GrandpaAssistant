from __future__ import annotations

import json
import os
from collections.abc import Iterable

import requests

from ..base import LLMRequest, LLMResponse


DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_REQUEST_TIMEOUT_SECONDS = 30.0


def _env_float(name: str, default: float) -> float:
    try:
        return max(0.1, float(str(os.getenv(name, default)).strip()))
    except Exception:
        return default


class OpenAILLMProvider:
    name = "openai"

    def __init__(self, api_key: str = "", model: str | None = None, base_url: str | None = None, timeout_seconds: float | None = None) -> None:
        self.api_key = (api_key or "").strip()
        self.model = model or DEFAULT_OPENAI_MODEL
        self.base_url = (base_url or DEFAULT_OPENAI_BASE_URL).rstrip("/")
        self.timeout_seconds = float(timeout_seconds or DEFAULT_OPENAI_REQUEST_TIMEOUT_SECONDS)

    @classmethod
    def from_environment(cls) -> "OpenAILLMProvider":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            base_url=os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL),
            timeout_seconds=_env_float("OPENAI_REQUEST_TIMEOUT_SECONDS", DEFAULT_OPENAI_REQUEST_TIMEOUT_SECONDS),
        )

    def _messages(self, request: LLMRequest) -> list[dict]:
        messages = [{"role": "system", "content": request.system_prompt or ""}]
        for item in request.history[-20:]:
            role = item.get("role")
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": request.prompt})
        return [message for message in messages if message.get("content")]

    def _endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _headers(self) -> dict:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is missing.")
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def generate(self, request: LLMRequest) -> LLMResponse:
        active_model = request.model or self.model
        try:
            response = requests.post(
                self._endpoint(),
                headers=self._headers(),
                json={"model": active_model, "messages": self._messages(request), "temperature": request.temperature},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
            return LLMResponse(bool(text), text, self.name, active_model, "" if text else "OpenAI returned an empty response.")
        except Exception as error:
            return LLMResponse(False, "", self.name, active_model, str(error))

    def stream_generate(self, request: LLMRequest) -> Iterable[str]:
        active_model = request.model or self.model
        response = requests.post(
            self._endpoint(),
            headers=self._headers(),
            json={"model": active_model, "messages": self._messages(request), "temperature": request.temperature, "stream": True},
            timeout=self.timeout_seconds,
            stream=True,
        )
        response.raise_for_status()
        try:
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    return
                try:
                    event_payload = json.loads(data)
                except json.JSONDecodeError:
                    continue
                content = event_payload.get("choices", [{}])[0].get("delta", {}).get("content")
                if content:
                    yield content
        finally:
            response.close()

    def health_check(self) -> dict:
        return {"ok": bool(self.api_key), "provider": self.name, "model": self.model, "base_url": self.base_url}

    def model_info(self) -> dict:
        return {"provider": self.name, "model": self.model, "base_url": self.base_url, "streaming": True, "memory": "messages"}
