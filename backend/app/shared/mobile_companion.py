from __future__ import annotations

import hashlib
import ipaddress
import os
import secrets
import socket
import threading
import time
import uuid
from typing import Any

from security.encryption_utils import read_encrypted_json, remember_protected_target, write_encrypted_json
from utils.config import get_setting


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "backend", "data")
STATE_PATH = os.path.join(DATA_DIR, "mobile_companion.json")


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _token_hash(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _default_state() -> dict[str, Any]:
    return {
        "pairing": {
            "code": "",
            "requested_name": "",
            "requested_at": "",
            "expires_at": 0.0,
        },
        "devices": [],
        "events": [],
        "notifications": [],
        "next_seq": 1,
    }


def _pairing_ttl_seconds() -> int:
    try:
        return max(60, int(get_setting("mobile.pairing_code_ttl_seconds", 300) or 300))
    except Exception:
        return 300


def _event_history_limit() -> int:
    try:
        return max(50, int(get_setting("mobile.event_history_limit", 240) or 240))
    except Exception:
        return 240


def _notification_history_limit() -> int:
    try:
        return max(20, int(get_setting("mobile.notification_history_limit", 80) or 80))
    except Exception:
        return 80


def _command_history_limit() -> int:
    try:
        return max(20, int(get_setting("mobile.command_history_limit", 60) or 60))
    except Exception:
        return 60


def _private_ipv4_addresses() -> list[str]:
    addresses = set()
    with threading.Lock():
        try:
            hostnames = {socket.gethostname(), socket.getfqdn()}
            for host in hostnames:
                if not host:
                    continue
                with_addresses = socket.gethostbyname_ex(host)[2]
                for item in with_addresses:
                    try:
                        address = ipaddress.ip_address(item)
                    except ValueError:
                        continue
                    if (
                        address.version == 4
                        and not address.is_loopback
                        and not address.is_link_local
                        and address.is_private
                    ):
                        addresses.add(str(address))
        except Exception:
            pass
    return sorted(addresses)


class MobileCompanionService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._active_connections: dict[str, int] = {}

    def _load_state(self) -> dict[str, Any]:
        state = read_encrypted_json(STATE_PATH, _default_state())
        if not isinstance(state, dict):
            return _default_state()
        payload = _default_state()
        payload.update({key: value for key, value in state.items() if key in payload})
        if not isinstance(payload.get("devices"), list):
            payload["devices"] = []
        if not isinstance(payload.get("events"), list):
            payload["events"] = []
        if not isinstance(payload.get("notifications"), list):
            payload["notifications"] = []
        if not isinstance(payload.get("pairing"), dict):
            payload["pairing"] = _default_state()["pairing"]
        if not isinstance(payload.get("next_seq"), int):
            payload["next_seq"] = 1
        return payload

    def _save_state(self, state: dict[str, Any]) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        write_encrypted_json(STATE_PATH, state, protect=True)
        remember_protected_target(STATE_PATH)

    def _sanitize_device(self, device: dict[str, Any]) -> dict[str, Any]:
        return {
            "device_id": _compact_text(device.get("device_id")),
            "name": _compact_text(device.get("name")) or "Mobile device",
            "platform": _compact_text(device.get("platform")) or "unknown",
            "app_version": _compact_text(device.get("app_version")) or "",
            "linked_at": _compact_text(device.get("linked_at")),
            "last_seen_at": _compact_text(device.get("last_seen_at")),
            "last_command_at": _compact_text(device.get("last_command_at")),
            "role": _compact_text(device.get("role")) or "owner",
            "revoked": bool(device.get("revoked")),
            "permissions": dict(device.get("permissions") or {}),
            "token_hint": _compact_text(device.get("token_hint")),
            "connected": bool(self._active_connections.get(_compact_text(device.get("device_id")), 0)),
        }

    def _append_event(
        self,
        state: dict[str, Any],
        event_type: str,
        payload: dict[str, Any],
        *,
        target_device_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        entry = {
            "seq": int(state.get("next_seq", 1) or 1),
            "type": _compact_text(event_type) or "event",
            "created_at": _utc_now(),
            "targets": list(target_device_ids or []),
            "payload": payload or {},
        }
        state["next_seq"] = entry["seq"] + 1
        events = list(state.get("events") or [])
        events.append(entry)
        limit = _event_history_limit()
        if len(events) > limit:
            del events[:-limit]
        state["events"] = events
        return entry

    def _find_device_by_token(self, state: dict[str, Any], token: str) -> dict[str, Any] | None:
        token_digest = _token_hash(token)
        for device in state.get("devices") or []:
            if device.get("revoked"):
                continue
            if _compact_text(device.get("token_hash")) == token_digest:
                return device
        return None

    def start_pairing(self, requested_name: str = "") -> dict[str, Any]:
        with self._lock:
            state = self._load_state()
            code = "".join(secrets.choice("0123456789") for _ in range(6))
            pairing = {
                "code": code,
                "requested_name": _compact_text(requested_name) or "Grandpa Mobile",
                "requested_at": _utc_now(),
                "expires_at": time.time() + _pairing_ttl_seconds(),
            }
            state["pairing"] = pairing
            self._append_event(
                state,
                "mobile.pairing.started",
                {
                    "requested_name": pairing["requested_name"],
                    "expires_in_seconds": _pairing_ttl_seconds(),
                },
            )
            self._save_state(state)
            return self.current_pairing_payload(include_code=True)

    def current_pairing_payload(self, *, include_code: bool = False) -> dict[str, Any]:
        with self._lock:
            state = self._load_state()
            pairing = dict(state.get("pairing") or {})
            expires_at = float(pairing.get("expires_at", 0.0) or 0.0)
            active = bool(pairing.get("code")) and expires_at > time.time()
            if not active and pairing.get("code"):
                state["pairing"] = _default_state()["pairing"]
                self._save_state(state)
                pairing = state["pairing"]
                expires_at = 0.0
            payload = {
                "active": active,
                "requested_name": _compact_text(pairing.get("requested_name")),
                "requested_at": _compact_text(pairing.get("requested_at")),
                "expires_at": expires_at,
                "expires_in_seconds": max(0, int(expires_at - time.time())) if active else 0,
                "lan_addresses": _private_ipv4_addresses(),
            }
            if include_code and active:
                payload["code"] = _compact_text(pairing.get("code"))
            return payload

    def complete_pairing(self, code: str, device_name: str, platform: str = "", app_version: str = "") -> dict[str, Any]:
        normalized_code = "".join(ch for ch in str(code or "") if ch.isdigit())
        clean_name = _compact_text(device_name) or "Grandpa Mobile"
        with self._lock:
            state = self._load_state()
            pairing = dict(state.get("pairing") or {})
            expires_at = float(pairing.get("expires_at", 0.0) or 0.0)
            active_code = _compact_text(pairing.get("code"))
            if not active_code or expires_at <= time.time():
                raise ValueError("Pairing code expired. Start pairing again on the desktop app.")
            if normalized_code != active_code:
                raise ValueError("Pairing code is invalid.")

            token = secrets.token_urlsafe(32)
            device_id = str(uuid.uuid4())
            linked_at = _utc_now()
            device = {
                "device_id": device_id,
                "name": clean_name,
                "platform": _compact_text(platform) or "unknown",
                "app_version": _compact_text(app_version),
                "linked_at": linked_at,
                "last_seen_at": linked_at,
                "last_command_at": "",
                "role": "owner",
                "permissions": {
                    "chat": True,
                    "commands": True,
                    "iot": True,
                    "tasks": True,
                    "files": True,
                },
                "revoked": False,
                "token_hash": _token_hash(token),
                "token_hint": token[-6:],
            }
            devices = [item for item in (state.get("devices") or []) if not item.get("revoked")]
            devices.append(device)
            state["devices"] = devices[-12:]
            state["pairing"] = _default_state()["pairing"]
            self._append_event(
                state,
                "mobile.device.paired",
                {
                    "device": self._sanitize_device(device),
                },
            )
            self._save_state(state)
            return {
                "token": token,
                "device": self._sanitize_device(device),
                "pairing": self.current_pairing_payload(include_code=False),
            }

    def authenticate_token(self, token: str) -> dict[str, Any] | None:
        clean_token = _compact_text(token)
        if not clean_token:
            return None
        with self._lock:
            state = self._load_state()
            device = self._find_device_by_token(state, clean_token)
            if not device:
                return None
            device["last_seen_at"] = _utc_now()
            self._save_state(state)
            return self._sanitize_device(device)

    def revoke_device(self, device_id: str) -> tuple[bool, str]:
        clean_id = _compact_text(device_id)
        if not clean_id:
            return False, "Device id is required."
        with self._lock:
            state = self._load_state()
            for device in state.get("devices") or []:
                if _compact_text(device.get("device_id")) != clean_id:
                    continue
                device["revoked"] = True
                device["last_seen_at"] = _utc_now()
                self._append_event(
                    state,
                    "mobile.device.revoked",
                    {"device_id": clean_id, "name": _compact_text(device.get("name"))},
                )
                self._save_state(state)
                self._active_connections.pop(clean_id, None)
                return True, f"Revoked mobile device {_compact_text(device.get('name')) or clean_id}."
        return False, "Mobile device not found."

    def note_connection(self, device_id: str, connected: bool) -> None:
        clean_id = _compact_text(device_id)
        if not clean_id:
            return
        with self._lock:
            current = int(self._active_connections.get(clean_id, 0) or 0)
            if connected:
                self._active_connections[clean_id] = current + 1
            else:
                if current <= 1:
                    self._active_connections.pop(clean_id, None)
                else:
                    self._active_connections[clean_id] = current - 1

    def note_command(self, device_id: str, command: str) -> None:
        clean_id = _compact_text(device_id)
        clean_command = _compact_text(command)
        if not clean_id or not clean_command:
            return
        with self._lock:
            state = self._load_state()
            for device in state.get("devices") or []:
                if _compact_text(device.get("device_id")) != clean_id:
                    continue
                device["last_command_at"] = _utc_now()
                break
            self._append_event(
                state,
                "mobile.command.sent",
                {"device_id": clean_id, "command": clean_command},
                target_device_ids=[clean_id],
            )
            self._save_state(state)

    def push_event(self, event_type: str, payload: dict[str, Any], *, target_device_ids: list[str] | None = None) -> dict[str, Any]:
        with self._lock:
            state = self._load_state()
            event = self._append_event(state, event_type, payload or {}, target_device_ids=target_device_ids)
            self._save_state(state)
            return event

    def queue_notification(
        self,
        title: str,
        body: str,
        *,
        level: str = "info",
        target_device_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        notification = {
            "id": str(uuid.uuid4()),
            "title": _compact_text(title) or "Grandpa Assistant",
            "body": _compact_text(body),
            "level": _compact_text(level) or "info",
            "created_at": _utc_now(),
            "targets": list(target_device_ids or []),
        }
        with self._lock:
            state = self._load_state()
            notifications = list(state.get("notifications") or [])
            notifications.append(notification)
            limit = _notification_history_limit()
            if len(notifications) > limit:
                del notifications[:-limit]
            state["notifications"] = notifications
            self._append_event(
                state,
                "mobile.notification",
                notification,
                target_device_ids=target_device_ids,
            )
            self._save_state(state)
        return notification

    def record_chat_message(self, role: str, text: str, *, session_id: str = "", source: str = "") -> None:
        clean_text = _compact_text(text)
        if not clean_text:
            return
        self.push_event(
            "mobile.chat.message",
            {
                "role": _compact_text(role) or "assistant",
                "text": clean_text,
                "session_id": _compact_text(session_id),
                "source": _compact_text(source) or "assistant",
            },
        )

    def record_command_result(
        self,
        command: str,
        messages: list[str],
        *,
        source: str = "",
        target_device_ids: list[str] | None = None,
    ) -> None:
        cleaned_messages = [_compact_text(item) for item in (messages or []) if _compact_text(item)]
        self.push_event(
            "mobile.command.result",
            {
                "command": _compact_text(command),
                "messages": cleaned_messages[-8:],
                "source": _compact_text(source) or "assistant",
            },
            target_device_ids=target_device_ids,
        )

    def events_since(self, last_seq: int = 0, *, device_id: str = "") -> list[dict[str, Any]]:
        clean_device_id = _compact_text(device_id)
        with self._lock:
            state = self._load_state()
            items = []
            for event in state.get("events") or []:
                if int(event.get("seq", 0) or 0) <= int(last_seq or 0):
                    continue
                targets = list(event.get("targets") or [])
                if targets and clean_device_id and clean_device_id not in targets:
                    continue
                items.append(event)
            return items

    def notifications(self, *, limit: int = 20, device_id: str = "") -> list[dict[str, Any]]:
        clean_device_id = _compact_text(device_id)
        with self._lock:
            state = self._load_state()
            items = []
            for notification in reversed(state.get("notifications") or []):
                targets = list(notification.get("targets") or [])
                if targets and clean_device_id and clean_device_id not in targets:
                    continue
                items.append(notification)
                if len(items) >= max(1, int(limit or 20)):
                    break
            return items

    def status_payload(self) -> dict[str, Any]:
        with self._lock:
            state = self._load_state()
            devices = [self._sanitize_device(item) for item in (state.get("devices") or []) if not item.get("revoked")]
            pairing = self.current_pairing_payload(include_code=True)
            connected_count = sum(1 for item in devices if item.get("connected"))
            summary = (
                f"Mobile companion ready with {len(devices)} linked device(s) and {connected_count} active connection(s)."
                if devices
                else "Mobile companion is ready but no phone is linked yet."
            )
            if pairing.get("active") and pairing.get("code"):
                summary += f" Pairing code {pairing['code']} is active for {pairing.get('expires_in_seconds', 0)} seconds."
            return {
                "enabled": True,
                "pairing": pairing,
                "paired_devices": devices,
                "paired_count": len(devices),
                "active_connections": connected_count,
                "event_history_count": len(state.get("events") or []),
                "notification_count": len(state.get("notifications") or []),
                "lan_addresses": pairing.get("lan_addresses", []),
                "summary": summary,
            }

    def queue_update(self, message: str) -> str:
        clean_message = _compact_text(message)
        if not clean_message:
            return "Tell me the mobile update message."
        status = self.status_payload()
        if status.get("paired_count", 0) <= 0:
            return "Mobile companion is not linked yet. Start mobile pairing first."
        self.queue_notification("Grandpa Assistant Update", clean_message, level="info")
        return f"Sent mobile update: {clean_message}"

    def pairing_summary(self, requested_name: str = "") -> str:
        pairing = self.start_pairing(requested_name=requested_name)
        addresses = pairing.get("lan_addresses") or []
        address_text = ", ".join(addresses[:3]) if addresses else "your desktop IP"
        return (
            f"Mobile pairing started for {pairing.get('requested_name') or 'Grandpa Mobile'}. "
            f"Use code {pairing.get('code', '')} in the mobile app within {pairing.get('expires_in_seconds', 0)} seconds. "
            f"Connect to {address_text} on port 8765 unless you changed the desktop API port."
        )


MOBILE_COMPANION = MobileCompanionService()
