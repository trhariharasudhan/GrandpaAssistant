import importlib.util
import ipaddress
import json
import os
import re
import socket
import subprocess
import threading
import time
from typing import Any

import psutil

from iot_registry import (
    build_iot_knowledge_response,
    build_iot_prompt_context,
    infer_iot_profile,
    match_configured_iot_device,
    summarize_iot_config,
)
from utils.config import get_setting


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BACKEND_DATA_DIR = os.path.join(PROJECT_ROOT, "backend", "data")
DEVICE_STATE_PATH = os.path.join(BACKEND_DATA_DIR, "hardware_devices.json")

_SMART_DEVICE_KEYWORDS = (
    "alexa",
    "echo",
    "nest",
    "google",
    "chromecast",
    "tuya",
    "sonoff",
    "shelly",
    "wiz",
    "hue",
    "ring",
    "camera",
    "iot",
    "smart",
    "roku",
    "firetv",
    "esp",
)
_USB_SKIP_KEYWORDS = (
    "controller",
    "root hub",
    "host controller",
    "composite device",
    "generic superspeed usb hub",
    "generic usb hub",
    "xhci",
    "unknown usb device",
)


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_key(value: Any) -> str:
    return _compact_text(value).lower()


def _normalize_match_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _normalize_key(value)).strip()


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_json_dump(path: str, payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
    os.replace(temp_path, path)


def _safe_json_load(path: str) -> dict[str, Any] | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _local_hostname() -> str:
    return _compact_text(socket.gethostname()) or "offline-assistant"


def _local_ip_addresses() -> set[str]:
    addresses = set()
    for interface_addresses in psutil.net_if_addrs().values():
        for item in interface_addresses:
            if getattr(item, "family", None) == socket.AF_INET and item.address:
                addresses.add(item.address)
    return addresses


class DeviceManager:
    def __init__(self, state_path: str | None = None) -> None:
        self.state_path = state_path or DEVICE_STATE_PATH
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._devices: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []
        self._capabilities = self._empty_capabilities()
        self._last_updated_at = ""
        self._monitoring = False
        self._last_camera_scan_at = 0.0
        self._last_network_scan_at = 0.0
        self._camera_cache: dict[str, dict[str, Any]] = {}
        self._network_cache: dict[str, dict[str, Any]] = {}
        self._network_name_cache: dict[str, str] = {}
        self._initial_scan_completed = False
        self._speaker = self._resolve_speaker()
        self._hydrate_from_disk()

    def _resolve_speaker(self):
        try:
            from voice.speak import speak

            return speak
        except Exception:
            return None

    def _empty_capabilities(self) -> dict[str, Any]:
        return {
            "vision_enabled": False,
            "voice_enabled": False,
            "storage_ready": False,
            "iot_detected": False,
            "smart_home_configured": False,
            "smart_home_enabled": False,
            "iot_control_ready": False,
            "connected_types": {},
            "summary": "No active hardware capabilities detected yet.",
        }

    def _event_history_limit(self) -> int:
        try:
            return max(10, int(get_setting("hardware.event_history_limit", 40) or 40))
        except Exception:
            return 40

    def _poll_interval_seconds(self) -> float:
        try:
            return max(1.5, float(get_setting("hardware.poll_interval_seconds", 4.0) or 4.0))
        except Exception:
            return 4.0

    def _camera_probe_max_index(self) -> int:
        try:
            return max(0, min(6, int(get_setting("hardware.camera_probe_max_index", 2) or 2)))
        except Exception:
            return 2

    def _camera_probe_interval_seconds(self) -> float:
        try:
            return max(5.0, float(get_setting("hardware.camera_probe_interval_seconds", 15.0) or 15.0))
        except Exception:
            return 15.0

    def _network_scan_enabled(self) -> bool:
        return bool(get_setting("hardware.iot_scan_enabled", True))

    def _network_scan_interval_seconds(self) -> float:
        try:
            return max(20.0, float(get_setting("hardware.iot_scan_interval_seconds", 45.0) or 45.0))
        except Exception:
            return 45.0

    def _network_name_lookup_enabled(self) -> bool:
        return bool(get_setting("iot.network_name_lookup_enabled", True))

    def _network_name_lookup_limit(self) -> int:
        try:
            return max(0, int(get_setting("iot.network_name_lookup_limit", 6) or 6))
        except Exception:
            return 6

    def _storage_scan_entry_limit(self) -> int:
        try:
            return max(5, int(get_setting("hardware.storage_scan_entry_limit", 24) or 24))
        except Exception:
            return 24

    def _speak_events_enabled(self) -> bool:
        return bool(get_setting("hardware.speak_events_enabled", True))

    def _hydrate_from_disk(self) -> None:
        payload = _safe_json_load(self.state_path) or {}
        devices = payload.get("devices")
        events = payload.get("events")
        capabilities = payload.get("capabilities")
        if isinstance(devices, list):
            self._devices = {
                _compact_text(item.get("id")): item
                for item in devices
                if isinstance(item, dict) and _compact_text(item.get("id"))
            }
        if isinstance(events, list):
            self._events = [item for item in events if isinstance(item, dict)][-self._event_history_limit():]
        if isinstance(capabilities, dict):
            self._capabilities = capabilities
        self._last_updated_at = _compact_text(payload.get("updated_at"))

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                self._monitoring = True
                return
            self._stop_event.clear()
            self._monitoring = True
            self._thread = threading.Thread(target=self._monitor_loop, name="device-monitor", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            self._monitoring = False

    def refresh(self, *, emit_events: bool = True) -> dict[str, Any]:
        scanned_devices = self._scan_devices()
        now = _utc_now()
        new_events = []

        with self._lock:
            previous_devices = dict(self._devices)
            previous_ids = set(previous_devices.keys())
            current_ids = set(scanned_devices.keys())

            for added_id in sorted(current_ids - previous_ids):
                new_events.append(self._build_event(scanned_devices[added_id], "connected", now))

            for removed_id in sorted(previous_ids - current_ids):
                new_events.append(self._build_event(previous_devices[removed_id], "disconnected", now))

            self._devices = scanned_devices
            self._capabilities = self._build_capabilities(scanned_devices)
            self._last_updated_at = now
            self._initial_scan_completed = True

            if emit_events and new_events:
                self._events.extend(new_events)
                self._events = self._events[-self._event_history_limit():]

            self._save_state_locked()

        if emit_events:
            for event in new_events:
                self._announce_event(event)

        return self.get_status()

    def get_devices(self, allow_refresh: bool = True) -> list[dict[str, Any]]:
        if allow_refresh and not self._initial_scan_completed and not self._monitoring:
            self._ensure_initial_scan()
        with self._lock:
            devices = [dict(item) for item in self._devices.values()]
        return sorted(devices, key=lambda item: (item.get("type", ""), item.get("name", "")))

    def get_recent_events(self, limit: int = 12) -> list[dict[str, Any]]:
        with self._lock:
            items = [dict(item) for item in self._events[-max(1, limit):]]
        return items

    def get_iot_devices(self) -> list[dict[str, Any]]:
        return [
            item
            for item in self.get_devices()
            if item.get("type") in {"iot", "network"}
        ]

    def get_status(self) -> dict[str, Any]:
        if not self._initial_scan_completed and not self._monitoring:
            self._ensure_initial_scan()
        with self._lock:
            devices = [dict(item) for item in self._devices.values()]
            capabilities = dict(self._capabilities)
            updated_at = self._last_updated_at
            monitoring = self._monitoring
            event_count = len(self._events)
        return {
            "ok": True,
            "monitoring": monitoring,
            "hostname": _local_hostname(),
            "updated_at": updated_at,
            "device_count": len(devices),
            "devices": sorted(devices, key=lambda item: (item.get("type", ""), item.get("name", ""))),
            "recent_events": self.get_recent_events(limit=8),
            "event_count": event_count,
            "capabilities": capabilities,
        }

    def get_iot_status(self) -> dict[str, Any]:
        discovered_devices = self.get_iot_devices()
        configured = summarize_iot_config()
        category_counts: dict[str, int] = {}
        protocol_hints: dict[str, int] = {}
        control_ready_count = 0

        for item in discovered_devices:
            profile = item.get("iot_profile") or {}
            category = profile.get("category") or item.get("type", "iot")
            category_counts[category] = category_counts.get(category, 0) + 1
            for protocol in profile.get("protocol_hints") or []:
                protocol_hints[protocol] = protocol_hints.get(protocol, 0) + 1
            if item.get("control_ready"):
                control_ready_count += 1

        summary_parts = []
        if discovered_devices:
            summary_parts.append(
                f"I can currently see {len(discovered_devices)} IoT or network device(s)."
            )
        else:
            summary_parts.append("No IoT or network devices are currently visible on the local scan.")

        if configured.get("configured"):
            summary_parts.append(configured.get("summary", "Smart Home config is available."))
        else:
            summary_parts.append("Smart Home control config is not set up yet.")

        if category_counts:
            top_categories = ", ".join(
                f"{name}={count}" for name, count in sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
            )
            summary_parts.append(f"Detected categories: {top_categories}.")

        if control_ready_count:
            summary_parts.append(f"{control_ready_count} discovered device(s) look ready for mapped control.")

        return {
            "ok": True,
            "discovered_count": len(discovered_devices),
            "control_ready_count": control_ready_count,
            "discovered_devices": discovered_devices,
            "categories": category_counts,
            "protocol_hints": protocol_hints,
            "configured": configured,
            "summary": " ".join(summary_parts),
        }

    def status_summary(self) -> str:
        status = self.get_status()
        capabilities = status["capabilities"]
        devices = status["devices"]
        if not devices:
            return "No connected hardware devices are currently detected."

        parts = [f"I can currently see {len(devices)} connected device or devices."]
        if capabilities.get("vision_enabled"):
            parts.append("Vision system is ready.")
        if capabilities.get("voice_enabled"):
            parts.append("Voice input is ready.")
        if capabilities.get("storage_ready"):
            parts.append("Storage scan is available.")
        if capabilities.get("iot_detected"):
            parts.append("Local network devices are visible.")
        parts.append(self.device_summary())
        return " ".join(parts)

    def device_summary(self) -> str:
        devices = self.get_devices()
        if not devices:
            return "No devices are connected right now."
        lines = []
        for item in devices[:8]:
            parts = [item.get("name") or item.get("id"), f"type {item.get('type', 'unknown')}"]
            if item.get("path"):
                parts.append(f"path {item['path']}")
            elif item.get("mountpoint"):
                parts.append(f"path {item['mountpoint']}")
            lines.append(", ".join(parts))
        suffix = "" if len(devices) <= 8 else f" Plus {len(devices) - 8} more."
        return "Connected devices: " + " | ".join(lines) + suffix

    def iot_summary(self) -> str:
        iot_status = self.get_iot_status()
        discovered = iot_status["discovered_devices"]
        if not discovered and not iot_status["configured"].get("configured"):
            return "I do not see any smart-home devices yet, and Smart Home control is not configured."

        parts = [iot_status["summary"]]
        if discovered:
            lines = []
            for item in discovered[:6]:
                profile = item.get("iot_profile") or {}
                category = profile.get("category") or item.get("type", "iot")
                detail = f"{item.get('name', 'device')} ({category})"
                if item.get("control_ready"):
                    detail += ", control ready"
                lines.append(detail)
            parts.append("Visible IoT devices: " + " | ".join(lines) + ".")
        configured_devices = iot_status["configured"].get("devices") or []
        if configured_devices:
            parts.append(
                "Configured smart-home devices: "
                + " | ".join(item.get("name", "device") for item in configured_devices[:6])
                + "."
            )
        return " ".join(part for part in parts if part)

    def local_response(self, prompt: str) -> str | None:
        normalized = _normalize_match_text(prompt)
        if normalized in {
            "devices",
            "list devices",
            "show devices",
            "connected devices",
            "what devices are connected",
            "which devices are connected",
            "hardware devices",
        }:
            return self.device_summary()
        if normalized in {
            "assistant status",
            "hardware status",
            "device status",
            "assistant hardware status",
            "system device status",
        }:
            return self.status_summary()
        if normalized in {"recent device events", "device events", "hardware events"}:
            events = self.get_recent_events(limit=6)
            if not events:
                return "No recent hardware change events were detected."
            return "Recent hardware events: " + " | ".join(
                f"{event.get('device_name', 'device')} {event.get('status', 'changed')}"
                for event in events
            )
        if normalized in {
            "iot status",
            "smart home status",
            "iot devices",
            "list iot devices",
            "smart home devices",
            "smart home inventory",
            "iot inventory",
            "what iot devices are connected",
            "what smart devices are connected",
        }:
            return self.iot_summary()

        iot_knowledge = build_iot_knowledge_response(prompt)
        if iot_knowledge:
            return iot_knowledge
        return None

    def build_prompt_context(self, prompt: str) -> str | None:
        normalized = _normalize_match_text(prompt)
        if not normalized:
            return None
        iot_context = build_iot_prompt_context(prompt, self.get_iot_status())
        if iot_context:
            return iot_context
        if not any(
            token in normalized
            for token in (
                "device",
                "hardware",
                "usb",
                "camera",
                "webcam",
                "microphone",
                "mic",
                "storage",
                "disk",
                "drive",
                "vision",
                "voice",
                "iot",
                "wifi",
                "network",
            )
        ):
            return None

        status = self.get_status()
        capability_lines = [
            f"vision_enabled={status['capabilities'].get('vision_enabled', False)}",
            f"voice_enabled={status['capabilities'].get('voice_enabled', False)}",
            f"storage_ready={status['capabilities'].get('storage_ready', False)}",
            f"iot_detected={status['capabilities'].get('iot_detected', False)}",
        ]
        device_lines = []
        for item in status["devices"][:10]:
            parts = [f"name={item.get('name', 'device')}", f"type={item.get('type', 'unknown')}"]
            if item.get("status"):
                parts.append(f"status={item['status']}")
            if item.get("mountpoint"):
                parts.append(f"mount={item['mountpoint']}")
            device_lines.append(", ".join(parts))

        event_lines = [
            f"{event.get('status', 'changed')}: {event.get('device_name', 'device')} ({event.get('type', 'unknown')})"
            for event in status["recent_events"][:6]
        ]

        sections = [
            "Current local hardware status for the offline assistant.",
            "Capabilities: " + ", ".join(capability_lines),
        ]
        if device_lines:
            sections.append("Connected devices:\n- " + "\n- ".join(device_lines))
        if event_lines:
            sections.append("Recent hardware events:\n- " + "\n- ".join(event_lines))
        sections.append("Use this hardware context when answering the user.")
        return "\n\n".join(sections)

    def _monitor_loop(self) -> None:
        try:
            self.refresh(emit_events=False)
        except Exception:
            pass
        while not self._stop_event.wait(self._poll_interval_seconds()):
            try:
                self.refresh(emit_events=True)
            except Exception:
                continue
        with self._lock:
            self._monitoring = False

    def _ensure_initial_scan(self) -> None:
        if self._initial_scan_completed:
            return
        try:
            self.refresh(emit_events=False)
        except Exception:
            return

    def _save_state_locked(self) -> None:
        payload = {
            "updated_at": self._last_updated_at,
            "monitoring": self._monitoring,
            "devices": list(self._devices.values()),
            "events": self._events[-self._event_history_limit():],
            "capabilities": self._capabilities,
        }
        _safe_json_dump(self.state_path, payload)

    def _build_event(self, device: dict[str, Any], status: str, timestamp: str) -> dict[str, Any]:
        return {
            "device_id": device.get("id"),
            "device_name": device.get("name") or device.get("id") or "device",
            "type": device.get("type", "unknown"),
            "status": status,
            "timestamp": timestamp,
            "message": self._device_event_message(device, status),
        }

    def _announce_event(self, event: dict[str, Any]) -> None:
        if not self._speak_events_enabled() or not self._speaker:
            return
        message = _compact_text(event.get("message"))
        if not message:
            return
        try:
            self._speaker(message)
        except Exception:
            return

    def _device_event_message(self, device: dict[str, Any], status: str) -> str:
        device_type = device.get("type", "unknown")
        name = device.get("name") or "Device"
        if status == "connected":
            if device_type == "camera":
                return "Webcam connected, vision system ready."
            if device_type == "microphone":
                return "Microphone detected, voice mode enabled."
            if device_type == "storage":
                sample = (device.get("scan_summary") or {}).get("sample_entries") or []
                if sample:
                    return f"Storage connected, file scan ready. Sample items: {', '.join(sample[:3])}."
                return "Storage connected, file scan ready."
            if device_type in {"iot", "network"}:
                return f"Network device detected: {name}."
            if device_type == "usb":
                return f"USB device connected: {name}."
            return f"Device connected: {name}."

        if device_type == "camera":
            return "Webcam disconnected, vision system paused."
        if device_type == "microphone":
            return "Microphone disconnected, voice mode unavailable."
        if device_type == "storage":
            return "Storage device disconnected."
        if device_type in {"iot", "network"}:
            return f"Network device disconnected: {name}."
        if device_type == "usb":
            return f"USB device disconnected: {name}."
        return f"Device disconnected: {name}."

    def _build_capabilities(self, devices: dict[str, dict[str, Any]]) -> dict[str, Any]:
        type_counts: dict[str, int] = {}
        for item in devices.values():
            device_type = item.get("type", "unknown")
            type_counts[device_type] = type_counts.get(device_type, 0) + 1

        smart_home = summarize_iot_config()
        vision_enabled = type_counts.get("camera", 0) > 0
        voice_enabled = type_counts.get("microphone", 0) > 0
        storage_ready = type_counts.get("storage", 0) > 0
        iot_detected = (type_counts.get("iot", 0) + type_counts.get("network", 0)) > 0
        iot_control_ready = any(item.get("control_ready") for item in devices.values())

        summary_parts = []
        if vision_enabled:
            summary_parts.append("Vision ready")
        if voice_enabled:
            summary_parts.append("Voice ready")
        if storage_ready:
            summary_parts.append("Storage scan ready")
        if iot_detected:
            summary_parts.append("Network devices visible")
        if smart_home.get("configured"):
            summary_parts.append("Smart Home config loaded")
        if iot_control_ready:
            summary_parts.append("IoT control mappings available")
        if not summary_parts:
            summary_parts.append("No special hardware modules are active")

        return {
            "vision_enabled": vision_enabled,
            "voice_enabled": voice_enabled,
            "storage_ready": storage_ready,
            "iot_detected": iot_detected,
            "smart_home_configured": bool(smart_home.get("configured")),
            "smart_home_enabled": bool(smart_home.get("enabled")),
            "iot_control_ready": iot_control_ready,
            "connected_types": type_counts,
            "summary": ". ".join(summary_parts) + ".",
        }

    def _scan_devices(self) -> dict[str, dict[str, Any]]:
        scanned: dict[str, dict[str, Any]] = {}
        for bucket in (
            self._scan_storage_devices(),
            self._scan_camera_devices(),
            self._scan_microphone_devices(),
            self._scan_usb_devices(),
            self._scan_network_devices(),
        ):
            scanned.update(bucket)
        return scanned

    def _scan_storage_devices(self) -> dict[str, dict[str, Any]]:
        devices: dict[str, dict[str, Any]] = {}
        for partition in psutil.disk_partitions(all=False):
            mountpoint = _compact_text(getattr(partition, "mountpoint", ""))
            if not mountpoint or not os.path.exists(mountpoint):
                continue
            opts = _normalize_key(getattr(partition, "opts", ""))
            if "cdrom" in opts:
                continue

            usage = None
            try:
                usage = psutil.disk_usage(mountpoint)
            except Exception:
                usage = None

            device_id = f"storage:{mountpoint.lower()}"
            item = {
                "id": device_id,
                "name": _compact_text(getattr(partition, "device", "")) or f"Storage {mountpoint}",
                "type": "storage",
                "status": "connected",
                "source": "psutil",
                "mountpoint": mountpoint,
                "path": mountpoint,
                "filesystem": _compact_text(getattr(partition, "fstype", "")),
                "removable": "removable" in opts,
                "scan_summary": self._scan_storage_root(mountpoint),
                "updated_at": _utc_now(),
            }
            if usage is not None:
                item["total_bytes"] = int(usage.total)
                item["free_bytes"] = int(usage.free)
                item["used_percent"] = float(usage.percent)
            devices[device_id] = item
        return devices

    def _scan_storage_root(self, root_path: str) -> dict[str, Any]:
        sample_entries: list[str] = []
        file_count = 0
        folder_count = 0
        try:
            with os.scandir(root_path) as entries:
                for index, entry in enumerate(entries):
                    if entry.is_dir(follow_symlinks=False):
                        folder_count += 1
                    else:
                        file_count += 1
                    if len(sample_entries) < self._storage_scan_entry_limit():
                        sample_entries.append(entry.name)
                    if index >= (self._storage_scan_entry_limit() * 8):
                        break
        except Exception as error:
            return {
                "path": root_path,
                "file_count": 0,
                "folder_count": 0,
                "sample_entries": [],
                "error": _compact_text(error),
            }
        return {
            "path": root_path,
            "file_count": file_count,
            "folder_count": folder_count,
            "sample_entries": sample_entries,
        }

    def _scan_camera_devices(self) -> dict[str, dict[str, Any]]:
        now = time.time()
        if self._camera_cache and (now - self._last_camera_scan_at) < self._camera_probe_interval_seconds():
            return dict(self._camera_cache)

        devices: dict[str, dict[str, Any]] = {}
        if not _module_available("cv2"):
            self._camera_cache = {}
            self._last_camera_scan_at = now
            return devices

        import cv2

        try:
            if hasattr(cv2, "utils") and hasattr(cv2.utils, "logging"):
                cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
            elif hasattr(cv2, "setLogLevel") and hasattr(cv2, "LOG_LEVEL_ERROR"):
                cv2.setLogLevel(cv2.LOG_LEVEL_ERROR)
        except Exception:
            pass

        backend = getattr(cv2, "CAP_DSHOW", 0) if os.name == "nt" else 0
        for index in range(self._camera_probe_max_index() + 1):
            capture = None
            try:
                capture = cv2.VideoCapture(index, backend) if backend else cv2.VideoCapture(index)
                if not capture or not capture.isOpened():
                    continue
                width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                device_id = f"camera:{index}"
                devices[device_id] = {
                    "id": device_id,
                    "name": f"Webcam {index}",
                    "type": "camera",
                    "status": "connected",
                    "source": "opencv",
                    "index": index,
                    "resolution": f"{width}x{height}" if width and height else "",
                    "updated_at": _utc_now(),
                }
            except Exception:
                continue
            finally:
                if capture is not None:
                    capture.release()

        self._camera_cache = devices
        self._last_camera_scan_at = now
        return dict(devices)

    def _scan_microphone_devices(self) -> dict[str, dict[str, Any]]:
        devices: dict[str, dict[str, Any]] = {}
        if _module_available("sounddevice"):
            try:
                import sounddevice as sounddevice

                for index, info in enumerate(sounddevice.query_devices()):
                    max_input = int(info.get("max_input_channels") or 0)
                    if max_input <= 0:
                        continue
                    device_id = f"microphone:{index}"
                    devices[device_id] = {
                        "id": device_id,
                        "name": _compact_text(info.get("name")) or f"Microphone {index}",
                        "type": "microphone",
                        "status": "connected",
                        "source": "sounddevice",
                        "index": index,
                        "max_input_channels": max_input,
                        "default_samplerate": float(info.get("default_samplerate") or 0.0),
                        "updated_at": _utc_now(),
                    }
                return devices
            except Exception:
                devices = {}

        if _module_available("pyaudio"):
            try:
                import pyaudio

                audio = pyaudio.PyAudio()
                try:
                    for index in range(audio.get_device_count()):
                        info = audio.get_device_info_by_index(index)
                        max_input = int(info.get("maxInputChannels") or 0)
                        if max_input <= 0:
                            continue
                        device_id = f"microphone:{index}"
                        devices[device_id] = {
                            "id": device_id,
                            "name": _compact_text(info.get("name")) or f"Microphone {index}",
                            "type": "microphone",
                            "status": "connected",
                            "source": "pyaudio",
                            "index": index,
                            "max_input_channels": max_input,
                            "default_samplerate": float(info.get("defaultSampleRate") or 0.0),
                            "updated_at": _utc_now(),
                        }
                finally:
                    audio.terminate()
            except Exception:
                return {}

        return devices

    def _scan_usb_devices(self) -> dict[str, dict[str, Any]]:
        if os.name == "nt" and _module_available("wmi"):
            return self._scan_usb_devices_windows()
        if _module_available("pyudev"):
            return self._scan_usb_devices_pyudev()
        return {}

    def _scan_usb_devices_windows(self) -> dict[str, dict[str, Any]]:
        devices: dict[str, dict[str, Any]] = {}
        try:
            import wmi

            client = wmi.WMI()
            for entity in client.Win32_PnPEntity():
                pnp_id = _compact_text(getattr(entity, "PNPDeviceID", ""))
                if not pnp_id.upper().startswith("USB"):
                    continue
                name = _compact_text(getattr(entity, "Name", "")) or _compact_text(getattr(entity, "Caption", "")) or pnp_id
                lower_name = name.lower()
                if any(keyword in lower_name for keyword in _USB_SKIP_KEYWORDS):
                    continue
                device_type = self._classify_device_type(name, fallback="usb")
                if device_type in {"camera", "microphone", "storage"}:
                    continue
                device_id = f"usb:{pnp_id.lower()}"
                devices[device_id] = {
                    "id": device_id,
                    "name": name,
                    "type": device_type,
                    "status": "connected",
                    "source": "wmi",
                    "pnp_device_id": pnp_id,
                    "manufacturer": _compact_text(getattr(entity, "Manufacturer", "")),
                    "updated_at": _utc_now(),
                }
        except Exception:
            return {}
        return devices

    def _scan_usb_devices_pyudev(self) -> dict[str, dict[str, Any]]:
        devices: dict[str, dict[str, Any]] = {}
        try:
            import pyudev

            context = pyudev.Context()
            for device in context.list_devices(subsystem="usb", DEVTYPE="usb_device"):
                model = _compact_text(device.get("ID_MODEL_FROM_DATABASE")) or _compact_text(device.get("ID_MODEL")) or "USB device"
                serial = _compact_text(device.get("ID_SERIAL_SHORT")) or _compact_text(device.device_node) or model
                device_type = self._classify_device_type(model, fallback="usb")
                if device_type in {"camera", "microphone", "storage"}:
                    continue
                device_id = f"usb:{_normalize_key(serial or model)}"
                devices[device_id] = {
                    "id": device_id,
                    "name": model,
                    "type": device_type,
                    "status": "connected",
                    "source": "pyudev",
                    "vendor": _compact_text(device.get("ID_VENDOR_FROM_DATABASE")) or _compact_text(device.get("ID_VENDOR")),
                    "serial": serial,
                    "updated_at": _utc_now(),
                }
        except Exception:
            return {}
        return devices

    def _scan_network_devices(self) -> dict[str, dict[str, Any]]:
        if not self._network_scan_enabled():
            return {}

        now = time.time()
        if self._network_cache and (now - self._last_network_scan_at) < self._network_scan_interval_seconds():
            return dict(self._network_cache)

        devices: dict[str, dict[str, Any]] = {}
        local_ips = _local_ip_addresses()
        smart_home = summarize_iot_config()
        configured_devices = smart_home.get("devices") or []
        lookup_budget = self._network_name_lookup_limit()

        try:
            result = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                text=True,
                timeout=6,
                check=False,
            )
            output = result.stdout or ""
        except Exception:
            output = ""

        for line in output.splitlines():
            match = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
            if not match:
                continue
            ip_address = match.group(1)
            if ip_address in local_ips:
                continue
            try:
                ipaddress.ip_address(ip_address)
            except ValueError:
                continue

            mac_match = re.search(r"([0-9a-f]{2}(?:-[0-9a-f]{2}){5})", line.lower())
            mac_address = mac_match.group(1) if mac_match else ""
            hostname = ""
            if self._network_name_lookup_enabled() and lookup_budget > 0:
                hostname = self._resolve_network_name(ip_address)
                if hostname:
                    lookup_budget -= 1

            label = hostname or f"Network device {ip_address}"
            device_type = "network"
            lowered_line = line.lower()
            if any(keyword in lowered_line for keyword in _SMART_DEVICE_KEYWORDS) or any(
                keyword in _normalize_key(hostname) for keyword in _SMART_DEVICE_KEYWORDS
            ):
                device_type = "iot"
                label = hostname or f"Smart device {ip_address}"

            profile = infer_iot_profile(label, context=f"{line} {hostname}", fallback=device_type)
            matched_config = match_configured_iot_device(f"{label} {hostname}", configured_devices)
            control_ready = bool(
                matched_config
                and smart_home.get("enabled")
                and not matched_config.get("placeholder_commands")
            )
            device_id = f"{device_type}:{ip_address}"
            devices[device_id] = {
                "id": device_id,
                "name": label,
                "type": device_type,
                "status": "connected",
                "source": "arp",
                "ip_address": ip_address,
                "mac_address": mac_address,
                "hostname": hostname,
                "iot_profile": profile,
                "control_ready": control_ready,
                "matched_configured_device": matched_config.get("name") if matched_config else "",
                "available_commands": list((matched_config or {}).get("commands") or [])[:4],
                "updated_at": _utc_now(),
            }

        self._network_cache = devices
        self._last_network_scan_at = now
        return dict(devices)

    def _resolve_network_name(self, ip_address: str) -> str:
        cached = _compact_text(self._network_name_cache.get(ip_address))
        if cached:
            return cached

        hostname = ""
        try:
            resolved = socket.getfqdn(ip_address)
            if resolved and resolved != ip_address:
                hostname = _compact_text(resolved.split(".")[0])
        except Exception:
            hostname = ""

        if not hostname and os.name == "nt":
            try:
                result = subprocess.run(
                    ["ping", "-a", "-n", "1", "-w", "350", ip_address],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    check=False,
                )
                first_line = _compact_text((result.stdout or "").splitlines()[0] if result.stdout else "")
                match = re.search(r"Pinging\s+(.+?)\s+\[", first_line, flags=re.IGNORECASE)
                if match:
                    hostname = _compact_text(match.group(1)).split(".")[0]
            except Exception:
                hostname = ""

        if hostname:
            self._network_name_cache[ip_address] = hostname
        return hostname

    def _classify_device_type(self, name: str, fallback: str = "unknown") -> str:
        lowered = _normalize_match_text(name)
        if any(token in lowered for token in ("camera", "webcam", "uvc")):
            return "camera"
        if any(token in lowered for token in ("microphone", "mic", "audio input", "usb audio")):
            return "microphone"
        if any(token in lowered for token in ("storage", "disk", "flash", "ssd", "hdd", "card reader", "mass storage")):
            return "storage"
        if any(token in lowered for token in _SMART_DEVICE_KEYWORDS):
            return "iot"
        if "usb" in lowered:
            return "usb"
        return fallback


DEVICE_MANAGER = DeviceManager()
