import contextlib
import datetime
import io
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import core.command_router as command_router_module
from brain.database import get_recent_commands
from brain.memory_engine import get_memory
from core.command_router import process_command
from modules.event_module import get_event_data
from modules.google_contacts_module import CACHE_PATH as GOOGLE_CONTACTS_CACHE_PATH
from modules.google_contacts_module import (
    get_recent_contact_change_summary,
    list_contact_aliases,
    list_favorite_contacts,
)
from modules.notes_module import latest_note
from modules.startup_module import (
    disable_startup_auto_launch,
    enable_startup_auto_launch,
    startup_auto_launch_status,
)
from modules.telegram_module import get_telegram_remote_history
from modules.task_module import get_task_data
from modules.weather_module import get_weather_report
from modules.health_module import get_system_status
from utils.config import get_setting, update_setting
from voice.listen import listen
import voice.speak as voice_speak_module


_server = None
_server_thread = None
_installed_apps = {}
_voice_thread = None
_voice_lock = threading.Lock()
_voice_enabled = False
_voice_activity = "Ready"
_voice_transcript = ""
_voice_error = ""
_voice_messages = []
_voice_last_reply = ""


def _compact_text(value):
    return " ".join(str(value or "").split()).strip()


def _safe_call(callback, fallback):
    try:
        value = callback()
    except Exception:
        return fallback
    return fallback if value is None else value


def _load_contact_preview(limit=6):
    if not os.path.exists(GOOGLE_CONTACTS_CACHE_PATH):
        return []
    try:
        with open(GOOGLE_CONTACTS_CACHE_PATH, "r", encoding="utf-8") as file:
            contacts = json.load(file)
    except Exception:
        return []

    preview = []
    seen = set()
    for contact in contacts:
        name = _compact_text(contact.get("display_name") or "")
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        preview.append(name)
        if len(preview) >= limit:
            break
    return preview


def _capture_command_reply(command):
    spoken_messages = []
    original_router_speak = command_router_module.speak
    original_voice_speak = voice_speak_module.speak
    buffer = io.StringIO()

    def capture_speak(text, *args, **kwargs):
        cleaned = _compact_text(text)
        if cleaned:
            spoken_messages.append(cleaned)

    command_router_module.speak = capture_speak
    voice_speak_module.speak = capture_speak
    try:
        with contextlib.redirect_stdout(buffer):
            process_command((command or "").lower().strip(), _installed_apps, input_mode="text")
    finally:
        command_router_module.speak = original_router_speak
        voice_speak_module.speak = original_voice_speak

    if spoken_messages:
        return spoken_messages

    output = _compact_text(buffer.getvalue())
    if output:
        return [output]
    return ["Command completed."]


def _set_voice_state(activity=None, transcript=None, error=None):
    global _voice_activity, _voice_transcript, _voice_error
    if activity is not None:
        _voice_activity = activity
    if transcript is not None:
        _voice_transcript = transcript
    if error is not None:
        _voice_error = error


def _push_voice_messages(messages):
    global _voice_messages, _voice_last_reply
    cleaned = [_compact_text(item) for item in (messages or []) if _compact_text(item)]
    if not cleaned:
        return
    for item in reversed(cleaned):
        if item.startswith("Grandpa : "):
            _voice_last_reply = item.replace("Grandpa : ", "", 1)
            break
    _voice_messages = (_voice_messages + cleaned)[-12:]


def _voice_loop():
    global _voice_enabled
    while _voice_enabled:
        try:
            _set_voice_state(activity="Listening", transcript="Listening... Speak now.", error="")
            heard = listen(for_wake_word=False)
            if not _voice_enabled:
                break
            if not heard:
                _set_voice_state(activity="Listening", transcript="Listening... Speak now.", error="")
                continue
            _set_voice_state(activity="Thinking", transcript=f"Heard: {heard}", error="")
            replies = _capture_command_reply(heard)
            _set_voice_state(
                activity="Speaking",
                transcript=f"Replying: {_compact_text(replies[0]) if replies else 'Done.'}",
                error="",
            )
            _push_voice_messages([f"You : {heard}", *[f"Grandpa : {reply}" for reply in replies]])
            _set_voice_state(activity="Listening", transcript=f"Heard: {heard}", error="")
        except Exception as error:
            _set_voice_state(activity="Error", error=str(error))
    _set_voice_state(activity="Ready", transcript="" if not _voice_enabled else _voice_transcript)


def _ensure_voice_thread():
    global _voice_thread
    if _voice_thread and _voice_thread.is_alive():
        return
    _voice_thread = threading.Thread(target=_voice_loop, daemon=True)
    _voice_thread.start()


def _voice_status_payload():
    return {
        "enabled": _voice_enabled,
        "activity": _voice_activity,
        "transcript": _voice_transcript,
        "error": _voice_error,
        "messages": _voice_messages[-8:],
        "last_reply": _voice_last_reply,
    }


def start_voice_api_mode():
    global _voice_enabled
    with _voice_lock:
        _voice_enabled = True
        _set_voice_state(activity="Listening", transcript="Listening... Speak now.", error="")
        _ensure_voice_thread()
    return _voice_status_payload()


def stop_voice_api_mode():
    global _voice_enabled
    with _voice_lock:
        _voice_enabled = False
        _set_voice_state(activity="Ready", transcript="", error="")
    return _voice_status_payload()


def _build_ui_state():
    task_data = _safe_call(get_task_data, {"tasks": [], "reminders": []})
    event_data = _safe_call(get_event_data, {"events": []})
    tasks = task_data.get("tasks", [])
    reminders = task_data.get("reminders", [])
    events = event_data.get("events", [])
    pending_tasks = sum(1 for task in tasks if not task.get("completed"))
    overdue_count = 0
    now = datetime.datetime.now()

    for reminder in reminders:
        due_at = reminder.get("due_at")
        due_date = reminder.get("due_date")
        due_dt = None
        if due_at:
            try:
                due_dt = datetime.datetime.fromisoformat(due_at)
            except ValueError:
                due_dt = None
        if due_dt is None and due_date:
            try:
                due_dt = datetime.datetime.combine(
                    datetime.date.fromisoformat(due_date),
                    datetime.time(hour=9, minute=0),
                )
            except ValueError:
                due_dt = None
        if due_dt and due_dt < now:
            overdue_count += 1

    upcoming_events = sorted(
        [event for event in events if event.get("date")],
        key=lambda item: (item.get("date", ""), item.get("time", "")),
    )
    next_event = upcoming_events[0]["title"] if upcoming_events else "No upcoming events."
    pending_task_titles = [
        _compact_text(task.get("title") or task.get("task") or "Untitled task")
        for task in tasks
        if not task.get("completed")
    ][:5]
    overdue_reminders = []

    for reminder in reminders:
        title = _compact_text(reminder.get("title") or reminder.get("text") or reminder.get("task") or "Reminder")
        due_label = reminder.get("due_at") or reminder.get("due_date") or ""
        if title and due_label:
            overdue_reminders.append(f"{title} - {due_label}")
        elif title:
            overdue_reminders.append(title)
        if len(overdue_reminders) >= 5:
            break

    event_titles = []
    for event in upcoming_events[:5]:
        title = _compact_text(event.get("title") or "Untitled event")
        date_text = _compact_text(event.get("date") or "")
        time_text = _compact_text(event.get("time") or "")
        suffix = " ".join(part for part in [date_text, time_text] if part)
        event_titles.append(f"{title} - {suffix}".strip(" -"))

    note_summary = _safe_call(latest_note, "No saved notes yet.")
    recent_commands = _safe_call(lambda: get_recent_commands(limit=5), [])
    preferred_language = _safe_call(lambda: get_memory("preferences.language"), None) or "Not set"
    favorite_contact = _safe_call(lambda: get_memory("personal.relationships.favorite_contact"), None) or "Not set"
    wake_word = _safe_call(lambda: get_setting("wake_word", "hey grandpa"), "hey grandpa")
    voice_profile = _safe_call(lambda: get_setting("voice.mode", "normal"), "normal")
    contacts_preview = _safe_call(_load_contact_preview, [])
    aliases_summary = _safe_call(list_contact_aliases, "I do not have any saved contact aliases yet.")
    favorites_summary = _safe_call(list_favorite_contacts, "You do not have any favorite contacts yet.")
    recent_contact_changes = _safe_call(get_recent_contact_change_summary, "No recent Google contact changes.")
    telegram_history = _safe_call(lambda: get_telegram_remote_history(limit=3), "No Telegram remote commands are logged yet.")
    notifications = []

    if overdue_count:
        notifications.append(
            {
                "level": "warning",
                "text": f"You have {overdue_count} overdue reminder(s).",
            }
        )

    if pending_tasks:
        notifications.append(
            {
                "level": "info",
                "text": f"{pending_tasks} pending task(s) need attention.",
            }
        )

    if next_event and next_event != "No upcoming events.":
        notifications.append(
            {
                "level": "info",
                "text": f"Next event: {next_event}",
            }
        )

    if _voice_error:
        notifications.append(
            {
                "level": "error",
                "text": f"Voice issue: {_compact_text(_voice_error)}",
            }
        )

    if not get_setting("startup.auto_launch_enabled", False):
        notifications.append(
            {
                "level": "neutral",
                "text": "Auto-launch is off.",
            }
        )

    if get_setting("assistant.emergency_mode_enabled", False):
        notifications.append(
            {
                "level": "warning",
                "text": "Emergency mode is enabled.",
            }
        )

    if recent_contact_changes and "No recent" not in recent_contact_changes:
        notifications.append(
            {
                "level": "info",
                "text": recent_contact_changes,
            }
        )

    if telegram_history and "No Telegram" not in telegram_history:
        notifications.append(
            {
                "level": "neutral",
                "text": telegram_history,
            }
        )

    return {
        "overview": {
            "tasks": f"{pending_tasks} pending",
            "reminders": f"{overdue_count} overdue",
            "weather": _safe_call(get_weather_report, "Weather unavailable right now."),
            "health": _safe_call(get_system_status, "Health unavailable right now."),
        },
        "today": f"Pending tasks: {pending_tasks} | Overdue reminders: {overdue_count}",
        "next_event": next_event,
        "latest_note": note_summary,
        "recent_commands": recent_commands,
        "notifications": notifications[:6],
        "dashboard": {
            "tasks": pending_task_titles or ["No pending tasks."],
            "reminders": overdue_reminders or ["No overdue reminders."],
            "events": event_titles or ["No upcoming events."],
        },
        "memory": {
            "preferred_language": preferred_language,
            "favorite_contact": favorite_contact,
        },
        "settings": {
            "wake_word": wake_word,
            "voice_profile": voice_profile,
            "offline_mode": get_setting("assistant.offline_mode_enabled", False),
            "developer_mode": _safe_call(lambda: get_setting("assistant.developer_mode_enabled", False), False),
            "emergency_mode": _safe_call(lambda: get_setting("assistant.emergency_mode_enabled", False), False),
        },
        "contacts": {
            "favorite_contact": favorite_contact,
            "preview": contacts_preview or ["No synced contacts yet."],
            "aliases_summary": aliases_summary,
            "favorites_summary": favorites_summary,
            "recent_changes": recent_contact_changes,
        },
        "emergency": {
            "location": _safe_call(lambda: get_memory("personal.contact.address"), None)
            or _safe_call(lambda: get_memory("personal.location.current_location.city"), None)
            or "No saved location.",
            "contact": _safe_call(lambda: get_memory("personal.contact.emergency_contact.name"), None) or "Not set",
            "mode_enabled": _safe_call(lambda: get_setting("assistant.emergency_mode_enabled", False), False),
            "protocol_summary": "Alert, location share, and contact call shortcuts are ready.",
        },
        "startup": {
            "auto_launch_enabled": _safe_call(lambda: get_setting("startup.auto_launch_enabled", False), False),
            "tray_mode": _safe_call(lambda: get_setting("startup.tray_mode", False), False),
            "summary": _safe_call(startup_auto_launch_status, "Startup status unavailable right now."),
            "portable_setup_ready": os.path.exists(
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "setup_portable_desktop.cmd")
            ),
            "react_ui_on_tray_enabled": _safe_call(lambda: get_setting("startup.react_ui_on_tray_enabled", False), False),
            "react_ui_on_tray_mode": _safe_call(lambda: get_setting("startup.react_ui_on_tray_mode", "browser"), "browser"),
            "react_frontend_ready": os.path.exists(
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "start_react_frontend.cmd")
            ),
            "react_desktop_ready": os.path.exists(
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "start_react_electron.cmd")
            ),
        },
        "voice": _voice_status_payload(),
    }


class _AssistantApiHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self):
        self._send_json({"ok": True})

    def do_GET(self):
        if self.path == "/api/health":
            self._send_json({"ok": True, "service": "grandpa-assistant-api"})
            return

        if self.path == "/api/ui-state":
            self._send_json({"ok": True, "state": _build_ui_state()})
            return

        if self.path == "/api/voice/status":
            self._send_json({"ok": True, "voice": _voice_status_payload()})
            return

        if self.path == "/api/settings/startup":
            self._send_json({"ok": True, "startup": _build_ui_state()["startup"]})
            return

        self._send_json({"ok": False, "error": "Not found"}, status=404)

    def do_POST(self):
        if self.path == "/api/voice/start":
            self._send_json({"ok": True, "voice": start_voice_api_mode()})
            return

        if self.path == "/api/voice/stop":
            self._send_json({"ok": True, "voice": stop_voice_api_mode()})
            return

        if self.path == "/api/settings/startup":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                self._send_json({"ok": False, "error": "Invalid JSON"}, status=400)
                return

            auto_launch = payload.get("auto_launch_enabled")
            tray_mode = payload.get("tray_mode")

            try:
                if tray_mode is not None:
                    update_setting("startup.tray_mode", bool(tray_mode))
                if auto_launch is True:
                    message = enable_startup_auto_launch()
                elif auto_launch is False:
                    message = disable_startup_auto_launch()
                else:
                    message = startup_auto_launch_status()
                self._send_json(
                    {
                        "ok": True,
                        "message": message,
                        "startup": _build_ui_state()["startup"],
                    }
                )
                return
            except Exception as error:
                self._send_json({"ok": False, "error": f"Startup settings error: {error}"}, status=500)
                return

        if self.path == "/api/settings/portable-setup":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                self._send_json({"ok": False, "error": "Invalid JSON"}, status=400)
                return

            action = _compact_text(payload.get("action")) or "desktop"
            root_dir = os.path.dirname(os.path.dirname(__file__))
            script_path = os.path.join(root_dir, "setup_portable_desktop.cmd")
            if not os.path.exists(script_path):
                self._send_json({"ok": False, "error": "Portable setup helper not found."}, status=404)
                return

            try:
                args = [script_path]
                if action == "startup-on":
                    args.append("/startup-on")
                elif action == "startup-off":
                    args.append("/startup-off")
                subprocess.run(args, cwd=root_dir, check=True, shell=True)
                if action == "startup-on":
                    message = "Portable app startup shortcut enabled."
                elif action == "startup-off":
                    message = "Portable app startup shortcut disabled."
                else:
                    message = "Portable app desktop shortcut created."
                self._send_json({"ok": True, "message": message, "startup": _build_ui_state()["startup"]})
                return
            except Exception as error:
                self._send_json({"ok": False, "error": f"Portable setup error: {error}"}, status=500)
                return

        if self.path != "/api/command":
            self._send_json({"ok": False, "error": "Not found"}, status=404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json({"ok": False, "error": "Invalid JSON"}, status=400)
            return

        command = _compact_text(payload.get("command"))
        if not command:
            self._send_json({"ok": False, "error": "Command is required."}, status=400)
            return

        try:
            messages = _capture_command_reply(command)
            self._send_json(
                {
                    "ok": True,
                    "command": command,
                    "messages": messages,
                    "state": _build_ui_state(),
                }
            )
        except Exception as error:
            self._send_json({"ok": False, "error": f"Assistant error: {error}"}, status=500)

    def log_message(self, format, *args):
        return


def start_web_api(installed_apps, host="127.0.0.1", port=8765):
    global _server, _server_thread, _installed_apps

    _installed_apps = installed_apps or {}

    if _server_thread and _server_thread.is_alive():
        return

    _server = ThreadingHTTPServer((host, port), _AssistantApiHandler)
    _server_thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _server_thread.start()
