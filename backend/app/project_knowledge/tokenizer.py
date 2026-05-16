from __future__ import annotations

import re
from typing import Any

from .config import DEFAULT_LIMITS, STOP_WORDS


_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def normalize_text(text: Any) -> str:
    try:
        value = str(text or "")
    except Exception:
        return ""
    value = value.replace("\\", "/")
    value = _CAMEL_BOUNDARY_RE.sub(" ", value)
    value = value.replace("_", " ").replace("-", " ").replace("/", " ").replace(".", " ")
    return value.lower()


def tokenize_text(text: Any) -> list[str]:
    normalized = normalize_text(text)
    tokens: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN_RE.finditer(normalized):
        token = match.group(0)
        if len(token) < DEFAULT_LIMITS.min_token_length:
            continue
        if token in STOP_WORDS:
            continue
        tokens.append(token)
        if token not in seen:
            seen.add(token)
    return tokens


def tokenize_query(query: Any) -> list[str]:
    try:
        value = str(query or "")[: DEFAULT_LIMITS.max_query_chars]
    except Exception:
        value = ""
    tokens = tokenize_text(value)
    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped
