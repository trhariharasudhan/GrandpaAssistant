from __future__ import annotations

import json
import os
from collections.abc import Iterable

import requests

from ..base import LLMRequest, LLMResponse


DEFAULT_OLLAMA_MODEL = "llama3:8b"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_REQUEST_TIMEOUT_SECONDS = 120.0


def _env_float(name: str, default: float) -> float:
    try:
        return max(0.1, float(str(os.getenv(name, default)).strip()))
    except Exception:
        return default


class OllamaLLMProvider:
    name = "ollama"

    def __init__(self, model: str | None = None, base_url: str | None = None, timeout_seconds: float | None = None) -> None:
        self.model = model or DEFAULT_OLLAMA_MODEL
        self.base_url = (base_url or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        self.timeout_seconds = float(timeout_seconds or DEFAULT_OLLAMA_REQUEST_TIMEOUT_SECONDS)

    @classmethod
    def from_environment(cls) -> "OllamaLLMProvider":
        return cls(
            model=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
            base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
            timeout_seconds=_env_float("OLLAMA_REQUEST_TIMEOUT_SECONDS", DEFAULT_OLLAMA_REQUEST_TIMEOUT_SECONDS),
        )

    def _endpoint(self) -> str:
        return f"{self.base_url}/api/generate"

    def _tags_endpoint(self) -> str:
        return f"{self.base_url}/api/tags"

    def _prompt(self, request: LLMRequest) -> str:
        if request.metadata.get("raw_prompt"):
            return request.prompt
        lines = [request.system_prompt or ""]
        for item in request.history[-20:]:
            role = item.get("role")
            content = str(item.get("content", "")).strip()
            if role == "user" and content:
                lines.append(f"User: {content}")
            elif role == "assistant" and content:
                lines.append(f"Assistant: {content}")
        lines.append(f"User: {request.prompt}")
        lines.append("Assistant:")
        return "\n".join(line for line in lines if line)

    def generate(self, request: LLMRequest) -> LLMResponse:
        active_model = request.model or self.model
        options = {"temperature": request.temperature}
        if isinstance(request.metadata.get("options"), dict):
            options.update(request.metadata["options"])
        try:
            response = requests.post(
                self._endpoint(),
                json={
                    "model": active_model,
                    "prompt": self._prompt(request),
                    "stream": False,
                    "options": options,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            text = (response.json().get("response") or "").strip()
            return LLMResponse(bool(text), text, self.name, active_model, "" if text else "Ollama returned an empty response.")
        except Exception as error:
            return LLMResponse(False, "", self.name, active_model, str(error))

    def stream_generate(self, request: LLMRequest) -> Iterable[str]:
        active_model = request.model or self.model
        options = {"temperature": request.temperature}
        if isinstance(request.metadata.get("options"), dict):
            options.update(request.metadata["options"])
        response = requests.post(
            self._endpoint(),
            json={
                "model": active_model,
                "prompt": self._prompt(request),
                "stream": True,
                "options": options,
            },
            timeout=self.timeout_seconds,
            stream=True,
        )
        response.raise_for_status()
        try:
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content = payload.get("response")
                if content:
                    yield content
                if payload.get("done"):
                    break
        finally:
            response.close()

    def health_check(self) -> dict:
        try:
            response = requests.get(self._tags_endpoint(), timeout=min(5.0, self.timeout_seconds))
            response.raise_for_status()
            payload = response.json()
            models = []
            for item in payload.get("models", []):
                if not isinstance(item, dict):
                    continue
                name = str(item.get("model") or item.get("name") or "").strip()
                if name:
                    models.append(name)
            return {
                "ok": True,
                "provider": self.name,
                "model": self.model,
                "base_url": self.base_url,
                "installed_models": models,
            }
        except Exception as error:
            return {
                "ok": False,
                "provider": self.name,
                "model": self.model,
                "base_url": self.base_url,
                "error": str(error),
                "installed_models": [],
            }

    def model_info(self) -> dict:
        return {"provider": self.name, "model": self.model, "base_url": self.base_url, "streaming": True, "memory": "prompt"}
