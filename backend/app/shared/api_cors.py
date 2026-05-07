import os
from urllib.parse import urlparse


DEFAULT_LOCAL_CORS_ORIGINS = (
    "http://127.0.0.1:8765",
    "http://localhost:8765",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
)


def localhost_cors_origins() -> list[str]:
    configured = os.getenv("GRANDPA_ASSISTANT_CORS_ORIGINS", "").strip()
    if configured:
        origins = [
            origin
            for origin in (origin.strip() for origin in configured.split(",") if origin.strip())
            if _is_safe_local_origin(origin)
        ]
        if origins:
            return origins
    return list(DEFAULT_LOCAL_CORS_ORIGINS)


def _is_safe_local_origin(origin: str) -> bool:
    if origin in {"*", "null"}:
        return False
    try:
        parsed = urlparse(origin)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    hostname = (parsed.hostname or "").lower()
    return hostname in {"localhost", "127.0.0.1", "::1"}
