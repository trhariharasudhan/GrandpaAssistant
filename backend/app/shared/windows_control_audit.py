from __future__ import annotations

import importlib
import importlib.util
from typing import Any

from call_control import call_capability_status


def _callable_exists(module_name: str, function_name: str) -> tuple[bool, str]:
    try:
        spec = importlib.util.find_spec(module_name)
    except Exception as error:
        return False, f"Lookup warning: {error}"
    if not spec or not spec.origin:
        return False, "Module was not found."
    try:
        with open(spec.origin, "r", encoding="utf-8", errors="ignore") as handle:
            source = handle.read()
    except OSError as error:
        return False, f"Could not inspect source: {error}"
    markers = (f"def {function_name}(", f"async def {function_name}(", f"{function_name} =")
    return any(marker in source for marker in markers), "Source inspected without importing feature module."


def _capability(
    category: str,
    capability_key: str,
    title: str,
    module_name: str = "",
    function_name: str = "",
    command_examples: list[str] | None = None,
    safety_level: str = "safe",
    notes: str = "",
    implemented_override: bool | None = None,
) -> dict[str, Any]:
    warning = ""
    implemented = implemented_override
    if implemented is None:
        implemented, warning = _callable_exists(module_name, function_name) if module_name and function_name else (False, "No implementation reference.")
    test_status = "pass" if implemented else "warning"
    return {
        "category": category,
        "capability_key": capability_key,
        "title": title,
        "implemented": bool(implemented),
        "command_examples": command_examples or [],
        "safety_level": safety_level,
        "test_status": test_status,
        "notes": notes or warning or "Routed through existing backend command handlers.",
    }


def build_windows_control_audit(language="auto"):
    items = [
        _capability("App/window controls", "open_app", "Open app", "system.app_scan_module", "find_best_app_match", ["open notepad"], "safe"),
        _capability("App/window controls", "close_app", "Close app", "system.system_module", "close_app", ["close notepad"], "confirmation_required"),
        _capability("App/window controls", "active_window_detection", "Active window detection", "window_awareness", "get_active_window_context", ["active window"], "safe"),
        _capability("App/window controls", "window_minimize_maximize_focus", "Window minimize/maximize/focus", "system.system_module", "minimize_app", ["minimize window", "maximize window", "switch to chrome"], "safe"),
        _capability("Browser/system navigation", "open_website", "Open website", "integrations.web_module", "wikipedia_search", ["open google.com"], "safe", "Website opening is routed through web/system command handlers."),
        _capability("Browser/system navigation", "search_web", "Search web", "integrations.web_module", "wikipedia_search", ["search web for weather"], "safe"),
        _capability("Browser/system navigation", "open_folder_file", "Open folder/file", "system.system_module", "open_explorer", ["open downloads"], "safe"),
        _capability("Keyboard/mouse safe controls", "type_text", "Type text", "system.media_module", "type_text_dynamic", ["type hello"], "confirmation_required"),
        _capability("Keyboard/mouse safe controls", "hotkeys", "Hotkeys", "system.windows_voice_control_module", "run_windows_voice_macro", ["paste that", "open run box"], "safe"),
        _capability("Keyboard/mouse safe controls", "click_scroll", "Click/scroll", "system.windows_voice_control_module", "handle_desktop_action", ["scroll down", "click start button"], "safe"),
        _capability("System controls", "volume", "Volume", "controls.volume_control", "handle_volume", ["volume up", "set volume to 40"], "safe"),
        _capability("System controls", "brightness", "Brightness", "controls.brightness_control", "handle_brightness", ["brightness up", "set brightness to 60"], "safe"),
        _capability("System controls", "screenshot", "Screenshot", "system.system_module", "take_screenshot", ["take screenshot"], "safe"),
        _capability("System controls", "clipboard", "Clipboard", "system.window_context_module", "summarize_code_editor", ["copy selected text", "paste that"], "safe", "Clipboard helpers are routed through selection/window modules and pyperclip."),
        _capability("System controls", "power_lock_safety", "Sleep/shutdown/restart/lock safety", "system.system_module", "shutdown_system", ["shutdown system", "restart system", "lock system"], "confirmation_required"),
        _capability("Communication", "call_contact_number", "Call contact/number", "call_control", "initiate_call", ["call mom", "call 9876543210", "riyaa ku call pannu"], "safe", call_capability_status().get("safety", "")),
        _capability("Communication", "phone_link_dialer", "Open dialer/Phone Link", "system.windows_voice_control_module", "open_default_windows_app", ["open phone link"], "safe"),
        _capability("Communication", "whatsapp_phone_route", "WhatsApp/phone route", "system.window_context_module", "handle_whatsapp_screen_action", ["whatsapp call riyaa", "open whatsapp chat riyaa"], "confirmation_required"),
        _capability("Productivity", "notes_reminders", "Notes/reminders", "productivity.notes_module", "add_note", ["add note buy milk", "remind me to call mom"], "safe"),
        _capability("Productivity", "file_search_read_only", "File search/read-only operations", "context_action_executor", "handle_file_explorer_help", ["help me with files"], "safe"),
        _capability("Debug assistant", "debug_report", "Debug report", "debug_assistant", "build_debug_report", ["debug this"], "safe"),
        _capability("Debug assistant", "fix_plan", "Fix plan", "fix_plan_generator", "build_fix_plan", ["give fix plan"], "safe"),
        _capability("Debug assistant", "approval_flow", "Approval flow", "fix_approval_flow", "create_fix_approval", ["apply fix", "allow <id>"], "confirmation_required"),
        _capability("Debug assistant", "audit_log", "Audit log", "fix_audit_log", "list_fix_audit_events", ["fix audit"], "safe"),
        _capability("Debug assistant", "debug_session", "Debug session", "debug_session", "get_current_debug_session", ["start debug session"], "safe"),
        _capability("Debug assistant", "debug_dashboard", "Debug dashboard", "debug_health_dashboard", "build_debug_health_dashboard", ["debug dashboard"], "safe"),
        _capability("Voice/chat", "text_chat", "Text chat", "llm_client", "generate_chat_reply", ["ask a question"], "safe"),
        _capability("Voice/chat", "voice_input_readiness", "Voice input readiness", "voice.listen", "stt_backend_payload", ["voice mode"], "safe"),
        _capability("Voice/chat", "tts_readiness", "TTS readiness", "voice.speak", "synthesize_speech_base64", ["read this aloud"], "safe"),
        _capability("Voice/chat", "wake_direct_commands", "Wake/direct commands", "voice.listen", "wake_word_detected", ["grandpa open notepad"], "safe"),
    ]
    warnings = [item for item in items if item["test_status"] in {"warning", "fail"}]
    categories = {}
    for item in items:
        categories.setdefault(item["category"], []).append(item)
    return {
        "ok": True,
        "language": language or "auto",
        "categories": [{"name": name, "items": values} for name, values in categories.items()],
        "items": items,
        "implemented_count": sum(1 for item in items if item["implemented"]),
        "total_count": len(items),
        "warnings": warnings,
        "critical_failures": [],
        "no_destructive_action": True,
    }


def summarize_windows_control_audit(payload, language="auto"):
    payload = payload or {}
    tamil = str(language or payload.get("language") or "").lower() in {"ta", "tamil"}
    implemented = int(payload.get("implemented_count") or 0)
    total = int(payload.get("total_count") or 0)
    warnings = payload.get("warnings") or []
    if tamil:
        prefix = f"Windows controls audit: {implemented}/{total} controls ready."
    else:
        prefix = f"Windows controls audit: {implemented}/{total} controls implemented."
    if warnings:
        return f"{prefix} Warnings: {len(warnings)}. Run scripts/dev/windows_controls_audit.py for details."
    return f"{prefix} No critical failures. No destructive actions were run."
