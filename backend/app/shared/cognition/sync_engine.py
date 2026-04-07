from __future__ import annotations

import copy

from cognition.state import load_section, update_section, utc_now
from utils.mood_memory import mood_status_payload


MAX_SYNC_EVENTS = 150


def _compact_text(value) -> str:
    return " ".join(str(value or "").split()).strip()


def queue_sync_event(kind: str, summary: str, entity_id: str = "", payload: dict | None = None) -> dict:
    event = {
        "kind": _compact_text(kind) or "update",
        "summary": _compact_text(summary) or "Updated state",
        "entity_id": _compact_text(entity_id),
        "created_at": utc_now(),
        "payload": payload or {},
    }

    def updater(current):
        data = current if isinstance(current, dict) else {}
        events = list(data.get("queued_events") or [])
        events.append(event)
        data["queued_events"] = events[-MAX_SYNC_EVENTS:]
        data.setdefault("enabled", False)
        data.setdefault("api_base_url", "")
        data.setdefault("device_id", "")
        return data

    update_section("sync", updater)
    return event


def configure_sync(*, enabled: bool | None = None, api_base_url: str | None = None) -> dict:
    def updater(current):
        data = current if isinstance(current, dict) else {}
        if enabled is not None:
            data["enabled"] = bool(enabled)
        if api_base_url is not None:
            data["api_base_url"] = _compact_text(api_base_url)
        return data

    return update_section("sync", updater)


def sync_status_payload() -> dict:
    sync = load_section("sync", {})
    events = list(sync.get("queued_events") or [])
    return {
        "enabled": bool(sync.get("enabled", False)),
        "api_base_url": _compact_text(sync.get("api_base_url")),
        "device_id": _compact_text(sync.get("device_id")),
        "queued_event_count": len(events),
        "last_exported_at": _compact_text(sync.get("last_exported_at")),
        "last_imported_at": _compact_text(sync.get("last_imported_at")),
        "recent_events": events[-8:],
        "summary": (
            "Cross-device sync is future-ready through a local API payload layer. "
            f"{len(events)} event(s) are queued for export."
        ),
    }


def export_sync_payload() -> dict:
    mood = mood_status_payload(limit=10)
    sync = load_section("sync", {})
    exported_at = utc_now()

    def updater(current):
        data = current if isinstance(current, dict) else {}
        data["last_exported_at"] = exported_at
        return data

    update_section("sync", updater)
    return {
        "schema_version": "1.0",
        "exported_at": exported_at,
        "device_id": _compact_text(sync.get("device_id")),
        "mood": mood,
        "events": copy.deepcopy(sync.get("queued_events") or [])[-50:],
    }


def import_sync_payload(payload: dict) -> dict:
    imported_at = utc_now()
    event = {
        "kind": "import",
        "summary": f"Imported sync payload from {payload.get('device_id') or 'unknown device'}",
        "entity_id": _compact_text(payload.get("device_id")),
        "created_at": imported_at,
        "payload": {"schema_version": payload.get("schema_version", "unknown")},
    }

    def updater(current):
        data = current if isinstance(current, dict) else {}
        events = list(data.get("queued_events") or [])
        events.append(event)
        data["queued_events"] = events[-MAX_SYNC_EVENTS:]
        data["last_imported_at"] = imported_at
        return data

    return update_section("sync", updater)
