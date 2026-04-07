from __future__ import annotations

import hashlib

from cognition.state import load_section, update_section, utc_now


MAX_ERRORS = 120


def _compact_text(value) -> str:
    return " ".join(str(value or "").split()).strip()


def _fingerprint(source: str, message: str) -> str:
    return hashlib.sha1(f"{_compact_text(source).lower()}::{_compact_text(message).lower()}".encode("utf-8")).hexdigest()


def _suggest_fix(message: str) -> str:
    lowered = _compact_text(message).lower()
    if "ollama" in lowered and ("not running" in lowered or "connection" in lowered):
        return "Start Ollama and verify the local model server is reachable."
    if "model" in lowered and "not installed" in lowered:
        return "Pull the missing local model with Ollama and try again."
    if "tesseract" in lowered or "ocr" in lowered:
        return "Check that Tesseract OCR is installed and available in PATH."
    if "microphone" in lowered or "audio" in lowered:
        return "Check the active input device and microphone permissions."
    if "camera" in lowered:
        return "Check camera permissions and whether another app is already using the camera."
    if "permission" in lowered or "access is denied" in lowered:
        return "Retry from a trusted terminal or adjust file and device permissions."
    if "timeout" in lowered:
        return "Retry the action and check whether the dependency or model is still warming up."
    return "Retry the action, then inspect the latest logs and health checks for the exact failing dependency."


def record_system_error(source: str, message: str, metadata: dict | None = None) -> dict:
    clean_source = _compact_text(source) or "system"
    clean_message = _compact_text(message) or "Unknown error"
    fingerprint = _fingerprint(clean_source, clean_message)
    record = {
        "fingerprint": fingerprint,
        "source": clean_source,
        "message": clean_message,
        "suggestion": _suggest_fix(clean_message),
        "metadata": metadata or {},
        "created_at": utc_now(),
    }

    def updater(current):
        data = current if isinstance(current, dict) else {}
        errors = list(data.get("errors") or [])
        errors.append(record)
        data["errors"] = errors[-MAX_ERRORS:]
        counters = dict(data.get("fingerprints") or {})
        counters[fingerprint] = int(counters.get(fingerprint, 0) or 0) + 1
        data["fingerprints"] = counters
        data["last_updated_at"] = utc_now()
        return data

    update_section("recovery", updater)
    return record


def recovery_status_payload() -> dict:
    section = load_section("recovery", {})
    errors = list(section.get("errors") or [])
    counters = dict(section.get("fingerprints") or {})
    repeated = []
    for item in reversed(errors):
        count = int(counters.get(item.get("fingerprint"), 0) or 0)
        if count < 2:
            continue
        repeated.append(
            {
                "source": item.get("source"),
                "message": item.get("message"),
                "count": count,
                "suggestion": item.get("suggestion"),
            }
        )
        if len(repeated) >= 5:
            break
    return {
        "error_count": len(errors),
        "repeated_errors": repeated,
        "latest_error": errors[-1] if errors else {},
        "summary": (
            f"Tracked {len(errors)} runtime error record(s)."
            + (f" {len(repeated)} repeated issue(s) have recovery suggestions." if repeated else "")
        ),
    }
