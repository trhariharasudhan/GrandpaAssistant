import os
import re
from typing import Any

import requests
from cognition.hub import build_intelligence_prompt_boost
from utils.emotion import build_emotion_prompt_context
from utils.mood_memory import build_mood_memory_context


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_GENERATE_URL = f"{OLLAMA_BASE_URL}/api/generate"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"
OLLAMA_REQUEST_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_REQUEST_TIMEOUT_SECONDS", "180"))

GENERAL_MODEL = os.getenv("OLLAMA_GENERAL_MODEL", "mistral:7b")
FAST_MODEL = os.getenv("OLLAMA_FAST_MODEL", "phi3:mini")
CODING_MODEL = os.getenv("OLLAMA_CODING_MODEL", "deepseek-coder:6.7b")

VALID_MODES = {"auto", "general", "fast", "coding"}
MODEL_BY_MODE = {
    "general": GENERAL_MODEL,
    "fast": FAST_MODEL,
    "coding": CODING_MODEL,
}

CODING_HINTS = (
    "code",
    "python",
    "javascript",
    "typescript",
    "java",
    "c++",
    "c#",
    "bug",
    "debug",
    "fix",
    "refactor",
    "function",
    "class",
    "api",
    "sql",
    "regex",
    "docker",
    "kubernetes",
    "fastapi",
    "react",
    "traceback",
    "stack trace",
    "exception",
    "error:",
    "failed test",
)

FAST_HINTS = (
    "quick answer",
    "quick response",
    "briefly",
    "short answer",
    "one line",
    "fast response",
    "tl;dr",
)

CODING_PATTERN = re.compile(r"```|def\s+\w+\(|class\s+\w+|import\s+\w+|SELECT\s+.+\s+FROM", re.IGNORECASE)

SYSTEM_PROMPTS = {
    "general": (
        "You are Grandpa Assistant running locally through Ollama. "
        "Talk like a smart, friendly real person. Keep answers practical, natural, and easy to follow. "
        "In normal chat, keep replies short, usually 1 or 2 sentences unless the user asks for more. "
        "Avoid robotic phrasing, bullet lists, and overly formal wording in casual conversation. "
        "The user may write in Tanglish or mixed Tamil-English, but you must always reply only in natural English unless the user explicitly asks for translation."
    ),
    "fast": (
        "You are Grandpa Assistant running locally through Ollama. "
        "Reply like a natural person with a concise, direct answer unless the user asks for more detail. "
        "Keep it short, easygoing, and human. "
        "The user may write in Tanglish or mixed Tamil-English, but you must always reply only in natural English unless the user explicitly asks for translation."
    ),
    "coding": (
        "You are Grandpa Assistant running locally through Ollama in coding mode. "
        "Focus on correct code, debugging help, and actionable implementation guidance. "
        "Even for technical topics, keep the tone natural and clear instead of robotic. "
        "If the user writes in Tanglish or mixed Tamil-English, still reply only in clear English unless the user explicitly asks for translation."
    ),
}


class OfflineAssistantError(RuntimeError):
    """Raised when the local offline assistant cannot fulfill a request."""


def _normalize_mode(mode: str | None) -> str:
    normalized = str(mode or "auto").strip().lower()
    if normalized not in VALID_MODES:
        raise OfflineAssistantError(
            f"Unsupported mode '{mode}'. Use one of: auto, general, fast, coding."
        )
    return normalized


def _is_coding_prompt(prompt: str) -> bool:
    lowered = prompt.lower()
    return CODING_PATTERN.search(prompt) is not None or any(token in lowered for token in CODING_HINTS)


def _is_fast_prompt(prompt: str) -> bool:
    lowered = prompt.lower()
    if any(token in lowered for token in FAST_HINTS):
        return True
    return len(prompt.split()) <= 12 and len(prompt) <= 80


def select_route(prompt: str, mode: str | None = None) -> dict[str, str]:
    normalized_mode = _normalize_mode(mode)

    if normalized_mode != "auto":
        route = normalized_mode
    elif _is_coding_prompt(prompt):
        route = "coding"
    elif _is_fast_prompt(prompt):
        route = "fast"
    else:
        route = "general"

    return {
        "mode": normalized_mode,
        "route": route,
        "model": MODEL_BY_MODE[route],
    }


def _build_prompt(prompt: str, route: str) -> str:
    emotion_context = build_emotion_prompt_context(prompt)
    mood_context = build_mood_memory_context()
    intelligence_context = build_intelligence_prompt_boost(prompt, context="casual")
    return (
        f"{SYSTEM_PROMPTS[route]}\n"
        f"{emotion_context}\n"
        f"{mood_context}\n"
        f"{intelligence_context or ''}\n\n"
        f"User: {prompt.strip()}\nAssistant:"
    )


def list_installed_models() -> list[str]:
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.ConnectionError as error:
        raise OfflineAssistantError(
            "Ollama is not running. Start Ollama and try again."
        ) from error
    except requests.RequestException as error:
        raise OfflineAssistantError(f"Unable to query Ollama models: {error}") from error

    models = payload.get("models", [])
    names = []
    for item in models:
        if not isinstance(item, dict):
            continue
        name = str(item.get("model") or item.get("name") or "").strip()
        if name:
            names.append(name)
    return names


def get_ollama_status() -> dict[str, Any]:
    try:
        models = list_installed_models()
        return {
            "ok": True,
            "base_url": OLLAMA_BASE_URL,
            "installed_models": models,
        }
    except OfflineAssistantError as error:
        return {
            "ok": False,
            "base_url": OLLAMA_BASE_URL,
            "error": str(error),
            "installed_models": [],
        }


def generate_offline_reply(prompt: str, mode: str | None = None) -> dict[str, str]:
    cleaned_prompt = str(prompt or "").strip()
    if not cleaned_prompt:
        raise OfflineAssistantError("Prompt is required.")

    routing = select_route(cleaned_prompt, mode=mode)
    payload = {
        "model": routing["model"],
        "prompt": _build_prompt(cleaned_prompt, routing["route"]),
        "stream": False,
    }

    try:
        response = requests.post(
            OLLAMA_GENERATE_URL,
            json=payload,
            timeout=OLLAMA_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.ConnectionError as error:
        raise OfflineAssistantError(
            "Ollama is not running. Start Ollama and try again."
        ) from error
    except requests.HTTPError as error:
        body = ""
        try:
            body = error.response.text.strip()
        except Exception:
            body = ""
        if error.response is not None and error.response.status_code == 404:
            raise OfflineAssistantError(
                f"Model '{routing['model']}' is not installed in Ollama yet. "
                f"Run 'ollama pull {routing['model']}' and retry."
            ) from error
        raise OfflineAssistantError(
            f"Ollama request failed for model '{routing['model']}': {body or error}"
        ) from error
    except requests.RequestException as error:
        raise OfflineAssistantError(f"Ollama request failed: {error}") from error

    reply = str(data.get("response") or "").strip()
    if not reply:
        raise OfflineAssistantError(
            f"Ollama returned an empty response for model '{routing['model']}'."
        )

    return {
        "prompt": cleaned_prompt,
        "mode": routing["mode"],
        "route": routing["route"],
        "model": routing["model"],
        "response": reply,
    }
