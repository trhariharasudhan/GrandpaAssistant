import os


DEFAULT_LOCAL_CORS_ORIGINS = (
    "http://127.0.0.1:8765",
    "http://localhost:8765",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
)


def localhost_cors_origins() -> list[str]:
    configured = os.getenv("GRANDPA_ASSISTANT_CORS_ORIGINS", "").strip()
    if configured:
        origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
        if origins:
            return origins
    return list(DEFAULT_LOCAL_CORS_ORIGINS)
