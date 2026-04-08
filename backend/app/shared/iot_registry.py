import json
import os
import re
import socket
from typing import Any

import requests

from utils.paths import config_path

IOT_CREDENTIALS_PATH = config_path("iot_credentials.json")

_STOPWORDS = {
    "the",
    "a",
    "an",
    "my",
    "your",
    "device",
    "smart",
    "home",
    "room",
    "turn",
    "switch",
    "on",
    "off",
    "toggle",
    "activate",
    "deactivate",
    "start",
    "stop",
}

_VENDOR_HINTS = {
    "alexa": "Amazon",
    "echo": "Amazon",
    "firetv": "Amazon",
    "fire tv": "Amazon",
    "nest": "Google",
    "google": "Google",
    "chromecast": "Google",
    "hue": "Philips Hue",
    "wiz": "WiZ",
    "tuya": "Tuya Smart",
    "sonoff": "Sonoff",
    "shelly": "Shelly",
    "ring": "Ring",
    "roku": "Roku",
    "tasmota": "Tasmota",
    "esp32": "Espressif",
    "esp8266": "Espressif",
}

_DEVICE_PATTERNS = [
    {
        "category": "smart-speaker",
        "tokens": ("alexa", "echo", "google home", "nest mini", "nest audio", "homepod"),
        "protocols": ["wifi", "bluetooth"],
        "usage": "voice assistant and speaker automation",
    },
    {
        "category": "streaming-device",
        "tokens": ("chromecast", "roku", "fire tv", "google tv", "apple tv"),
        "protocols": ["wifi"],
        "usage": "media streaming and casting",
    },
    {
        "category": "camera",
        "tokens": ("ring", "arlo", "blink", "reolink", "camera", "doorbell"),
        "protocols": ["wifi"],
        "usage": "video monitoring and security",
    },
    {
        "category": "light",
        "tokens": ("hue", "bulb", "light", "lamp", "wiz"),
        "protocols": ["zigbee", "wifi", "matter"],
        "usage": "lighting automation",
    },
    {
        "category": "plug-switch",
        "tokens": ("plug", "switch", "relay", "sonoff", "shelly", "tuya"),
        "protocols": ["wifi", "zigbee", "matter"],
        "usage": "power and switching control",
    },
    {
        "category": "climate",
        "tokens": ("thermostat", "ac", "air conditioner", "hvac"),
        "protocols": ["wifi", "matter"],
        "usage": "temperature and climate control",
    },
    {
        "category": "sensor",
        "tokens": ("sensor", "motion", "contact", "door", "temp", "temperature", "humidity", "leak"),
        "protocols": ["zigbee", "z-wave", "thread", "bluetooth"],
        "usage": "environment and occupancy sensing",
    },
    {
        "category": "hub",
        "tokens": ("hub", "bridge", "gateway", "coordinator"),
        "protocols": ["ethernet", "wifi", "zigbee", "z-wave", "thread"],
        "usage": "smart-home device coordination",
    },
    {
        "category": "microcontroller",
        "tokens": ("esp32", "esp8266", "tasmota", "arduino", "microcontroller"),
        "protocols": ["wifi", "mqtt"],
        "usage": "custom IoT automation and sensors",
    },
]

_IOT_KNOWLEDGE = {
    "iot": {
        "title": "IoT",
        "summary": "IoT means internet-connected sensors, switches, cameras, appliances, and controllers that can share data or be automated locally.",
        "best_for": "monitoring, automation, notifications, and remote or local control",
        "watchouts": "security, device isolation, firmware updates, and avoiding cloud-only lock-in",
    },
    "matter": {
        "title": "Matter",
        "summary": "Matter is a modern smart-home interoperability standard designed to let devices from different brands work together with local-first control.",
        "best_for": "cross-brand smart-home setups and long-term compatibility",
        "watchouts": "real-world support still varies by brand and device generation",
    },
    "thread": {
        "title": "Thread",
        "summary": "Thread is a low-power IPv6 mesh network used by many newer smart-home devices, especially Matter sensors and accessories.",
        "best_for": "battery-powered sensors and reliable mesh networking",
        "watchouts": "it needs a compatible border router for the rest of the network to reach Thread devices",
    },
    "zigbee": {
        "title": "Zigbee",
        "summary": "Zigbee is a low-power mesh protocol popular for bulbs, switches, plugs, and sensors.",
        "best_for": "large sensor networks and lighting automation",
        "watchouts": "it usually needs a coordinator or hub and can see interference near busy 2.4 GHz Wi-Fi channels",
    },
    "zwave": {
        "title": "Z-Wave",
        "summary": "Z-Wave is a low-power smart-home mesh protocol that typically uses sub-GHz radio for good range and reliability.",
        "best_for": "locks, sensors, switches, and stable home automation",
        "watchouts": "regional radio differences mean devices and hubs must match your country frequency",
    },
    "mqtt": {
        "title": "MQTT",
        "summary": "MQTT is a lightweight publish-subscribe messaging protocol widely used by custom IoT devices and local automation systems.",
        "best_for": "ESP32 projects, sensors, local automation, and event pipelines",
        "watchouts": "you need a broker and topic design; security depends on your local setup",
    },
    "wifi": {
        "title": "Wi-Fi IoT",
        "summary": "Wi-Fi IoT devices connect directly to your router and are easy to set up for cameras, speakers, TVs, and smart plugs.",
        "best_for": "high-bandwidth devices and quick setup without a hub",
        "watchouts": "battery life is weaker than Zigbee or Thread, and cheap cloud devices can be noisy or insecure",
    },
    "bluetooth": {
        "title": "Bluetooth and BLE",
        "summary": "Bluetooth Low Energy is useful for short-range sensors, beacons, and onboarding nearby smart devices.",
        "best_for": "presence, wearable, and low-power local interactions",
        "watchouts": "range is shorter than Wi-Fi and many setups need a gateway for whole-home visibility",
    },
    "home_assistant": {
        "title": "Home Assistant",
        "summary": "Home Assistant is a local automation platform that unifies smart-home devices, dashboards, and automations across many protocols.",
        "best_for": "offline-first control, dashboards, rules, and privacy-focused smart homes",
        "watchouts": "initial setup takes time, and some cloud devices still need vendor-specific integrations",
    },
    "esp32": {
        "title": "ESP32",
        "summary": "ESP32 is a popular microcontroller for custom IoT projects with Wi-Fi, Bluetooth, sensors, relays, and MQTT-based automation.",
        "best_for": "DIY sensors, displays, controllers, and local prototypes",
        "watchouts": "device security, OTA updates, and power design matter for reliable deployments",
    },
}

_TOPIC_ALIASES = {
    "smart home": "iot",
    "smart-home": "iot",
    "internet of things": "iot",
    "matter": "matter",
    "thread": "thread",
    "zigbee": "zigbee",
    "zig bee": "zigbee",
    "z-wave": "zwave",
    "z wave": "zwave",
    "zwave": "zwave",
    "mqtt": "mqtt",
    "wi fi": "wifi",
    "wifi": "wifi",
    "bluetooth": "bluetooth",
    "ble": "bluetooth",
    "bluetooth low energy": "bluetooth",
    "home assistant": "home_assistant",
    "esp32": "esp32",
    "esp 32": "esp32",
    "esp8266": "esp32",
    "esp 8266": "esp32",
    "tasmota": "esp32",
}


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _compact_text(value).lower()).strip()


def _load_json(path: str) -> dict[str, Any] | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _meaningful_tokens(value: str) -> set[str]:
    return {
        token
        for token in _normalize_text(value).split()
        if token and token not in _STOPWORDS and len(token) > 1
    }


def _placeholder_url(url: str) -> bool:
    normalized = _compact_text(url)
    return "YOUR_KEY_HERE" in normalized or "YOUR_HOME_ASSISTANT_WEBHOOK_ID" in normalized


def load_iot_credentials() -> dict[str, Any] | None:
    return _load_json(IOT_CREDENTIALS_PATH)


def summarize_iot_config() -> dict[str, Any]:
    creds = load_iot_credentials()
    if not creds:
        return {
            "configured": False,
            "enabled": False,
            "command_count": 0,
            "device_count": 0,
            "placeholder_count": 0,
            "sample_commands": [],
            "devices": [],
            "summary": "Smart Home is not configured yet.",
        }

    webhooks = creds.get("webhooks") or {}
    devices: dict[str, dict[str, Any]] = {}
    placeholder_count = 0
    for raw_command, config in webhooks.items():
        command = _compact_text(raw_command)
        if not command:
            continue
        url = str((config or {}).get("url") or "")
        if _placeholder_url(url):
            placeholder_count += 1

        device_name = command
        for prefix in (
            "turn on ",
            "turn off ",
            "switch on ",
            "switch off ",
            "toggle ",
            "start ",
            "stop ",
            "open ",
            "close ",
            "activate ",
            "deactivate ",
        ):
            if device_name.lower().startswith(prefix):
                device_name = device_name[len(prefix):]
                break
        device_name = _compact_text(device_name) or command
        device_key = _normalize_text(device_name)
        device = devices.setdefault(
            device_key,
            {
                "name": device_name,
                "commands": [],
                "placeholder_commands": 0,
            },
        )
        device["commands"].append(command)
        if _placeholder_url(url):
            device["placeholder_commands"] += 1

    enabled = bool(creds.get("enabled"))
    device_list = sorted(devices.values(), key=lambda item: item["name"].lower())
    sample_commands = sorted(webhooks.keys())[:4]
    summary_parts = [
        f"Smart Home is {'enabled' if enabled else 'disabled'} with {len(webhooks)} configured command(s)."
    ]
    if device_list:
        sample_names = ", ".join(item["name"] for item in device_list[:4])
        summary_parts.append(f"Configured devices include {sample_names}.")
    if placeholder_count:
        summary_parts.append(f"{placeholder_count} command(s) still use placeholder URLs or keys.")

    return {
        "configured": True,
        "enabled": enabled,
        "command_count": len(webhooks),
        "device_count": len(device_list),
        "placeholder_count": placeholder_count,
        "sample_commands": sample_commands,
        "devices": device_list,
        "summary": " ".join(summary_parts),
    }


def validate_iot_config(*, test_connectivity: bool = False, timeout_seconds: float = 2.0) -> dict[str, Any]:
    creds = load_iot_credentials()
    if not creds:
        return {
            "ok": False,
            "configured": False,
            "enabled": False,
            "summary": "Smart Home credentials file is missing.",
            "checks": [
                {
                    "key": "credentials_file",
                    "status": "error",
                    "detail": f"Add {IOT_CREDENTIALS_PATH} to enable local IoT control.",
                }
            ],
        }

    webhooks = creds.get("webhooks") if isinstance(creds.get("webhooks"), dict) else {}
    ha_config = creds.get("home_assistant") if isinstance(creds.get("home_assistant"), dict) else {}
    mqtt_config = creds.get("mqtt") if isinstance(creds.get("mqtt"), dict) else {}
    enabled = bool(creds.get("enabled"))

    checks: list[dict[str, Any]] = []

    if webhooks:
        checks.append(
            {
                "key": "commands",
                "status": "ok",
                "detail": f"{len(webhooks)} Smart Home command(s) are configured.",
            }
        )
    else:
        checks.append(
            {
                "key": "commands",
                "status": "warning",
                "detail": "No Smart Home commands are configured yet.",
            }
        )

    placeholder_count = 0
    integration_counts = {"webhook": 0, "home_assistant_service": 0, "mqtt": 0, "unknown": 0}
    for raw_name, entry in webhooks.items():
        config = entry if isinstance(entry, dict) else {}
        integration = _compact_text(config.get("type") or "webhook").lower() or "webhook"
        if integration not in integration_counts:
            integration = "unknown"
        integration_counts[integration] += 1

        url = _compact_text(config.get("url"))
        if _placeholder_url(url):
            placeholder_count += 1
            checks.append(
                {
                    "key": f"placeholder:{raw_name}",
                    "status": "warning",
                    "detail": f"{raw_name} still uses a placeholder URL or key.",
                }
            )

        if integration == "webhook" and not url:
            checks.append(
                {
                    "key": f"webhook_url:{raw_name}",
                    "status": "error",
                    "detail": f"{raw_name} is missing its webhook URL.",
                }
            )

        if integration == "home_assistant_service":
            if not _compact_text(config.get("service")):
                checks.append(
                    {
                        "key": f"ha_service:{raw_name}",
                        "status": "error",
                        "detail": f"{raw_name} is missing its Home Assistant service name.",
                    }
                )
            if not _compact_text(config.get("entity_id")):
                checks.append(
                    {
                        "key": f"ha_entity:{raw_name}",
                        "status": "error",
                        "detail": f"{raw_name} is missing its Home Assistant entity_id.",
                    }
                )

        if integration == "mqtt" and not _compact_text(config.get("topic")):
            checks.append(
                {
                    "key": f"mqtt_topic:{raw_name}",
                    "status": "error",
                    "detail": f"{raw_name} is missing its MQTT topic.",
                }
            )

    if integration_counts["home_assistant_service"]:
        ha_base = _compact_text(ha_config.get("base_url"))
        ha_token = _compact_text(ha_config.get("token"))
        if not ha_base:
            checks.append(
                {
                    "key": "home_assistant_base_url",
                    "status": "error",
                    "detail": "Home Assistant base_url is missing.",
                }
            )
        elif "PASTE_LONG_LIVED_ACCESS_TOKEN_HERE" in ha_token or not ha_token:
            checks.append(
                {
                    "key": "home_assistant_token",
                    "status": "warning",
                    "detail": "Home Assistant token still looks like a placeholder or is empty.",
                }
            )
        else:
            checks.append(
                {
                    "key": "home_assistant_auth",
                    "status": "ok",
                    "detail": "Home Assistant base_url and token are present.",
                }
            )

        if test_connectivity and ha_base and ha_token and "PASTE_LONG_LIVED_ACCESS_TOKEN_HERE" not in ha_token:
            try:
                response = requests.get(
                    ha_base.rstrip("/") + "/api/",
                    headers={"Authorization": f"Bearer {ha_token}"},
                    timeout=timeout_seconds,
                )
                status = "ok" if response.ok else "warning"
                checks.append(
                    {
                        "key": "home_assistant_connectivity",
                        "status": status,
                        "detail": f"Home Assistant connectivity check returned HTTP {response.status_code}.",
                    }
                )
            except requests.RequestException as error:
                checks.append(
                    {
                        "key": "home_assistant_connectivity",
                        "status": "warning",
                        "detail": f"Could not reach Home Assistant: {error}",
                    }
                )

    if integration_counts["mqtt"]:
        mqtt_host = _compact_text(mqtt_config.get("host"))
        mqtt_port = int(mqtt_config.get("port") or 1883)
        if not mqtt_host:
            checks.append(
                {
                    "key": "mqtt_host",
                    "status": "error",
                    "detail": "MQTT host is missing.",
                }
            )
        else:
            checks.append(
                {
                    "key": "mqtt_host",
                    "status": "ok",
                    "detail": f"MQTT broker target is {mqtt_host}:{mqtt_port}.",
                }
            )

        if test_connectivity and mqtt_host:
            try:
                with socket.create_connection((mqtt_host, mqtt_port), timeout=timeout_seconds):
                    pass
                checks.append(
                    {
                        "key": "mqtt_connectivity",
                        "status": "ok",
                        "detail": f"MQTT broker accepted a TCP connection on {mqtt_host}:{mqtt_port}.",
                    }
                )
            except OSError as error:
                checks.append(
                    {
                        "key": "mqtt_connectivity",
                        "status": "warning",
                        "detail": f"Could not connect to MQTT broker at {mqtt_host}:{mqtt_port}: {error}",
                    }
                )

    if enabled:
        checks.append(
            {
                "key": "enabled",
                "status": "ok",
                "detail": "Smart Home control is enabled.",
            }
        )
    else:
        checks.append(
            {
                "key": "enabled",
                "status": "warning",
                "detail": "Smart Home control is still disabled.",
            }
        )

    error_count = sum(1 for item in checks if item["status"] == "error")
    warning_count = sum(1 for item in checks if item["status"] == "warning")
    ok_count = sum(1 for item in checks if item["status"] == "ok")
    summary = (
        f"IoT config validation found {ok_count} ready, {warning_count} warning, and {error_count} error check(s)."
    )
    return {
        "ok": error_count == 0,
        "configured": True,
        "enabled": enabled,
        "summary": summary,
        "integration_counts": integration_counts,
        "placeholder_count": placeholder_count,
        "checks": checks,
    }


def infer_iot_profile(name: str, *, context: str = "", fallback: str = "iot") -> dict[str, Any]:
    text = _normalize_text(f"{name} {context}")
    vendor_hint = ""
    for token, vendor in _VENDOR_HINTS.items():
        if token in text:
            vendor_hint = vendor
            break

    for profile in _DEVICE_PATTERNS:
        if any(token in text for token in profile["tokens"]):
            return {
                "category": profile["category"],
                "protocol_hints": list(profile["protocols"]),
                "likely_use": profile["usage"],
                "vendor_hint": vendor_hint,
                "confidence": "high",
                "smart_candidate": True,
            }

    if any(token in text for token in ("smart", "iot", "wifi", "lan", "network")):
        return {
            "category": "smart-device",
            "protocol_hints": ["wifi"],
            "likely_use": "general smart-home or network automation",
            "vendor_hint": vendor_hint,
            "confidence": "medium",
            "smart_candidate": fallback == "iot",
        }

    return {
        "category": fallback,
        "protocol_hints": [],
        "likely_use": "general network presence",
        "vendor_hint": vendor_hint,
        "confidence": "low",
        "smart_candidate": fallback == "iot",
    }


def match_configured_iot_device(device_name: str, configured_devices: list[dict[str, Any]]) -> dict[str, Any] | None:
    device_tokens = _meaningful_tokens(device_name)
    if not device_tokens:
        return None

    best_match = None
    best_score = 0
    for configured in configured_devices:
        configured_tokens = _meaningful_tokens(configured.get("name", ""))
        score = len(device_tokens & configured_tokens)
        if score > best_score:
            best_match = configured
            best_score = score

    if best_match and best_score >= 2:
        return best_match
    return None


def _detect_iot_topics(prompt: str) -> list[str]:
    normalized = _normalize_text(prompt)
    topics = []
    for alias, topic in _TOPIC_ALIASES.items():
        if alias in normalized and topic not in topics:
            topics.append(topic)
    return topics


def iot_knowledge_topics() -> list[str]:
    return [payload["title"] for payload in _IOT_KNOWLEDGE.values()]


def build_iot_knowledge_response(prompt: str) -> str | None:
    normalized = _normalize_text(prompt)
    topics = _detect_iot_topics(prompt)
    if not topics:
        return None

    explanatory_intent = any(
        phrase in normalized
        for phrase in (
            "what is",
            "explain",
            "tell me about",
            "how does",
            "how do",
            "difference",
            "compare",
            "versus",
            " vs ",
        )
    ) or normalized in set(_TOPIC_ALIASES.values())

    if not explanatory_intent:
        return None

    if len(topics) >= 2 and any(token in normalized for token in ("difference", "compare", "versus", "vs")):
        left = _IOT_KNOWLEDGE[topics[0]]
        right = _IOT_KNOWLEDGE[topics[1]]
        return (
            f"{left['title']} vs {right['title']}: {left['summary']} "
            f"{right['summary']} "
            f"Choose {left['title']} when you want {left['best_for']}, and choose {right['title']} when you want {right['best_for']}."
        )

    topic = topics[0]
    entry = _IOT_KNOWLEDGE.get(topic)
    if not entry:
        return None
    return (
        f"{entry['title']}: {entry['summary']} Best for {entry['best_for']}. "
        f"Main watch-out: {entry['watchouts']}."
    )


def build_iot_prompt_context(prompt: str, iot_status: dict[str, Any]) -> str | None:
    normalized = _normalize_text(prompt)
    if not any(token in normalized for token in ("iot", "smart home", "matter", "thread", "zigbee", "z wave", "zwave", "mqtt", "home assistant", "sensor", "automation", "protocol")):
        return None

    discovered_devices = iot_status.get("discovered_devices") or []
    configured_devices = iot_status.get("configured", {}).get("devices") or []
    sections = [
        "Current offline smart-home context.",
        f"Configured smart-home summary: {iot_status.get('configured', {}).get('summary', 'Not configured.')}",
        f"Discovered IoT summary: {iot_status.get('summary', 'No smart-home summary available.')}",
    ]

    if discovered_devices:
        lines = []
        for item in discovered_devices[:8]:
            profile = item.get("iot_profile") or {}
            parts = [
                f"name={item.get('name', 'device')}",
                f"category={profile.get('category', item.get('type', 'iot'))}",
            ]
            if item.get("ip_address"):
                parts.append(f"ip={item['ip_address']}")
            if profile.get("protocol_hints"):
                parts.append("protocols=" + "/".join(profile["protocol_hints"][:3]))
            lines.append(", ".join(parts))
        sections.append("Discovered smart or network devices:\n- " + "\n- ".join(lines))

    if configured_devices:
        sections.append(
            "Configured smart-home command devices:\n- "
            + "\n- ".join(
                f"{item.get('name', 'device')} ({len(item.get('commands') or [])} command(s))"
                for item in configured_devices[:8]
            )
        )

    sections.append(
        "IoT knowledge topics supported locally: " + ", ".join(iot_knowledge_topics()[:8]) + "."
    )
    sections.append("Use this smart-home context only when it helps answer the user's question.")
    return "\n\n".join(sections)
