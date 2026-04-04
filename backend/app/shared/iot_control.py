import importlib.util
import json
import os
import time
from typing import Any

import requests

from iot_registry import load_iot_credentials
from utils.config import get_setting


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BACKEND_DATA_DIR = os.path.join(PROJECT_ROOT, "backend", "data")
IOT_ACTION_HISTORY_PATH = os.path.join(BACKEND_DATA_DIR, "iot_action_history.json")

_ACTION_PREFIXES = (
    ("turn on ", "turn_on"),
    ("switch on ", "turn_on"),
    ("turn off ", "turn_off"),
    ("switch off ", "turn_off"),
    ("toggle ", "toggle"),
    ("open ", "open"),
    ("close ", "close"),
    ("lock ", "lock"),
    ("unlock ", "unlock"),
    ("start ", "start"),
    ("stop ", "stop"),
    ("activate ", "activate"),
    ("deactivate ", "deactivate"),
    ("enable ", "enable"),
    ("disable ", "disable"),
    ("arm ", "arm"),
    ("disarm ", "disarm"),
)
_HIGH_RISK_ACTIONS = {"unlock", "disarm", "open", "disable"}
_MEDIUM_RISK_ACTIONS = {"turn_off", "stop", "close", "lock", "arm", "deactivate"}
_RISKY_TARGET_KEYWORDS = ("door", "garage", "gate", "alarm", "security", "lock", "camera")


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_text(value: Any) -> str:
    return "".join(
        character.lower() if character.isalnum() else " "
        for character in _compact_text(value)
    ).strip()


def _meaningful_tokens(value: str) -> set[str]:
    stopwords = {
        "the",
        "a",
        "an",
        "my",
        "your",
        "to",
        "for",
        "smart",
        "home",
        "device",
    }
    return {token for token in _normalize_text(value).split() if token and token not in stopwords}


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_json_load(path: str) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


def _safe_json_dump(path: str, payload: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False)
    os.replace(temp_path, path)


def _history_limit() -> int:
    try:
        return max(10, int(get_setting("iot.action_history_limit", 40) or 40))
    except Exception:
        return 40


def _fuzzy_matching_enabled() -> bool:
    return bool(get_setting("iot.allow_fuzzy_command_matching", True))


def _confirmation_mode() -> str:
    value = str(get_setting("iot.confirmation_mode", "risky_only") or "risky_only").strip().lower()
    if value not in {"off", "risky_only", "all"}:
        return "risky_only"
    return value


def _extract_action_target(command_text: str) -> tuple[str, str]:
    normalized = _normalize_text(command_text)
    for prefix, action in _ACTION_PREFIXES:
        prefix_key = prefix.strip()
        if normalized.startswith(prefix_key + " "):
            return action, _compact_text(normalized[len(prefix_key):]).strip()
        if f" {prefix_key} " in f" {normalized} ":
            before, _separator, after = normalized.partition(prefix_key + " ")
            target = _compact_text(after)
            if target:
                return action, target
    return "", normalized


def _device_name_from_command(command_text: str) -> str:
    normalized = _compact_text(command_text)
    lowered = normalized.lower()
    for prefix, _action in _ACTION_PREFIXES:
        if lowered.startswith(prefix):
            return _compact_text(normalized[len(prefix):]) or normalized
    return normalized


def _integration_type(config: dict[str, Any]) -> str:
    explicit = _compact_text(config.get("type") or config.get("transport")).lower()
    if explicit in {"mqtt", "home_assistant_service", "home-assistant-service", "webhook"}:
        return explicit.replace("-", "_")
    if config.get("service") or config.get("entity_id"):
        return "home_assistant_service"
    if config.get("topic"):
        return "mqtt"
    if config.get("url"):
        return "webhook"
    return "unknown"


def _build_command_catalog(credentials: dict[str, Any]) -> list[dict[str, Any]]:
    catalog = []
    webhooks = credentials.get("webhooks") or {}
    for raw_command, raw_config in webhooks.items():
        command = _compact_text(raw_command)
        if not command:
            continue
        config = raw_config if isinstance(raw_config, dict) else {}
        action, _target = _extract_action_target(command)
        device_name = _device_name_from_command(command)
        catalog.append(
            {
                "command": command,
                "normalized_command": _normalize_text(command),
                "action": action,
                "device_name": device_name,
                "device_tokens": _meaningful_tokens(device_name),
                "command_tokens": _meaningful_tokens(command),
                "config": config,
                "integration_type": _integration_type(config),
            }
        )
    return catalog


def _risk_level(command_text: str, config: dict[str, Any]) -> str:
    explicit = _compact_text(config.get("risk_level")).lower()
    if explicit in {"low", "medium", "high"}:
        return explicit

    action, target = _extract_action_target(command_text)
    target_text = _normalize_text(target)
    if action in _HIGH_RISK_ACTIONS:
        return "high"
    if any(token in target_text for token in _RISKY_TARGET_KEYWORDS):
        return "high" if action in {"open", "unlock", "disable", "disarm"} else "medium"
    if action in _MEDIUM_RISK_ACTIONS:
        return "medium"
    return "low"


def _requires_confirmation(command_text: str, config: dict[str, Any]) -> bool:
    if "requires_confirmation" in config:
        return bool(config.get("requires_confirmation"))

    mode = _confirmation_mode()
    if mode == "off":
        return False
    if mode == "all":
        return True
    return _risk_level(command_text, config) in {"medium", "high"}


def _resolution_payload(
    *,
    handled: bool,
    matched: bool,
    command_text: str,
    message: str,
    candidate_commands: list[str] | None = None,
    catalog_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "handled": handled,
        "matched": matched,
        "input": _compact_text(command_text),
        "message": message,
        "candidate_commands": candidate_commands or [],
    }
    if catalog_entry:
        payload.update(
            {
                "matched_command": catalog_entry["command"],
                "device_name": catalog_entry["device_name"],
                "integration_type": catalog_entry["integration_type"],
                "risk_level": _risk_level(catalog_entry["command"], catalog_entry["config"]),
                "requires_confirmation": _requires_confirmation(catalog_entry["command"], catalog_entry["config"]),
                "match_type": catalog_entry.get("match_type", "exact"),
            }
        )
    else:
        payload.update(
            {
                "matched_command": "",
                "device_name": "",
                "integration_type": "",
                "risk_level": "low",
                "requires_confirmation": False,
                "match_type": "",
            }
        )
    return payload


def resolve_iot_control_command(command_text: str) -> dict[str, Any]:
    text = _compact_text(command_text)
    if not text:
        return _resolution_payload(
            handled=False,
            matched=False,
            command_text=command_text,
            message="No IoT command was provided.",
        )

    credentials = load_iot_credentials()
    action, target = _extract_action_target(text)
    looks_like_iot_action = bool(action)
    if not credentials:
        return _resolution_payload(
            handled=looks_like_iot_action,
            matched=False,
            command_text=text,
            message="IoT config file is missing.",
        )

    catalog = _build_command_catalog(credentials)
    if not catalog:
        return _resolution_payload(
            handled=looks_like_iot_action,
            matched=False,
            command_text=text,
            message="No Smart Home devices are configured.",
        )

    normalized = _normalize_text(text)
    for entry in catalog:
        if normalized == entry["normalized_command"]:
            exact = dict(entry)
            exact["match_type"] = "exact"
            message = f"Resolved {text} to {entry['command']}."
            return _resolution_payload(
                handled=True,
                matched=True,
                command_text=text,
                message=message,
                catalog_entry=exact,
            )

    if not looks_like_iot_action or not _fuzzy_matching_enabled():
        return _resolution_payload(
            handled=False,
            matched=False,
            command_text=text,
            message="No configured IoT command matched this request.",
            candidate_commands=[entry["command"] for entry in catalog[:5]],
        )

    input_tokens = _meaningful_tokens(text)
    target_tokens = _meaningful_tokens(target)
    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in catalog:
        score = 0
        if action and entry["action"] == action:
            score += 5
        score += len(input_tokens & entry["command_tokens"]) * 2
        score += len(target_tokens & entry["device_tokens"]) * 3
        if target and _normalize_text(target) in entry["normalized_command"]:
            score += 3
        if entry["device_tokens"] and entry["device_tokens"].issubset(input_tokens):
            score += 2
        if score > 0:
            fuzzy_entry = dict(entry)
            fuzzy_entry["match_type"] = "fuzzy"
            scored.append((score, fuzzy_entry))

    if not scored:
        return _resolution_payload(
            handled=False,
            matched=False,
            command_text=text,
            message="No configured IoT command matched this request.",
            candidate_commands=[entry["command"] for entry in catalog[:5]],
        )

    scored.sort(key=lambda item: (-item[0], item[1]["command"]))
    best_score, best_entry = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else -1
    if best_score < 5 or (second_score >= best_score and len(scored) > 1):
        return _resolution_payload(
            handled=True,
            matched=False,
            command_text=text,
            message="The Smart Home command is ambiguous. Please be more specific.",
            candidate_commands=[entry["command"] for _score, entry in scored[:4]],
        )

    return _resolution_payload(
        handled=True,
        matched=True,
        command_text=text,
        message=f"Matched {text} to configured command {best_entry['command']}.",
        catalog_entry=best_entry,
    )


def _append_action_history(entry: dict[str, Any]) -> None:
    history = _safe_json_load(IOT_ACTION_HISTORY_PATH)
    history.append(entry)
    history = history[-_history_limit():]
    _safe_json_dump(IOT_ACTION_HISTORY_PATH, history)


def get_iot_action_history(limit: int = 20) -> list[dict[str, Any]]:
    history = _safe_json_load(IOT_ACTION_HISTORY_PATH)
    return history[-max(1, limit):]


def _execute_webhook(entry: dict[str, Any]) -> tuple[bool, str]:
    config = entry["config"]
    url = _compact_text(config.get("url"))
    if not url or "YOUR_KEY_HERE" in url or "YOUR_HOME_ASSISTANT_WEBHOOK_ID" in url:
        return False, "This Smart Home command still uses a placeholder URL or key."

    method = _compact_text(config.get("method") or "POST").upper() or "POST"
    headers = config.get("headers") if isinstance(config.get("headers"), dict) else None
    params = config.get("params") if isinstance(config.get("params"), dict) else None
    json_payload = config.get("json_payload") if isinstance(config.get("json_payload"), dict) else None
    data = config.get("body")

    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_payload,
            data=data,
            timeout=float(config.get("timeout_seconds") or 5),
        )
    except requests.RequestException as error:
        return False, f"I couldn't reach the Smart Home endpoint. ({error})"

    if response.status_code in {200, 201, 202, 204}:
        return True, _compact_text(config.get("success_message")) or "Smart Home command completed."
    return False, f"The Smart Home endpoint returned status code {response.status_code}."


def _execute_home_assistant_service(credentials: dict[str, Any], entry: dict[str, Any]) -> tuple[bool, str]:
    config = entry["config"]
    ha_config = credentials.get("home_assistant") if isinstance(credentials.get("home_assistant"), dict) else {}
    base_url = _compact_text(config.get("base_url") or ha_config.get("base_url"))
    token = _compact_text(config.get("token") or ha_config.get("token"))
    service_value = _compact_text(config.get("service"))
    if not base_url or not token or not service_value:
        return False, "Home Assistant service command is missing base URL, token, or service name."

    domain, separator, service_name = service_value.partition(".")
    if not separator:
        return False, "Home Assistant service should look like light.turn_on."

    payload = dict(config.get("data") or {})
    if config.get("entity_id") and "entity_id" not in payload:
        payload["entity_id"] = config.get("entity_id")
    if config.get("device_id") and "device_id" not in payload:
        payload["device_id"] = config.get("device_id")

    endpoint = base_url.rstrip("/") + f"/api/services/{domain}/{service_name}"
    try:
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=float(config.get("timeout_seconds") or 5),
        )
    except requests.RequestException as error:
        return False, f"I couldn't reach Home Assistant. ({error})"

    if response.status_code in {200, 201, 202}:
        return True, _compact_text(config.get("success_message")) or "Home Assistant command completed."
    return False, f"Home Assistant returned status code {response.status_code}."


def _execute_mqtt(credentials: dict[str, Any], entry: dict[str, Any]) -> tuple[bool, str]:
    if importlib.util.find_spec("paho.mqtt.client") is None:
        return False, "MQTT support needs the paho-mqtt package."

    import paho.mqtt.client as mqtt

    config = entry["config"]
    mqtt_config = credentials.get("mqtt") if isinstance(credentials.get("mqtt"), dict) else {}
    host = _compact_text(config.get("host") or mqtt_config.get("host"))
    topic = _compact_text(config.get("topic"))
    if not host or not topic:
        return False, "MQTT command is missing broker host or topic."

    port = int(config.get("port") or mqtt_config.get("port") or 1883)
    username = _compact_text(config.get("username") or mqtt_config.get("username"))
    password = _compact_text(config.get("password") or mqtt_config.get("password"))
    payload = config.get("payload", "")
    qos = int(config.get("qos") or 0)
    retain = bool(config.get("retain", False))

    client = mqtt.Client()
    if username:
        client.username_pw_set(username, password or None)

    try:
        client.connect(host, port, keepalive=int(mqtt_config.get("keepalive") or 30))
        client.loop_start()
        result = client.publish(topic, payload=json.dumps(payload) if isinstance(payload, (dict, list)) else payload, qos=qos, retain=retain)
        result.wait_for_publish()
        client.loop_stop()
        client.disconnect()
    except Exception as error:
        return False, f"I couldn't publish the MQTT command. ({error})"

    if result.rc == 0:
        return True, _compact_text(config.get("success_message")) or "MQTT command published."
    return False, f"MQTT publish failed with code {result.rc}."


def execute_iot_control(command_text: str, *, confirm: bool = False) -> dict[str, Any]:
    resolution = resolve_iot_control_command(command_text)
    response = dict(resolution)
    response["ok"] = False
    response["executed"] = False

    if not resolution.get("matched"):
        return response

    credentials = load_iot_credentials() or {}
    if not credentials.get("enabled"):
        response["message"] = "Smart Home controls are currently disabled in settings."
        return response

    matched_command = resolution["matched_command"]
    catalog = _build_command_catalog(credentials)
    entry = next((item for item in catalog if item["command"] == matched_command), None)
    if not entry:
        response["message"] = "The configured Smart Home command could not be loaded."
        return response

    if resolution.get("requires_confirmation") and not confirm:
        response["message"] = (
            f"Please confirm before I run {matched_command}. "
            f"This action is marked as {resolution.get('risk_level', 'low')} risk."
        )
        response["confirmation_prompt"] = response["message"]
        return response

    integration = entry["integration_type"]
    if integration == "webhook":
        success, message = _execute_webhook(entry)
    elif integration == "home_assistant_service":
        success, message = _execute_home_assistant_service(credentials, entry)
    elif integration == "mqtt":
        success, message = _execute_mqtt(credentials, entry)
    else:
        success, message = False, "Unsupported Smart Home integration type."

    response["ok"] = success
    response["executed"] = True
    response["message"] = message
    response["matched_command"] = matched_command

    history_entry = {
        "timestamp": _utc_now(),
        "input": _compact_text(command_text),
        "matched_command": matched_command,
        "device_name": entry["device_name"],
        "integration_type": integration,
        "risk_level": resolution.get("risk_level", "low"),
        "confirmed": bool(confirm),
        "ok": success,
        "message": message,
    }
    _append_action_history(history_entry)
    response["history_entry"] = history_entry
    return response
