import json
import os
import threading
import time
import uuid
from typing import Any

from utils.paths import logs_path

LOG_DIR = logs_path()
API_LOG_PATH = logs_path("fastapi_events.jsonl")

_WRITE_LOCK = threading.Lock()


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ensure_log_dir() -> str:
    os.makedirs(LOG_DIR, exist_ok=True)
    return LOG_DIR


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def log_api_event(event_type: str, **fields: Any) -> None:
    ensure_log_dir()
    payload = {
        "timestamp": _utc_now(),
        "event_type": event_type,
    }
    payload.update(fields)

    line = json.dumps(payload, ensure_ascii=False)
    with _WRITE_LOCK:
        with open(API_LOG_PATH, "a", encoding="utf-8") as file:
            file.write(line + "\n")


def request_summary(request: Any) -> dict[str, Any]:
    client = getattr(request, "client", None)
    return {
        "method": getattr(request, "method", ""),
        "path": getattr(getattr(request, "url", None), "path", ""),
        "query": str(getattr(getattr(request, "url", None), "query", "") or ""),
        "client_host": getattr(client, "host", None),
    }
