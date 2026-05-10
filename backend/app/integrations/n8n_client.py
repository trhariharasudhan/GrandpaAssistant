import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any


N8N_WEBHOOK_URL_ENV = "N8N_WEBHOOK_URL"
DEFAULT_N8N_WEBHOOK_URL = "http://localhost:5678/webhook/grandpa-message"
DEFAULT_TIMEOUT_SECONDS = 10

logger = logging.getLogger(__name__)


def _parse_response_body(body: bytes) -> Any:
    text = body.decode("utf-8", errors="replace")
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def send_n8n_message(
    message: str,
    *,
    source: str = "GrandpaAssistant",
    channel: str | None = None,
    raw_command: str | None = None,
    extra_payload: dict[str, Any] | None = None,
    webhook_url: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Forward a message to n8n without letting webhook failures crash the backend.

    Curl example:
    curl -X POST http://localhost:8000/api/automation/n8n/test ^
      -H "Content-Type: application/json" ^
      -d "{\"message\":\"hello from GrandpaAssistant\"}"
    """
    resolved_url = (webhook_url or os.getenv(N8N_WEBHOOK_URL_ENV) or DEFAULT_N8N_WEBHOOK_URL).strip()
    payload = {"message": str(message or ""), "source": source}
    if channel:
        payload["channel"] = str(channel)
    if raw_command:
        payload["raw_command"] = str(raw_command)
    if extra_payload:
        payload.update(extra_payload)
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        resolved_url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            return {
                "ok": 200 <= int(response.status) < 300,
                "status_code": int(response.status),
                "data": _parse_response_body(body),
            }
    except urllib.error.HTTPError as error:
        body = error.read() if hasattr(error, "read") else b""
        logger.warning("n8n webhook returned HTTP %s", getattr(error, "code", None))
        return {
            "ok": False,
            "status_code": int(getattr(error, "code", 0) or 0) or None,
            "data": _parse_response_body(body),
        }
    except Exception as error:
        logger.warning("n8n webhook call failed: %s", error)
        return {
            "ok": False,
            "status_code": None,
            "data": {"error": str(error), "message": "n8n webhook is unavailable."},
        }
