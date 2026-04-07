from __future__ import annotations

import contextlib
import io
import uuid

import core.command_router as command_router_module
from cognition.state import load_section, update_section, utc_now
from core.command_router import process_command
import voice.speak as voice_speak_module


MAX_HISTORY = 80
BUILTIN_WORKFLOWS = {
    "work mode": {
        "description": "Start a focused work session with planning and focus helpers.",
        "commands": ["enable focus mode", "plan my day", "what should i do now"],
    },
    "planning reset": {
        "description": "Refresh the daily view and overdue workload.",
        "commands": ["show overdue items", "what is due today", "latest note"],
    },
    "voice check": {
        "description": "Check voice system health and diagnostics quickly.",
        "commands": ["voice status", "voice diagnostics", "assistant doctor"],
    },
}


def _compact_text(value) -> str:
    return " ".join(str(value or "").split()).strip()


def _capture_command_reply(command: str) -> list[str]:
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
            process_command((command or "").lower().strip(), {}, input_mode="text")
    finally:
        command_router_module.speak = original_router_speak
        voice_speak_module.speak = original_voice_speak

    if spoken_messages:
        return spoken_messages
    output = _compact_text(buffer.getvalue())
    if output:
        return [output]
    return ["Command completed."]


def _workflow_items() -> list[dict]:
    section = load_section("workflows", {})
    custom = list(section.get("custom_workflows") or [])
    items = []
    seen = set()
    for name, payload in BUILTIN_WORKFLOWS.items():
        items.append(
            {
                "name": name,
                "description": payload.get("description", ""),
                "commands": payload.get("commands", []),
                "builtin": True,
            }
        )
        seen.add(name.lower())
    for item in custom:
        name = _compact_text(item.get("name"))
        if not name or name.lower() in seen:
            continue
        items.append(
            {
                "name": name,
                "description": _compact_text(item.get("description")),
                "commands": [_compact_text(command) for command in item.get("commands", []) if _compact_text(command)],
                "builtin": False,
            }
        )
    return items


def workflow_status_payload() -> dict:
    section = load_section("workflows", {})
    items = _workflow_items()
    history = list(section.get("run_history") or [])
    return {
        "workflow_count": len(items),
        "builtin_count": len([item for item in items if item.get("builtin")]),
        "custom_count": len([item for item in items if not item.get("builtin")]),
        "workflows": items,
        "recent_runs": history[-8:],
        "summary": f"{len(items)} workflow(s) available for task chaining.",
    }


def create_workflow(name: str, commands: list[str], description: str = "") -> dict | None:
    clean_name = _compact_text(name).lower()
    clean_commands = [_compact_text(command) for command in commands if _compact_text(command)]
    if not clean_name or not clean_commands:
        return None

    record = {
        "id": f"workflow-{uuid.uuid4().hex[:10]}",
        "name": clean_name,
        "description": _compact_text(description),
        "commands": clean_commands,
        "created_at": utc_now(),
    }

    def updater(current):
        data = current if isinstance(current, dict) else {}
        custom = [item for item in list(data.get("custom_workflows") or []) if _compact_text(item.get("name")).lower() != clean_name]
        custom.append(record)
        data["custom_workflows"] = custom[-30:]
        data.setdefault("run_history", [])
        return data

    update_section("workflows", updater)
    return record


def run_workflow(name: str, execute: bool = True) -> dict:
    clean_name = _compact_text(name).lower()
    selected = None
    for item in _workflow_items():
        if _compact_text(item.get("name")).lower() == clean_name:
            selected = item
            break
    if not selected:
        return {"ok": False, "message": f"Workflow not found: {name}"}

    steps = []
    for command in selected.get("commands", []):
        result = {"command": command, "messages": []}
        if execute:
            result["messages"] = _capture_command_reply(command)
        steps.append(result)

    run_record = {
        "name": selected.get("name"),
        "executed": bool(execute),
        "created_at": utc_now(),
        "step_count": len(steps),
    }

    def updater(current):
        data = current if isinstance(current, dict) else {}
        history = list(data.get("run_history") or [])
        history.append(run_record)
        data["run_history"] = history[-MAX_HISTORY:]
        data.setdefault("custom_workflows", [])
        return data

    update_section("workflows", updater)
    return {
        "ok": True,
        "workflow": selected,
        "steps": steps,
        "message": f"Workflow {selected.get('name')} {'executed' if execute else 'planned'}.",
    }
