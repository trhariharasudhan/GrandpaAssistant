from __future__ import annotations

import os
from typing import Any

from security.state import STATE, append_security_activity, utc_now
from utils.config import get_setting


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _approval_required_types() -> set[str]:
    raw = get_setting("security.device_approval_required_types", ["usb", "storage", "camera", "microphone"])
    if isinstance(raw, list):
        return {_compact_text(item).lower() for item in raw if _compact_text(item)}
    return {"usb", "storage", "camera", "microphone"}


def _device_key(device: dict[str, Any]) -> str:
    return _compact_text(device.get("id") or device.get("name") or device.get("device_name"))


def sync_device_inventory(device_manager) -> dict[str, Any]:
    devices = device_manager.get_devices(allow_refresh=False) if device_manager else []
    snapshot = STATE.snapshot()
    security_devices = snapshot.get("devices", {})
    previous_inventory = dict(security_devices.get("inventory") or {})
    trusted_ids = set(security_devices.get("trusted_device_ids") or [])
    unknown_ids = []
    recent_alerts = list(security_devices.get("recent_alerts") or [])
    inventory: dict[str, dict[str, Any]] = {}

    for device in devices:
        device_id = _device_key(device)
        if not device_id:
            continue
        device_type = _compact_text(device.get("type") or "unknown").lower() or "unknown"
        known = previous_inventory.get(device_id, {})
        trusted = bool(known.get("trusted")) or device_id in trusted_ids
        permission_required = device_type in _approval_required_types() and not trusted
        entry = {
            "id": device_id,
            "name": _compact_text(device.get("name") or device.get("device_name") or device_id),
            "type": device_type,
            "status": _compact_text(device.get("status") or "connected") or "connected",
            "trusted": trusted,
            "permission_required": permission_required,
            "updated_at": utc_now(),
        }
        inventory[device_id] = entry
        if permission_required:
            unknown_ids.append(device_id)
            if device_id not in previous_inventory:
                alert_message = f"Unknown device detected: {entry['name']}"
                recent_alerts.append(
                    {
                        "timestamp": utc_now(),
                        "device_id": device_id,
                        "message": alert_message,
                        "type": device_type,
                    }
                )
                append_security_activity(
                    "unknown_device_detected",
                    level="warning",
                    source="device-monitor",
                    message=alert_message,
                    metadata={"device_id": device_id, "device_type": device_type},
                )

    recent_alerts = recent_alerts[-20:]

    def _update(state: dict[str, Any]) -> None:
        device_state = state.setdefault("devices", {})
        device_state["inventory"] = inventory
        device_state["trusted_device_ids"] = sorted(trusted_ids)
        device_state["unknown_device_ids"] = unknown_ids
        device_state["recent_alerts"] = recent_alerts
        device_state["last_synced_at"] = utc_now()

    snapshot = STATE.update(_update).get("devices", {})
    return {
        "inventory": snapshot.get("inventory", {}),
        "unknown_device_ids": snapshot.get("unknown_device_ids", []),
        "recent_alerts": snapshot.get("recent_alerts", []),
        "last_synced_at": snapshot.get("last_synced_at", ""),
    }


def trust_device(device_query: str) -> tuple[bool, str]:
    query = _compact_text(device_query).lower()
    if not query:
        return False, "Tell me which device you want to trust."

    snapshot = STATE.snapshot().get("devices", {})
    inventory = dict(snapshot.get("inventory") or {})
    matched_id = ""
    for device_id, item in inventory.items():
        name = _compact_text(item.get("name")).lower()
        if query in {device_id.lower(), name} or query in name:
            matched_id = device_id
            break
    if not matched_id:
        return False, "I could not find that device in the security inventory."

    def _update(state: dict[str, Any]) -> None:
        device_state = state.setdefault("devices", {})
        trusted_ids = set(device_state.get("trusted_device_ids") or [])
        trusted_ids.add(matched_id)
        device_state["trusted_device_ids"] = sorted(trusted_ids)
        inventory = device_state.setdefault("inventory", {})
        if matched_id in inventory:
            inventory[matched_id]["trusted"] = True
            inventory[matched_id]["permission_required"] = False
        unknown = [item for item in device_state.get("unknown_device_ids", []) if item != matched_id]
        device_state["unknown_device_ids"] = unknown

    STATE.update(_update)
    append_security_activity(
        "device_trusted",
        source="device-monitor",
        message=f"Trusted device {matched_id}",
        metadata={"device_id": matched_id},
    )
    return True, f"Device {matched_id} is now trusted."


def device_security_status_payload(limit: int = 8) -> dict[str, Any]:
    snapshot = STATE.snapshot().get("devices", {})
    inventory = list((snapshot.get("inventory") or {}).values())
    unknown_ids = list(snapshot.get("unknown_device_ids") or [])
    alerts = list(snapshot.get("recent_alerts") or [])[-max(1, int(limit)):]
    return {
        "inventory_count": len(inventory),
        "unknown_device_count": len(unknown_ids),
        "unknown_devices": [item for item in inventory if item.get("id") in unknown_ids][:limit],
        "recent_alerts": alerts,
        "trusted_device_ids": list(snapshot.get("trusted_device_ids") or []),
        "last_synced_at": snapshot.get("last_synced_at", ""),
        "approval_required_types": sorted(_approval_required_types()),
    }
