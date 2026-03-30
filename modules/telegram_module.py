import json
import json
import os
import threading
import time

import requests

from utils.config import get_setting


TELEGRAM_API_BASE = "https://api.telegram.org"
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_PATH = os.path.join(DATA_DIR, "telegram_state.json")
LOG_PATH = os.path.join(DATA_DIR, "telegram_remote_log.json")

_telegram_listener_thread = None
_telegram_listener_lock = threading.Lock()
SAFE_REMOTE_PREFIXES = (
    "today agenda",
    "weather",
    "system status",
    "dashboard",
    "offline help",
    "offline mode status",
    "voice status",
    "github summary",
    "current git branch",
    "recent commits",
    "google calendar status",
    "today in google calendar",
    "upcoming google calendar events",
    "emergency mode status",
    "emergency quick response",
    "share my location",
    "share my location everywhere",
    "send emergency alert",
    "send emergency alert everywhere",
    "send i am safe alert",
    "send safe alert everywhere",
)


def _telegram_settings():
    return {
        "enabled": bool(get_setting("telegram.enabled", False)),
        "bot_token": (get_setting("telegram.bot_token", "") or "").strip(),
        "chat_id": str(get_setting("telegram.chat_id", "") or "").strip(),
        "alerts_enabled": bool(get_setting("telegram.alerts_enabled", True)),
        "remote_control_enabled": bool(get_setting("telegram.remote_control_enabled", False)),
        "poll_interval_seconds": max(2, int(get_setting("telegram.poll_interval_seconds", 4) or 4)),
    }


def _is_ready(settings=None):
    settings = settings or _telegram_settings()
    return bool(settings["enabled"] and settings["bot_token"] and settings["chat_id"])


def _api_url(bot_token, method):
    return f"{TELEGRAM_API_BASE}/bot{bot_token}/{method}"


def _load_state():
    if not os.path.exists(STATE_PATH):
        return {"last_update_id": 0}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {"last_update_id": 0}


def _save_state(state):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)


def _append_log(command_text, reply_text):
    os.makedirs(DATA_DIR, exist_ok=True)
    entries = []
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, "r", encoding="utf-8") as file:
                loaded = json.load(file)
            if isinstance(loaded, list):
                entries = loaded[-24:]
        except Exception:
            entries = []

    entries.append(
        {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "command": " ".join(str(command_text or "").split()),
            "reply": " ".join(str(reply_text or "").split()),
        }
    )

    with open(LOG_PATH, "w", encoding="utf-8") as file:
        json.dump(entries[-25:], file, indent=2, ensure_ascii=False)


def get_telegram_remote_history(limit=5):
    if not os.path.exists(LOG_PATH):
        return "No Telegram remote commands are logged yet."
    try:
        with open(LOG_PATH, "r", encoding="utf-8") as file:
            entries = json.load(file)
    except Exception:
        return "I could not read the Telegram remote history right now."

    if not entries:
        return "No Telegram remote commands are logged yet."

    lines = []
    for item in entries[-limit:]:
        lines.append(f"{item.get('time', '')}: {item.get('command', '')}")
    return "Recent Telegram remote commands: " + " | ".join(lines)


def get_telegram_quick_help_summary():
    return "Try: today agenda | weather | github summary | google calendar status | emergency protocol status"


def telegram_status():
    settings = _telegram_settings()
    if not settings["enabled"]:
        return "Telegram integration is disabled."
    if not settings["bot_token"]:
        return "Telegram integration is enabled, but the bot token is not set yet."
    if not settings["chat_id"]:
        return "Telegram integration is enabled, but the chat id is not set yet."
    remote_status = "on" if settings["remote_control_enabled"] else "off"
    return (
        f"Telegram integration is ready for chat id {settings['chat_id']}. "
        f"Remote control is {remote_status}."
    )


def send_telegram_message(message, purpose="message"):
    settings = _telegram_settings()
    if not _is_ready(settings):
        return False, telegram_status()

    text = " ".join(str(message or "").split())
    if not text:
        return False, "I need a Telegram message to send."

    url = _api_url(settings["bot_token"], "sendMessage")
    payload = {
        "chat_id": settings["chat_id"],
        "text": text,
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=12)
        data = response.json() if response.content else {}
        if response.ok and data.get("ok"):
            if purpose == "alert":
                return True, "Telegram alert sent."
            return True, "Telegram message sent."
        description = data.get("description") or f"HTTP {response.status_code}"
        return False, f"I could not send the Telegram {purpose}: {description}."
    except requests.RequestException:
        return False, f"I could not reach Telegram right now to send the {purpose}."
    except Exception:
        return False, f"I hit an unexpected Telegram error while sending the {purpose}."


def send_telegram_quick_help():
    settings = _telegram_settings()
    if not _is_ready(settings):
        return False, telegram_status()

    url = _api_url(settings["bot_token"], "sendMessage")
    payload = {
        "chat_id": settings["chat_id"],
        "text": (
            "Telegram quick help:\n"
            "- today agenda\n"
            "- weather\n"
            "- github summary\n"
            "- google calendar status\n"
            "- upcoming google calendar events\n"
            "- emergency protocol status\n"
            "- share my location everywhere"
        ),
        "disable_web_page_preview": True,
        "reply_markup": {
            "keyboard": [
                ["today agenda", "weather"],
                ["github summary", "google calendar status"],
                ["upcoming google calendar events", "emergency protocol status"],
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False,
        },
    }

    try:
        response = requests.post(url, json=payload, timeout=12)
        data = response.json() if response.content else {}
        if response.ok and data.get("ok"):
            return True, "Telegram quick help sent."
        description = data.get("description") or f"HTTP {response.status_code}"
        return False, f"I could not send Telegram quick help: {description}."
    except requests.RequestException:
        return False, "I could not reach Telegram right now to send quick help."
    except Exception:
        return False, "I hit an unexpected Telegram error while sending quick help."


def send_telegram_alert(message):
    settings = _telegram_settings()
    if not settings["alerts_enabled"]:
        return False, "Telegram alerts are disabled."
    return send_telegram_message(message, purpose="alert")


def _fetch_updates(settings, offset):
    response = requests.get(
        _api_url(settings["bot_token"], "getUpdates"),
        params={
            "timeout": settings["poll_interval_seconds"],
            "offset": offset,
        },
        timeout=settings["poll_interval_seconds"] + 5,
    )
    data = response.json() if response.content else {}
    if response.ok and data.get("ok"):
        return data.get("result", [])
    return []


def _extract_command_text(update, expected_chat_id):
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    if str(chat.get("id", "")) != expected_chat_id:
        return None
    if from_user.get("is_bot"):
        return None
    text = (message.get("text") or "").strip()
    if text in {"/status", "/start", "/help"}:
        alias_map = {
            "/status": "github summary",
            "/start": "__telegram_quick_help__",
            "/help": "__telegram_quick_help__",
        }
        text = alias_map[text]
    return text or None


def is_safe_remote_command(command):
    normalized = " ".join(str(command or "").strip().lower().split())
    if not normalized:
        return False
    return any(normalized.startswith(prefix) for prefix in SAFE_REMOTE_PREFIXES)


def start_telegram_remote_control(command_callback):
    global _telegram_listener_thread

    settings = _telegram_settings()
    if not (_is_ready(settings) and settings["remote_control_enabled"]):
        return False

    with _telegram_listener_lock:
        if _telegram_listener_thread and _telegram_listener_thread.is_alive():
            return True

        def listener():
            state = _load_state()
            offset = int(state.get("last_update_id", 0) or 0)

            while True:
                loop_settings = _telegram_settings()
                if not (_is_ready(loop_settings) and loop_settings["remote_control_enabled"]):
                    time.sleep(2)
                    continue

                try:
                    updates = _fetch_updates(loop_settings, offset + 1)
                except Exception:
                    time.sleep(loop_settings["poll_interval_seconds"])
                    continue

                for update in updates:
                    update_id = int(update.get("update_id", 0) or 0)
                    if update_id > offset:
                        offset = update_id
                    text = _extract_command_text(update, loop_settings["chat_id"])
                    if not text:
                        continue

                    if not is_safe_remote_command(text):
                        if text == "__telegram_quick_help__":
                            send_telegram_quick_help()
                            continue
                        send_telegram_message(
                            "That Telegram command is blocked for safety. Try status, agenda, weather, calendar, git, or emergency helpers."
                        )
                        continue

                    send_telegram_message(f"Running command: {text}")
                    try:
                        reply = command_callback(text)
                    except Exception:
                        reply = "I hit an error while running that Telegram command."
                    _append_log(text, reply or "Command completed.")
                    if reply:
                        send_telegram_message(reply)
                    else:
                        send_telegram_message("Command completed.")

                state["last_update_id"] = offset
                _save_state(state)
                time.sleep(loop_settings["poll_interval_seconds"])

        _telegram_listener_thread = threading.Thread(target=listener, daemon=True)
        _telegram_listener_thread.start()
        return True
