import os

import requests


CLAUDE_API_KEY_ENV = "CLAUDE_API_KEY"
CLAUDE_MODEL_ENV = "CLAUDE_MODEL"
CLAUDE_API_URL_ENV = "CLAUDE_API_URL"
CLAUDE_MAX_TOKENS_ENV = "CLAUDE_MAX_TOKENS"
CLAUDE_TIMEOUT_ENV = "CLAUDE_REQUEST_TIMEOUT_SECONDS"

DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-latest"
DEFAULT_CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_CLAUDE_MAX_TOKENS = 800
DEFAULT_CLAUDE_TIMEOUT_SECONDS = 45.0


class ClaudeClientError(RuntimeError):
    """Raised when the Claude client cannot fulfill a request."""


def is_claude_configured() -> bool:
    return bool(os.getenv(CLAUDE_API_KEY_ENV, "").strip())


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, default)).strip())
    except Exception:
        return int(default)


def _env_float(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name, default)).strip())
    except Exception:
        return float(default)


def generate_claude_reply(user_input: str) -> dict[str, str]:
    prompt = str(user_input or "").strip()
    if not prompt:
        raise ClaudeClientError("Prompt is required.")

    api_key = os.getenv(CLAUDE_API_KEY_ENV, "").strip()
    if not api_key:
        raise ClaudeClientError("CLAUDE_API_KEY is missing.")

    payload = {
        "model": str(os.getenv(CLAUDE_MODEL_ENV, DEFAULT_CLAUDE_MODEL)).strip() or DEFAULT_CLAUDE_MODEL,
        "max_tokens": _env_int(CLAUDE_MAX_TOKENS_ENV, DEFAULT_CLAUDE_MAX_TOKENS),
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    endpoint = str(os.getenv(CLAUDE_API_URL_ENV, DEFAULT_CLAUDE_API_URL)).strip() or DEFAULT_CLAUDE_API_URL

    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=_env_float(CLAUDE_TIMEOUT_ENV, DEFAULT_CLAUDE_TIMEOUT_SECONDS),
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.ConnectionError as error:
        raise ClaudeClientError("Claude is unreachable right now.") from error
    except requests.RequestException as error:
        detail = ""
        try:
            detail = error.response.text.strip()
        except Exception:
            detail = ""
        raise ClaudeClientError(f"Claude request failed: {detail or error}") from error
    except ValueError as error:
        raise ClaudeClientError("Claude returned an unreadable response.") from error

    content_blocks = data.get("content") or []
    text_parts = []
    for item in content_blocks:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "text":
            continue
        text = str(item.get("text") or "").strip()
        if text:
            text_parts.append(text)

    reply = "\n".join(text_parts).strip()
    if not reply:
        raise ClaudeClientError("Claude returned an empty response.")

    return {
        "response": reply,
        "model": "claude",
        "route": "online",
    }
