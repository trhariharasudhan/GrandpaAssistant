from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import quote_plus

try:
    from services import local_action_executor
except ImportError:  # pragma: no cover
    from backend.app.services import local_action_executor

from .context import compact_text


RiskLevel = str
ToolExecutor = Callable[[dict[str, Any], Any | None], dict[str, Any]]

RISK_SAFE_READ = "safe_read"
RISK_SAFE_LOCAL_ACTION = "safe_local_action"
RISK_MEDIUM_CONFIRMATION = "medium_confirmation"
RISK_HIGH_CONFIRMATION = "high_confirmation"
RISK_BLOCKED = "blocked"


def _truthy_available() -> bool:
    return True


@dataclass(frozen=True)
class LocalAssistantTool:
    tool_name: str
    description: str
    supported_intents: tuple[str, ...]
    capabilities: tuple[str, ...]
    required_parameters: tuple[str, ...] = ()
    optional_parameters: tuple[str, ...] = ()
    risk_level: RiskLevel = RISK_SAFE_READ
    permission_requirement: str = "none"
    confirmation_required: bool = False
    platform_support: tuple[str, ...] = ("windows",)
    availability_check: Callable[[], bool] = _truthy_available
    executor: ToolExecutor | None = None
    safe_failure_message: str = "I understood the intent, but this adapter is not available yet."
    alternatives: tuple[str, ...] = field(default_factory=tuple)

    def is_available(self) -> bool:
        try:
            return bool(self.availability_check())
        except Exception:
            return False


def _missing_required(tool: LocalAssistantTool, params: dict[str, Any]) -> list[str]:
    return [name for name in tool.required_parameters if compact_text(params.get(name)) == ""]


def validate_tool_parameters(tool_name: str, params: dict[str, Any] | None) -> dict[str, Any]:
    tool = get_tool(tool_name)
    if tool is None:
        return {"ok": False, "missing_parameters": [], "error": f"Unknown tool: {tool_name}"}
    safe_params = params if isinstance(params, dict) else {}
    missing = _missing_required(tool, safe_params)
    return {"ok": not missing, "missing_parameters": missing, "error": ""}


def _local_action(action: str) -> ToolExecutor:
    def _execute(params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
        return local_action_executor.execute_local_action({"action": action, "params": params or {}})

    return _execute


def _execute_create_reminder(params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import executor as executor_module

    result = executor_module._create_structured_reminder_result(params or {})
    return {"ok": bool(result.get("ok", True)), "action": "create_reminder", "message": compact_text(result.get("message")), "data": {"reminder": result.get("reminder", {})}}


def _execute_list_reminders(params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import executor as executor_module

    result = executor_module._list_reminders_result(compact_text((params or {}).get("status")) or "pending")
    return {"ok": bool(result.get("ok", True)), "action": "list_reminders", "message": compact_text(result.get("message")), "data": {"reminders": result.get("reminders", [])}}


def _execute_complete_reminder(params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import executor as executor_module

    result = executor_module._complete_reminder_result(compact_text((params or {}).get("reminder_query")))
    data = {"reminder": result.get("reminder", {}), "matches": result.get("matches", []), "needs_disambiguation": bool(result.get("needs_disambiguation"))}
    return {"ok": bool(result.get("ok")), "action": "complete_reminder", "message": compact_text(result.get("message")), "data": data}


def _execute_cancel_reminder(params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import executor as executor_module

    result = executor_module._cancel_reminder_result(compact_text((params or {}).get("reminder_query")))
    data = {"reminder": result.get("reminder", {}), "matches": result.get("matches", []), "needs_disambiguation": bool(result.get("needs_disambiguation"))}
    return {"ok": bool(result.get("ok")), "action": "cancel_reminder", "message": compact_text(result.get("message")), "data": data}


def _execute_check_due_reminders(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import executor as executor_module

    result = executor_module._check_due_reminders_result()
    return {
        "ok": bool(result.get("ok", True)),
        "action": "check_due_reminders",
        "message": compact_text(result.get("message")),
        "data": {"due_reminders": result.get("due_reminders", []), "notification_count": result.get("notification_count", 0)},
    }


def _execute_startup_status(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import windows_startup_manager

    result = windows_startup_manager.startup_status()
    return {"ok": bool(result.get("ok", True)), "action": "startup_status", "message": compact_text(result.get("message")), "data": result}


def _execute_enable_startup(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import windows_startup_manager

    result = windows_startup_manager.enable_startup()
    return {"ok": bool(result.get("ok")), "action": "enable_startup", "message": compact_text(result.get("message")), "data": result}


def _execute_disable_startup(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import windows_startup_manager

    result = windows_startup_manager.disable_startup()
    return {"ok": bool(result.get("ok")), "action": "disable_startup", "message": compact_text(result.get("message")), "data": result}


def _execute_voice_runtime_status(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import voice_runtime

    status = voice_runtime.get_voice_runtime_status()
    state = "running" if status.get("running") else "stopped"
    enabled = "enabled" if status.get("enabled") else "disabled"
    backend = (status.get("stt_provider") or {}).get("resolved_backend") or "unknown"
    message = f"Voice runtime is {state} and {enabled}. Wake word is {status.get('wake_word')}. STT backend is {backend}."
    return {"ok": True, "action": "voice_runtime_status", "message": message, "data": status}


def _execute_enable_voice_runtime(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import voice_runtime

    result = voice_runtime.enable_voice_runtime()
    return {"ok": bool(result.get("ok")), "action": "enable_voice_runtime", "message": compact_text(result.get("message")), "data": result}


def _execute_disable_voice_runtime(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import voice_runtime

    result = voice_runtime.disable_voice_runtime()
    return {"ok": bool(result.get("ok")), "action": "disable_voice_runtime", "message": compact_text(result.get("message")), "data": result}


def _format_memory_label(memory: dict[str, Any]) -> str:
    key = compact_text((memory or {}).get("key")).replace("_", " ")
    value = compact_text((memory or {}).get("value"))
    category = compact_text((memory or {}).get("category")).replace("_", " ")
    return compact_text(f"{category}: {key} = {value}")


def _execute_remember_this(params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import memory_manager

    text = compact_text((params or {}).get("memory_text"))
    result = memory_manager.remember_from_message(text, explicit=not bool((params or {}).get("implicit")))
    stored = result.get("stored") if isinstance(result.get("stored"), list) else []
    conflicts = result.get("conflicts") if isinstance(result.get("conflicts"), list) else []
    return {
        "ok": bool(result.get("ok")),
        "action": "remember_this",
        "message": compact_text(result.get("message")),
        "data": {"stored": stored, "stored_count": len(stored), "blocked": result.get("blocked", []), "conflicts": conflicts, "low_quality": bool(result.get("low_quality"))},
    }


def _execute_list_memories(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import memory_manager

    memories = memory_manager.list_memories(min_confidence=memory_manager.DEFAULT_MIN_CONFIDENCE)
    if not memories:
        message = "I do not have any saved long-term memories yet."
    else:
        shown = "; ".join(_format_memory_label(item) for item in memories[:8])
        more = f" ({len(memories) - 8} more)" if len(memories) > 8 else ""
        message = f"Saved memories: {shown}{more}."
    return {"ok": True, "action": "list_memories", "message": message, "data": {"memories": memories, "memory_count": len(memories)}}


def _execute_forget_memory(params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import memory_manager

    query = compact_text((params or {}).get("memory_query"))
    result = memory_manager.forget_memory(query)
    return {
        "ok": bool(result.get("ok")),
        "action": "forget_memory",
        "message": compact_text(result.get("message")),
        "data": {"forgotten": result.get("forgotten", []), "matches": result.get("matches", []), "ambiguous": bool(result.get("ambiguous"))},
    }


def _execute_memory_status(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import memory_manager

    status = memory_manager.memory_status()
    message = f"Long-term memory is local-only with {status.get('memory_count', 0)} saved item(s)."
    return {"ok": True, "action": "memory_status", "message": message, "data": status}


def _execute_memory_opt_out(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    return {"ok": True, "action": "memory_opt_out", "message": "Okay, I will not save that to long-term memory.", "data": {}}


def _execute_review_memories(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import memory_manager

    review = memory_manager.review_memories()
    return {"ok": True, "action": "review_memories", "message": compact_text(review.get("message")), "data": review}


def _execute_cleanup_memories(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import memory_manager

    cleanup = memory_manager.cleanup_memory_suggestions()
    return {"ok": True, "action": "cleanup_memories", "message": compact_text(cleanup.get("message")), "data": cleanup}


def _execute_update_memory(params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import memory_manager

    category = compact_text((params or {}).get("category")) or "user_preferences"
    key = compact_text((params or {}).get("key"))
    value = compact_text((params or {}).get("value"))
    result = memory_manager.update_memory(category, key, value)
    return {"ok": bool(result.get("ok")), "action": "update_memory", "message": compact_text(result.get("message")), "data": {"memory": result.get("memory", {}), "quality": result.get("quality", {})}}


def _execute_memory_conflicts(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import memory_manager

    result = memory_manager.memory_conflicts()
    return {"ok": True, "action": "memory_conflicts", "message": compact_text(result.get("message")), "data": result}


def _execute_resolve_memory_conflict(params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import memory_manager

    result = memory_manager.resolve_conflict(compact_text((params or {}).get("memory_id")), compact_text((params or {}).get("decision")))
    return {"ok": bool(result.get("ok")), "action": "resolve_memory_conflict", "message": compact_text(result.get("message")), "data": result}


def _execute_create_task(params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import executor as executor_module

    reply = executor_module._save_task(str((params or {}).get("task_text") or ""))
    return {"ok": True, "action": "create_task", "message": reply, "data": {}}


def _execute_diagnostics(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import executor as executor_module

    reply = executor_module._diagnostics_summary()
    return {"ok": True, "action": "system_diagnostics", "message": reply, "data": {}}


def _execute_active_window_context(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from .screen_context import get_screen_context

    payload = get_screen_context(include_screenshot=False)
    active = payload.get("active_window") if isinstance(payload, dict) else {}
    app = compact_text((active or {}).get("app_name")) or "unknown app"
    activity = compact_text((active or {}).get("activity")) or "unknown"
    return {
        "ok": True,
        "action": "active_window_context",
        "message": f"Active window context checked: {app}, activity {activity}.",
        "data": payload,
    }


def _execute_screen_read(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    from . import executor as executor_module

    screen_context_module = getattr(executor_module, "screen_context_module", None)
    if screen_context_module is None:
        return {
            "ok": False,
            "action": "screen_read",
            "message": "I understood you want screen analysis, but the screen awareness adapter is missing.",
            "data": {"missing_adapter": "screen_awareness"},
        }
    payload = screen_context_module.get_screen_context(include_screenshot=True)
    screenshot = payload.get("screenshot") if isinstance(payload, dict) else {}
    summary = compact_text((screenshot or {}).get("summary"))
    if not summary:
        summary = "I cannot read the screen right now because screenshot or OCR context is not available."
    return {
        "ok": bool((screenshot or {}).get("ok")),
        "action": "screen_read",
        "message": summary,
        "data": {"screen_context": payload},
    }


def _execute_search_selected_google(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    try:
        import pyperclip  # type: ignore

        selected = compact_text(pyperclip.paste())
    except Exception:
        selected = ""
    if not selected:
        return {
            "ok": False,
            "action": "search_selected_google",
            "message": "I understood you want to search selected text on Google, but I cannot read clipboard or selected text right now.",
            "data": {"missing_adapter": "clipboard_selection"},
        }
    query = selected[:300]
    result = local_action_executor.execute_local_action({"action": "open_url", "params": {"url": "https://www.google.com/search?q=" + quote_plus(query)}})
    if result.get("ok"):
        return {"ok": True, "action": "search_selected_google", "message": "Searching Google for the selected text.", "data": result.get("data", {})}
    return {
        "ok": False,
        "action": "search_selected_google",
        "message": f"I understood the search intent, but browser opening failed: {compact_text(result.get('message'))}",
        "data": result.get("data", {}),
    }


def _execute_capability_discovery(_params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    tools = list_available_tools()
    names = [tool["tool_name"].replace("_", " ") for tool in tools if tool.get("available")]
    featured = ", ".join(names[:10])
    more = " and more" if len(names) > 10 else ""
    return {
        "ok": True,
        "action": "capability_discovery",
        "message": f"I can help with registered local tools like {featured}{more}. I will ask before risky actions.",
        "data": {"available_tool_count": len(names), "tools": [tool["tool_name"] for tool in tools if tool.get("available")]},
    }


def _execute_unsupported_action(params: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    capability = compact_text((params or {}).get("capability")) or "that action"
    explanation = explain_missing_tool(capability)
    return {
        "ok": False,
        "action": "unsupported_action",
        "message": explanation["message"],
        "data": {"missing_adapter": explanation["missing_adapter"], "capability": capability},
    }


_TOOLS: dict[str, LocalAssistantTool] = {
    "volume_control": LocalAssistantTool(
        tool_name="volume_control",
        description="Increase, decrease, mute, or unmute local Windows system volume.",
        supported_intents=("adjust_volume",),
        capabilities=("volume", "audio", "sound"),
        required_parameters=("operation",),
        optional_parameters=("step",),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="local_action_allowlist",
        executor=_local_action("adjust_volume"),
        safe_failure_message="I understood the volume intent, but the volume adapter failed.",
    ),
    "open_app": LocalAssistantTool(
        tool_name="open_app",
        description="Open a safe allowlisted local application.",
        supported_intents=("open_app",),
        capabilities=("apps", "launch"),
        required_parameters=("app",),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="allowlisted_app",
        confirmation_required=True,
        executor=_local_action("open_app"),
        safe_failure_message="I understood the app-open intent, but the open-app adapter failed.",
    ),
    "close_tracked_app": LocalAssistantTool(
        tool_name="close_tracked_app",
        description="Close only an assistant-tracked allowlisted application process.",
        supported_intents=("close_target", "close_current_window"),
        capabilities=("apps", "windows", "close"),
        required_parameters=("app",),
        optional_parameters=("assistant_tracked", "pid"),
        risk_level=RISK_MEDIUM_CONFIRMATION,
        permission_requirement="assistant_tracked_process",
        confirmation_required=True,
        executor=_local_action("close_app"),
        safe_failure_message="I understood the close-app intent, but the close-app adapter failed.",
    ),
    "system_diagnostics": LocalAssistantTool(
        tool_name="system_diagnostics",
        description="Run read-only local system and backend diagnostics.",
        supported_intents=("system_diagnostics",),
        capabilities=("diagnostics", "health", "performance"),
        risk_level=RISK_SAFE_READ,
        permission_requirement="none",
        executor=_execute_diagnostics,
    ),
    "create_reminder": LocalAssistantTool(
        tool_name="create_reminder",
        description="Store a structured local reminder.",
        supported_intents=("create_reminder", "meeting_reminder"),
        capabilities=("reminders", "tasks"),
        required_parameters=("reminder_text", "time_text"),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="local_productivity_store",
        executor=_execute_create_reminder,
    ),
    "list_reminders": LocalAssistantTool(
        tool_name="list_reminders",
        description="List local pending or due reminders without changing them.",
        supported_intents=("list_reminders",),
        capabilities=("reminders", "tasks", "read"),
        optional_parameters=("status",),
        risk_level=RISK_SAFE_READ,
        permission_requirement="local_productivity_store",
        executor=_execute_list_reminders,
    ),
    "complete_reminder": LocalAssistantTool(
        tool_name="complete_reminder",
        description="Mark one matching local reminder as done.",
        supported_intents=("complete_reminder",),
        capabilities=("reminders", "tasks", "done"),
        required_parameters=("reminder_query",),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="local_productivity_store",
        executor=_execute_complete_reminder,
    ),
    "cancel_reminder": LocalAssistantTool(
        tool_name="cancel_reminder",
        description="Cancel one matching local reminder after resolving ambiguity.",
        supported_intents=("cancel_reminder",),
        capabilities=("reminders", "tasks", "cancel"),
        required_parameters=("reminder_query",),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="local_productivity_store",
        executor=_execute_cancel_reminder,
    ),
    "check_due_reminders": LocalAssistantTool(
        tool_name="check_due_reminders",
        description="Check pending reminders and surface local notifications for newly due items.",
        supported_intents=("check_due_reminders",),
        capabilities=("reminders", "notifications", "scheduler"),
        risk_level=RISK_SAFE_READ,
        permission_requirement="local_productivity_store",
        executor=_execute_check_due_reminders,
    ),
    "startup_status": LocalAssistantTool(
        tool_name="startup_status",
        description="Show current user Windows startup status and startup command path.",
        supported_intents=("startup_status",),
        capabilities=("startup", "windows", "autostart"),
        risk_level=RISK_SAFE_READ,
        permission_requirement="none",
        executor=_execute_startup_status,
    ),
    "enable_startup": LocalAssistantTool(
        tool_name="enable_startup",
        description="Create or refresh a current-user Windows Startup folder entry for GrandpaAssistant.",
        supported_intents=("enable_startup",),
        capabilities=("startup", "windows", "autostart"),
        risk_level=RISK_MEDIUM_CONFIRMATION,
        permission_requirement="explicit_user_confirmation",
        confirmation_required=True,
        executor=_execute_enable_startup,
        safe_failure_message="I understood startup enable, but the startup adapter failed.",
    ),
    "disable_startup": LocalAssistantTool(
        tool_name="disable_startup",
        description="Remove GrandpaAssistant's current-user Windows Startup folder entry.",
        supported_intents=("disable_startup",),
        capabilities=("startup", "windows", "autostart"),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="current_user_startup_folder",
        executor=_execute_disable_startup,
        safe_failure_message="I understood startup disable, but the startup adapter failed.",
    ),
    "voice_runtime_status": LocalAssistantTool(
        tool_name="voice_runtime_status",
        description="Show local wake-word voice runtime status without opening the microphone.",
        supported_intents=("voice_runtime_status",),
        capabilities=("voice", "wake_word", "runtime"),
        risk_level=RISK_SAFE_READ,
        permission_requirement="none",
        executor=_execute_voice_runtime_status,
    ),
    "enable_voice_runtime": LocalAssistantTool(
        tool_name="enable_voice_runtime",
        description="Enable managed local wake-word voice runtime in this process.",
        supported_intents=("enable_voice_runtime",),
        capabilities=("voice", "wake_word", "runtime"),
        risk_level=RISK_MEDIUM_CONFIRMATION,
        permission_requirement="explicit_user_confirmation",
        confirmation_required=True,
        executor=_execute_enable_voice_runtime,
        safe_failure_message="I understood voice runtime enable, but the voice runtime adapter failed.",
    ),
    "disable_voice_runtime": LocalAssistantTool(
        tool_name="disable_voice_runtime",
        description="Disable managed local wake-word voice runtime in this process.",
        supported_intents=("disable_voice_runtime",),
        capabilities=("voice", "wake_word", "runtime"),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="local_runtime_control",
        executor=_execute_disable_voice_runtime,
        safe_failure_message="I understood voice runtime disable, but the voice runtime adapter failed.",
    ),
    "remember_this": LocalAssistantTool(
        tool_name="remember_this",
        description="Store a structured long-term memory after filtering sensitive content.",
        supported_intents=("remember_this",),
        capabilities=("memory", "preferences", "personalization"),
        required_parameters=("memory_text",),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="local_memory_store",
        executor=_execute_remember_this,
        safe_failure_message="I understood the memory intent, but the memory adapter failed.",
    ),
    "list_memories": LocalAssistantTool(
        tool_name="list_memories",
        description="List structured long-term memories the user can inspect.",
        supported_intents=("list_memories",),
        capabilities=("memory", "preferences", "read"),
        risk_level=RISK_SAFE_READ,
        permission_requirement="local_memory_store",
        executor=_execute_list_memories,
    ),
    "forget_memory": LocalAssistantTool(
        tool_name="forget_memory",
        description="Delete one matching structured long-term memory.",
        supported_intents=("forget_memory",),
        capabilities=("memory", "preferences", "forget"),
        required_parameters=("memory_query",),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="local_memory_store",
        executor=_execute_forget_memory,
        safe_failure_message="I understood the forget-memory intent, but the memory adapter failed.",
    ),
    "memory_status": LocalAssistantTool(
        tool_name="memory_status",
        description="Show safe local long-term memory status without exposing hidden data.",
        supported_intents=("memory_status",),
        capabilities=("memory", "status"),
        risk_level=RISK_SAFE_READ,
        permission_requirement="none",
        executor=_execute_memory_status,
    ),
    "memory_opt_out": LocalAssistantTool(
        tool_name="memory_opt_out",
        description="Respect a user request not to save the current information.",
        supported_intents=("memory_opt_out",),
        capabilities=("memory", "privacy"),
        risk_level=RISK_SAFE_READ,
        permission_requirement="none",
        executor=_execute_memory_opt_out,
    ),
    "review_memories": LocalAssistantTool(
        tool_name="review_memories",
        description="Review long-term memories and summarize quality, conflicts, and stale items.",
        supported_intents=("review_memories",),
        capabilities=("memory", "review", "cleanup"),
        risk_level=RISK_SAFE_READ,
        permission_requirement="local_memory_store",
        executor=_execute_review_memories,
    ),
    "cleanup_memories": LocalAssistantTool(
        tool_name="cleanup_memories",
        description="Suggest stale or low-quality memories for cleanup without deleting them.",
        supported_intents=("cleanup_memories",),
        capabilities=("memory", "cleanup", "review"),
        risk_level=RISK_SAFE_READ,
        permission_requirement="local_memory_store",
        executor=_execute_cleanup_memories,
    ),
    "update_memory": LocalAssistantTool(
        tool_name="update_memory",
        description="Explicitly update one structured memory key.",
        supported_intents=("update_memory",),
        capabilities=("memory", "preferences", "update"),
        required_parameters=("key", "value"),
        optional_parameters=("category",),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="local_memory_store",
        executor=_execute_update_memory,
    ),
    "memory_conflicts": LocalAssistantTool(
        tool_name="memory_conflicts",
        description="Show unresolved memory conflicts without changing memory.",
        supported_intents=("memory_conflicts",),
        capabilities=("memory", "conflicts", "review"),
        risk_level=RISK_SAFE_READ,
        permission_requirement="local_memory_store",
        executor=_execute_memory_conflicts,
    ),
    "resolve_memory_conflict": LocalAssistantTool(
        tool_name="resolve_memory_conflict",
        description="Resolve one pending memory conflict from short-term conversation context.",
        supported_intents=("resolve_memory_conflict",),
        capabilities=("memory", "conflicts", "update"),
        required_parameters=("memory_id", "decision"),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="local_memory_store",
        executor=_execute_resolve_memory_conflict,
    ),
    "create_task": LocalAssistantTool(
        tool_name="create_task",
        description="Store a structured local task.",
        supported_intents=("create_task",),
        capabilities=("tasks", "todo"),
        required_parameters=("task_text",),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="local_productivity_store",
        executor=_execute_create_task,
    ),
    "active_window_context": LocalAssistantTool(
        tool_name="active_window_context",
        description="Read safe active-window metadata for context-aware planning.",
        supported_intents=("active_window_context",),
        capabilities=("screen", "window", "context"),
        risk_level=RISK_SAFE_READ,
        permission_requirement="none",
        executor=_execute_active_window_context,
    ),
    "screen_read": LocalAssistantTool(
        tool_name="screen_read",
        description="Capture and summarize the screen only after explicit user request.",
        supported_intents=("screen_read",),
        capabilities=("screen", "screenshot", "ocr"),
        risk_level=RISK_SAFE_READ,
        permission_requirement="explicit_user_request",
        executor=_execute_screen_read,
        safe_failure_message="I understood the screen-read intent, but the screen awareness adapter failed.",
    ),
    "media_key_control": LocalAssistantTool(
        tool_name="media_key_control",
        description="Send safe local media-key controls such as play or pause.",
        supported_intents=("media_control",),
        capabilities=("media", "audio", "playback"),
        required_parameters=("operation",),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="active_media_context",
        executor=_local_action("media_key"),
    ),
    "open_website": LocalAssistantTool(
        tool_name="open_website",
        description="Open an http or https URL in the default browser.",
        supported_intents=("open_url", "play_media_search"),
        capabilities=("browser", "web", "search"),
        required_parameters=("url",),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="safe_url",
        executor=_local_action("open_url"),
    ),
    "search_selected_google": LocalAssistantTool(
        tool_name="search_selected_google",
        description="Search selected or clipboard text on Google without reading hidden content.",
        supported_intents=("search_selected_google",),
        capabilities=("browser", "search", "clipboard"),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="clipboard_available",
        executor=_execute_search_selected_google,
    ),
    "create_folder": LocalAssistantTool(
        tool_name="create_folder",
        description="Create a folder under configured safe local roots.",
        supported_intents=("create_folder",),
        capabilities=("files", "folders"),
        required_parameters=("path",),
        risk_level=RISK_SAFE_LOCAL_ACTION,
        permission_requirement="safe_local_path",
        executor=_local_action("create_folder"),
    ),
    "capability_discovery": LocalAssistantTool(
        tool_name="capability_discovery",
        description="List registered local assistant capabilities safely.",
        supported_intents=("capability_discovery",),
        capabilities=("help", "capabilities", "tools"),
        risk_level=RISK_SAFE_READ,
        permission_requirement="none",
        executor=_execute_capability_discovery,
    ),
    "unsupported_action": LocalAssistantTool(
        tool_name="unsupported_action",
        description="Explain unsupported or blocked capabilities clearly.",
        supported_intents=("unsupported_action",),
        capabilities=("missing_adapter", "unsupported", "blocked"),
        risk_level=RISK_BLOCKED,
        permission_requirement="blocked_or_missing_adapter",
        executor=_execute_unsupported_action,
        safe_failure_message="I understood the request, but the required adapter is not available.",
    ),
}


def get_tool(tool_name: str) -> LocalAssistantTool | None:
    return _TOOLS.get(compact_text(tool_name).lower())


def list_available_tools() -> list[dict[str, Any]]:
    return [_tool_summary(tool) for tool in _TOOLS.values()]


def list_tools_by_intent(intent: str) -> list[dict[str, Any]]:
    normalized = compact_text(intent).lower()
    return [_tool_summary(tool) for tool in _TOOLS.values() if normalized in tool.supported_intents or normalized in tool.capabilities]


def explain_missing_tool(intent: str) -> dict[str, Any]:
    capability = compact_text(intent) or "that action"
    alternatives = []
    for tool in _TOOLS.values():
        alternatives.extend(tool.alternatives)
    message = (
        f"I understood that you want {capability}, but GrandpaAssistant does not have a safe registered adapter for that capability yet. "
        "A tool needs to be added to the personal assistant registry with permissions and an executor before I can do it."
    )
    return {
        "intent": capability,
        "missing_adapter": capability.replace(" ", "_"),
        "safe_alternatives": sorted(set(alternatives)),
        "message": message,
    }


def execute_registered_tool(tool_name: str, params: dict[str, Any] | None = None, context: Any | None = None) -> dict[str, Any]:
    tool = get_tool(tool_name)
    if tool is None:
        explanation = explain_missing_tool(tool_name)
        return {"ok": False, "action": compact_text(tool_name), "message": explanation["message"], "data": {"missing_adapter": explanation["missing_adapter"]}}
    validation = validate_tool_parameters(tool.tool_name, params)
    if not validation["ok"]:
        missing = ", ".join(validation["missing_parameters"])
        return {
            "ok": False,
            "action": tool.tool_name,
            "message": f"I understood the intent, but {tool.tool_name} needs: {missing}.",
            "data": {"missing_parameters": validation["missing_parameters"]},
        }
    if not tool.is_available():
        return {"ok": False, "action": tool.tool_name, "message": tool.safe_failure_message, "data": {"missing_adapter": tool.tool_name}}
    if tool.executor is None:
        return {"ok": False, "action": tool.tool_name, "message": tool.safe_failure_message, "data": {"missing_adapter": tool.tool_name}}
    try:
        result = tool.executor(params or {}, context)
    except Exception as error:
        result = {"ok": False, "action": tool.tool_name, "message": f"{tool.safe_failure_message}: {compact_text(error)}", "data": {}}
    result.setdefault("action", tool.tool_name)
    result.setdefault("data", {})
    return result


def tool_debug_snapshot(tool_name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    tool = get_tool(tool_name)
    if tool is None:
        return {"tool_name": compact_text(tool_name), "available": False, "missing_parameters": [], "risk_level": RISK_BLOCKED}
    validation = validate_tool_parameters(tool.tool_name, params)
    return {
        "tool_name": tool.tool_name,
        "available": tool.is_available(),
        "missing_parameters": validation["missing_parameters"],
        "risk_level": tool.risk_level,
        "permission_requirement": tool.permission_requirement,
        "confirmation_required": tool.confirmation_required,
    }


def _tool_summary(tool: LocalAssistantTool) -> dict[str, Any]:
    return {
        "tool_name": tool.tool_name,
        "description": tool.description,
        "supported_intents": list(tool.supported_intents),
        "capabilities": list(tool.capabilities),
        "required_parameters": list(tool.required_parameters),
        "optional_parameters": list(tool.optional_parameters),
        "risk_level": tool.risk_level,
        "permission_requirement": tool.permission_requirement,
        "confirmation_required": tool.confirmation_required,
        "platform_support": list(tool.platform_support),
        "available": tool.is_available(),
        "safe_failure_message": tool.safe_failure_message,
    }
