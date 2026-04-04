import json
import os
import random
import time
from typing import Generator

import requests


LLM_PROVIDER_ENV = "LLM_PROVIDER"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
OPENAI_FALLBACK_MODEL_ENV = "OPENAI_FALLBACK_MODEL"
OPENAI_BASE_URL_ENV = "OPENAI_BASE_URL"
OPENAI_MAX_RETRIES_ENV = "OPENAI_MAX_RETRIES"
OPENAI_RETRY_BASE_DELAY_ENV = "OPENAI_RETRY_BASE_DELAY_SECONDS"
OPENAI_RETRY_MAX_DELAY_ENV = "OPENAI_RETRY_MAX_DELAY_SECONDS"
OPENAI_REQUEST_TIMEOUT_ENV = "OPENAI_REQUEST_TIMEOUT_SECONDS"
OLLAMA_MODEL_ENV = "OLLAMA_MODEL"
OLLAMA_BASE_URL_ENV = "OLLAMA_BASE_URL"
DEFAULT_LLM_PROVIDER = "auto"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MAX_RETRIES = 4
DEFAULT_OPENAI_RETRY_BASE_DELAY_SECONDS = 2.0
DEFAULT_OPENAI_RETRY_MAX_DELAY_SECONDS = 20.0
DEFAULT_OPENAI_REQUEST_TIMEOUT_SECONDS = 30.0
DEFAULT_OLLAMA_MODEL = "llama3:8b"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
RETRYABLE_HTTP_STATUS_CODES = {408, 429, 500, 502, 503, 504}

SYSTEM_PROMPT = (
    "You are Grandpa Assistant, a warm, practical AI desktop assistant. "
    "Give clear, concise, helpful replies. Prefer direct answers and useful next steps."
)


def load_env_file(env_path: str) -> None:
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as file:
            for line in file:
                entry = line.strip()
                if not entry or entry.startswith("#") or "=" not in entry:
                    continue
                key, value = entry.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        return


def _openai_headers() -> dict:
    api_key = os.getenv(OPENAI_API_KEY_ENV, "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _chat_endpoint() -> str:
    base_url = os.getenv(OPENAI_BASE_URL_ENV, DEFAULT_OPENAI_BASE_URL).rstrip("/")
    return f"{base_url}/chat/completions"


def _ollama_generate_endpoint() -> str:
    base_url = os.getenv(OLLAMA_BASE_URL_ENV, DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    return f"{base_url}/api/generate"


def _resolved_provider() -> str:
    provider = os.getenv(LLM_PROVIDER_ENV, DEFAULT_LLM_PROVIDER).strip().lower() or DEFAULT_LLM_PROVIDER
    if provider in {"openai", "ollama"}:
        return provider
    return "openai" if os.getenv(OPENAI_API_KEY_ENV, "").strip() else "ollama"


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(float(str(os.getenv(name, default)).strip())))
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return max(0.1, float(str(os.getenv(name, default)).strip()))
    except Exception:
        return default


def _parse_retry_delay_seconds(value) -> float | None:
    text = str(value or "").strip().lower()
    if not text:
        return None
    try:
        if text.endswith("ms"):
            return max(0.1, float(text[:-2].strip()) / 1000.0)
        if text.endswith("s"):
            return max(0.1, float(text[:-1].strip()))
        return max(0.1, float(text))
    except ValueError:
        return None


def _response_json(response: requests.Response | None) -> dict | None:
    if response is None:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _provider_error_object(payload: dict | None) -> dict:
    error = payload.get("error") if isinstance(payload, dict) else None
    return error if isinstance(error, dict) else {}


def _provider_error_reason(payload: dict | None) -> str:
    error = _provider_error_object(payload)
    reason = str(error.get("reason") or "").strip()
    if reason:
        return reason
    details = error.get("details")
    if isinstance(details, list):
        for item in details:
            if not isinstance(item, dict):
                continue
            reason = str(item.get("reason") or "").strip()
            if reason:
                return reason
    return ""


def _provider_error_message(response: requests.Response | None, payload: dict | None) -> str:
    error = _provider_error_object(payload)
    message = str(error.get("message") or "").strip()
    if message:
        return message
    try:
        return str(response.text or "").strip() if response is not None else ""
    except Exception:
        return ""


def _provider_error_model(payload: dict | None, model_name: str | None = None) -> str:
    error = _provider_error_object(payload)
    details = error.get("details")
    if isinstance(details, list):
        for item in details:
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata")
            if not isinstance(metadata, dict):
                continue
            extracted_model = str(metadata.get("model") or "").strip()
            if extracted_model:
                return extracted_model
    return str(model_name or "").strip()


def _provider_retry_delay_seconds(response: requests.Response | None, payload: dict | None) -> float | None:
    if response is not None:
        retry_after = _parse_retry_delay_seconds(response.headers.get("Retry-After"))
        if retry_after is not None:
            return retry_after

    error = _provider_error_object(payload)
    retry_delay = _parse_retry_delay_seconds(error.get("retryDelay"))
    if retry_delay is not None:
        return retry_delay

    details = error.get("details")
    if isinstance(details, list):
        for item in details:
            if not isinstance(item, dict):
                continue
            retry_delay = _parse_retry_delay_seconds(item.get("retryDelay"))
            if retry_delay is not None:
                return retry_delay
    return None


def _is_retryable_openai_error(
    error: requests.RequestException,
    response: requests.Response | None,
    payload: dict | None,
) -> bool:
    status_code = response.status_code if response is not None else None
    if status_code in RETRYABLE_HTTP_STATUS_CODES:
        return True
    if _provider_error_reason(payload) == "MODEL_CAPACITY_EXHAUSTED":
        return True
    return isinstance(error, (requests.Timeout, requests.ConnectionError))


def _retry_delay_seconds_for_attempt(
    attempt_index: int,
    response: requests.Response | None,
    payload: dict | None,
) -> float:
    provider_delay = _provider_retry_delay_seconds(response, payload)
    if provider_delay is not None:
        return provider_delay

    base_delay = _env_float(OPENAI_RETRY_BASE_DELAY_ENV, DEFAULT_OPENAI_RETRY_BASE_DELAY_SECONDS)
    max_delay = _env_float(OPENAI_RETRY_MAX_DELAY_ENV, DEFAULT_OPENAI_RETRY_MAX_DELAY_SECONDS)
    delay = min(max_delay, base_delay * (2 ** attempt_index))
    return delay + random.uniform(0.0, min(1.0, delay * 0.25))


def _friendly_openai_error_message(
    error: requests.RequestException,
    response: requests.Response | None,
    payload: dict | None,
    model_name: str | None = None,
) -> str:
    status_code = response.status_code if response is not None else None
    provider_message = _provider_error_message(response, payload)
    retry_delay = _provider_retry_delay_seconds(response, payload)
    retry_hint = ""
    if retry_delay is not None:
        retry_hint = f" Retry in about {max(1, round(retry_delay))} seconds."

    reason = _provider_error_reason(payload)
    active_model = _provider_error_model(payload, model_name=model_name)
    if reason == "MODEL_CAPACITY_EXHAUSTED" or "capacity" in provider_message.lower():
        model_hint = f" for model {active_model}" if active_model else ""
        return f"AI provider is temporarily busy{model_hint}.{retry_hint or ' Please try again shortly.'}"
    if status_code == 429:
        return f"AI provider rate limit reached.{retry_hint or ' Please try again shortly.'}"
    if status_code == 503:
        return f"AI provider is temporarily unavailable.{retry_hint or ' Please try again shortly.'}"
    if isinstance(error, requests.Timeout):
        return "Connection timed out while contacting the AI provider."
    if isinstance(error, requests.ConnectionError):
        return "Connection error while contacting the AI provider."
    return provider_message or str(error)


def _openai_model_candidates(model: str | None = None) -> list[str]:
    primary_model = str(model or os.getenv(OPENAI_MODEL_ENV, DEFAULT_OPENAI_MODEL)).strip() or DEFAULT_OPENAI_MODEL
    fallback_model = str(os.getenv(OPENAI_FALLBACK_MODEL_ENV, "")).strip()
    candidates = [primary_model]
    if fallback_model and fallback_model not in candidates:
        candidates.append(fallback_model)
    return candidates


def _post_openai_request(payload: dict, *, stream: bool = False) -> requests.Response:
    max_attempts = _env_int(OPENAI_MAX_RETRIES_ENV, DEFAULT_OPENAI_MAX_RETRIES)
    request_timeout = _env_float(
        OPENAI_REQUEST_TIMEOUT_ENV,
        DEFAULT_OPENAI_REQUEST_TIMEOUT_SECONDS,
    )
    requested_model = str(payload.get("model") or "").strip() or None
    last_error = None

    for attempt_index in range(max_attempts):
        response = None
        try:
            response = requests.post(
                _chat_endpoint(),
                headers=_openai_headers(),
                json=payload,
                timeout=request_timeout,
                stream=stream,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            last_error = error
            response = getattr(error, "response", None) or response
            error_payload = _response_json(response)
            if attempt_index >= max_attempts - 1 or not _is_retryable_openai_error(error, response, error_payload):
                raise RuntimeError(
                    _friendly_openai_error_message(
                        error,
                        response,
                        error_payload,
                        model_name=requested_model,
                    )
                ) from error
            if response is not None:
                response.close()
            time.sleep(_retry_delay_seconds_for_attempt(attempt_index, response, error_payload))

    if last_error is not None:
        raise RuntimeError(str(last_error)) from last_error
    raise RuntimeError("AI request failed before a response was received.")


def _build_ollama_prompt(history: list[dict], user_message: str, system_prompt: str | None = None) -> str:
    lines = [system_prompt or SYSTEM_PROMPT]
    for item in history[-20:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role == "user" and content:
            lines.append(f"User: {content}")
        elif role == "assistant" and content:
            lines.append(f"Assistant: {content}")
    lines.append(f"User: {user_message}")
    lines.append("Assistant:")
    return "\n".join(lines)


def get_llm_status() -> dict:
    api_key = os.getenv(OPENAI_API_KEY_ENV, "").strip()
    provider = _resolved_provider()
    openai_model = os.getenv(OPENAI_MODEL_ENV, DEFAULT_OPENAI_MODEL).strip() or DEFAULT_OPENAI_MODEL
    openai_fallback_model = os.getenv(OPENAI_FALLBACK_MODEL_ENV, "").strip()
    openai_base_url = os.getenv(OPENAI_BASE_URL_ENV, DEFAULT_OPENAI_BASE_URL).strip() or DEFAULT_OPENAI_BASE_URL
    ollama_model = os.getenv(OLLAMA_MODEL_ENV, DEFAULT_OLLAMA_MODEL).strip() or DEFAULT_OLLAMA_MODEL
    ollama_base_url = os.getenv(OLLAMA_BASE_URL_ENV, DEFAULT_OLLAMA_BASE_URL).strip() or DEFAULT_OLLAMA_BASE_URL
    return {
        "provider": provider,
        "model": openai_model if provider == "openai" else ollama_model,
        "base_url": openai_base_url if provider == "openai" else ollama_base_url,
        "api_key_configured": bool(api_key),
        "ready": bool(api_key) if provider == "openai" else True,
        "fallback_available": True,
        "openai_model": openai_model,
        "openai_fallback_model": openai_fallback_model,
        "ollama_model": ollama_model,
    }


def _build_messages(history: list[dict], user_message: str, system_prompt: str | None = None) -> list[dict]:
    messages = [{"role": "system", "content": system_prompt or SYSTEM_PROMPT}]
    for item in history[-20:]:
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


def _generate_openai_reply(history: list[dict], user_message: str, model: str | None = None, system_prompt: str | None = None) -> str:
    last_error = None
    for candidate_model in _openai_model_candidates(model):
        response = None
        try:
            payload = {
                "model": candidate_model,
                "messages": _build_messages(history, user_message, system_prompt=system_prompt),
                "temperature": 0.7,
            }
            response = _post_openai_request(payload, stream=False)
            data = response.json()
            return (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            ) or "I could not generate a reply right now."
        except Exception as error:
            last_error = error
        finally:
            if response is not None:
                response.close()
    if last_error is not None:
        raise last_error
    raise RuntimeError("I could not generate a reply right now.")


def _generate_ollama_reply(history: list[dict], user_message: str, model: str | None = None, system_prompt: str | None = None) -> str:
    payload = {
        "model": model or os.getenv(OLLAMA_MODEL_ENV, DEFAULT_OLLAMA_MODEL),
        "prompt": _build_ollama_prompt(history, user_message, system_prompt=system_prompt),
        "stream": False,
        "options": {
            "temperature": 0.7,
        },
    }
    response = requests.post(_ollama_generate_endpoint(), json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return (data.get("response") or "").strip() or "I could not generate a reply right now."


def generate_chat_reply(history: list[dict], user_message: str, model: str | None = None, system_prompt: str | None = None) -> str:
    provider = _resolved_provider()
    if provider == "ollama":
        return _generate_ollama_reply(history, user_message, model=None, system_prompt=system_prompt)

    try:
        return _generate_openai_reply(history, user_message, model=model, system_prompt=system_prompt)
    except Exception as openai_error:
        try:
            return _generate_ollama_reply(history, user_message, model=None, system_prompt=system_prompt)
        except Exception:
            raise openai_error


def _stream_openai_reply(
    history: list[dict],
    user_message: str,
    model: str | None = None,
    system_prompt: str | None = None,
) -> Generator[str, None, None]:
    last_error = None
    for candidate_model in _openai_model_candidates(model):
        response = None
        try:
            payload = {
                "model": candidate_model,
                "messages": _build_messages(history, user_message, system_prompt=system_prompt),
                "temperature": 0.7,
                "stream": True,
            }
            response = _post_openai_request(payload, stream=True)
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    return
                try:
                    event_payload = json.loads(data)
                except json.JSONDecodeError:
                    continue

                delta = event_payload.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content
            return
        except Exception as error:
            last_error = error
        finally:
            if response is not None:
                response.close()
    if last_error is not None:
        raise last_error
    raise RuntimeError("I could not generate a reply right now.")


def _stream_ollama_reply(
    history: list[dict],
    user_message: str,
    model: str | None = None,
    system_prompt: str | None = None,
) -> Generator[str, None, None]:
    payload = {
        "model": model or os.getenv(OLLAMA_MODEL_ENV, DEFAULT_OLLAMA_MODEL),
        "prompt": _build_ollama_prompt(history, user_message, system_prompt=system_prompt),
        "stream": True,
        "options": {
            "temperature": 0.7,
        },
    }
    response = requests.post(
        _ollama_generate_endpoint(),
        json=payload,
        timeout=120,
        stream=True,
    )
    response.raise_for_status()

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


def stream_chat_reply(
    history: list[dict],
    user_message: str,
    model: str | None = None,
    system_prompt: str | None = None,
) -> Generator[str, None, None]:
    provider = _resolved_provider()
    if provider == "ollama":
        yield from _stream_ollama_reply(history, user_message, model=None, system_prompt=system_prompt)
        return

    try:
        yielded_content = False
        for chunk in _stream_openai_reply(history, user_message, model=model, system_prompt=system_prompt):
            yielded_content = True
            yield chunk
        return
    except Exception as openai_error:
        if yielded_content:
            raise openai_error
        try:
            yield from _stream_ollama_reply(history, user_message, model=None, system_prompt=system_prompt)
        except Exception:
            raise openai_error
