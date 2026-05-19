from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from security.permission_engine import classify_command

from .context import AssistantActionPlan, ConversationContext, compact_text
from .intent_engine import IntentCandidate
from . import memory_manager
from .tool_registry import get_tool


def _documents_dir() -> str:
    return str(Path.home() / "Documents")


def _folder_path(name: str, parent: str = "") -> str:
    folder_name = compact_text(name).strip("\"'")
    if not parent:
        parent = _documents_dir()
    parent_clean = compact_text(parent).strip("\"'")
    if parent_clean.lower() in {"documents", "my documents"}:
        parent_clean = _documents_dir()
    if parent_clean.lower() == "desktop":
        parent_clean = str(Path.home() / "Desktop")
    return os.path.join(os.path.expanduser(parent_clean), folder_name)


def _permission(command: str) -> dict[str, Any]:
    try:
        return classify_command(command)
    except Exception:
        return {"level": "LOW", "requires_confirmation": False, "reason": "Permission classifier unavailable."}


def _command_text(intent: IntentCandidate) -> str:
    if intent.intent == "open_app":
        return f"open {intent.slots.get('app') or 'app'}"
    if intent.intent == "open_url":
        return f"open {intent.slots.get('url') or 'url'}"
    if intent.intent == "create_folder":
        return "create folder"
    if intent.intent == "create_reminder":
        return "add reminder"
    if intent.intent == "list_reminders":
        return "list reminders"
    if intent.intent == "complete_reminder":
        return "complete reminder"
    if intent.intent == "cancel_reminder":
        return "cancel reminder"
    if intent.intent == "check_due_reminders":
        return "check due reminders"
    if intent.intent == "enable_startup":
        return "enable startup"
    if intent.intent == "disable_startup":
        return "disable startup"
    if intent.intent == "startup_status":
        return "startup status"
    if intent.intent == "enable_voice_runtime":
        return "enable voice runtime"
    if intent.intent == "disable_voice_runtime":
        return "disable voice runtime"
    if intent.intent == "voice_runtime_status":
        return "voice runtime status"
    if intent.intent == "remember_this":
        return "remember user preference"
    if intent.intent == "forget_memory":
        return "forget user memory"
    if intent.intent == "list_memories":
        return "list user memories"
    if intent.intent == "memory_status":
        return "memory status"
    if intent.intent == "review_memories":
        return "review memories"
    if intent.intent == "cleanup_memories":
        return "cleanup memories"
    if intent.intent == "update_memory":
        return "update memory"
    if intent.intent == "memory_conflicts":
        return "memory conflicts"
    if intent.intent == "resolve_memory_conflict":
        return "resolve memory conflict"
    if intent.intent == "create_task":
        return "add task"
    if intent.intent == "system_diagnostics":
        return "system diagnostics"
    return intent.normalized_message or intent.intent


def _pending_confirmation_plan(context: ConversationContext, message: str) -> AssistantActionPlan | None:
    pending = context.pending_plan
    if pending and pending.requires_confirmation and pending.action:
        pending.source_message = message
        pending.requires_confirmation = False
        return pending
    return None


def _active_window(screen_context: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(screen_context, dict) and isinstance(screen_context.get("active_window"), dict):
        return screen_context["active_window"]
    return {}


def build_action_plan(intent: IntentCandidate, context: ConversationContext, message: str, *, screen_context: dict[str, Any] | None = None) -> AssistantActionPlan | None:
    if intent.intent in {"empty", "unknown"}:
        return None
    if intent.intent == "confirmation_yes" or intent.intent == "follow_up_execute":
        return _pending_confirmation_plan(context, message)
    if intent.intent == "confirmation_no":
        return AssistantActionPlan(intent="cancel_pending", source_message=message)
    if intent.intent == "context_question":
        return AssistantActionPlan(intent="context_question", source_message=message)
    if intent.intent == "capability_discovery":
        return AssistantActionPlan(
            intent="capability_discovery",
            action="capability_discovery",
            tool_name="capability_discovery",
            target="registered tools",
            params={},
            source_message=message,
        )
    if intent.intent == "unsupported_action":
        capability = compact_text(intent.slots.get("capability")) or "that action"
        return AssistantActionPlan(
            intent="unsupported_action",
            action="unsupported_action",
            tool_name="unsupported_action",
            target=capability,
            params={"capability": capability},
            risk_level="BLOCKED",
            reason="No safe registered adapter is available for this capability.",
            source_message=message,
        )
    if intent.intent == "memory_opt_out":
        return AssistantActionPlan(
            intent="memory_opt_out",
            action="memory_opt_out",
            tool_name="memory_opt_out",
            target="memory",
            params={},
            source_message=message,
        )
    if intent.intent == "resolve_memory_conflict":
        decision = compact_text(intent.slots.get("decision"))
        memory_id = compact_text(intent.slots.get("memory_id"))
        return AssistantActionPlan(
            intent="resolve_memory_conflict",
            action="resolve_memory_conflict",
            tool_name="resolve_memory_conflict",
            target=memory_id,
            params={"memory_id": memory_id, "decision": decision},
            missing_details=[] if memory_id and decision else ["memory_conflict_decision"],
            source_message=message,
        )
    if intent.intent == "close_target":
        target = compact_text(intent.slots.get("target")) or context.target_app or context.target_object
        missing = [] if target else ["target"]
        tracked_pid = None
        last_action = context.last_executed_action if isinstance(context.last_executed_action, dict) else {}
        if last_action.get("action") == "open_app" and last_action.get("target") == target:
            data = last_action.get("data") if isinstance(last_action.get("data"), dict) else {}
            tracked_pid = data.get("pid")
        plan = AssistantActionPlan(
            intent="close_target",
            action="close_app",
            tool_name="close_tracked_app",
            target=target,
            params={"app": target, "assistant_tracked": bool(target and target == context.target_app), "pid": tracked_pid},
            missing_details=missing,
            source_message=message,
        )
        if target in {"notepad", "paint", "mspaint"} and not missing:
            plan.requires_confirmation = True
            plan.risk_level = "MEDIUM"
            plan.reason = "The app may contain unsaved work."
        return plan
    if intent.intent == "close_current_window":
        active = _active_window(screen_context)
        app_name = compact_text(active.get("app_name"))
        kind = compact_text(active.get("kind"))
        target = context.target_app or app_name
        plan = AssistantActionPlan(
            intent="close_current_window",
            action="close_app",
            tool_name="close_tracked_app",
            target=target,
            params={"app": target.lower(), "assistant_tracked": bool(target and target.lower() == context.target_app), "pid": (context.last_executed_action.get("data") or {}).get("pid") if isinstance(context.last_executed_action, dict) else None},
            missing_details=[] if target else ["target"],
            requires_confirmation=True,
            risk_level="MEDIUM",
            reason=f"Closing current {kind or 'window'} requires confirmation and exact assistant tracking.",
            source_message=message,
        )
        return plan
    if intent.intent == "open_app":
        app = compact_text(intent.slots.get("app"))
        if app.lower() in {"my editor", "editor", "code editor", "my code editor", "preferred editor"}:
            editor = memory_manager.query_memories("", category="favorite_apps", key="preferred_code_editor", limit=1)
            if editor:
                app = compact_text(editor[0].get("value")) or app
        plan = AssistantActionPlan(
            intent="open_app",
            action="open_app",
            tool_name="open_app",
            target=app,
            params={"app": app},
            missing_details=list(intent.missing_details),
            source_message=message,
        )
    elif intent.intent == "open_url":
        url = compact_text(intent.slots.get("url"))
        plan = AssistantActionPlan(
            intent="open_url",
            action="open_url",
            tool_name="open_website",
            target=url,
            params={"url": url},
            missing_details=list(intent.missing_details),
            source_message=message,
        )
    elif intent.intent == "create_folder":
        name = compact_text(intent.slots.get("name"))
        parent = compact_text(intent.slots.get("parent"))
        params = {"path": _folder_path(name, parent)} if name else {}
        plan = AssistantActionPlan(
            intent="create_folder",
            action="create_folder",
            tool_name="create_folder",
            target=name,
            params=params,
            missing_details=list(intent.missing_details),
            source_message=message,
        )
    elif intent.intent == "create_reminder":
        reminder_text = compact_text(intent.slots.get("reminder_text") or context.reminder_details.get("reminder_text"))
        time_text = compact_text(intent.slots.get("time_text") or context.reminder_details.get("time_text"))
        missing = []
        if not reminder_text:
            missing.append("reminder_text")
        if not time_text:
            missing.append("reminder_time")
        plan = AssistantActionPlan(
            intent="create_reminder",
            action="create_reminder",
            tool_name="create_reminder",
            target=reminder_text,
            params={"reminder_text": reminder_text, "time_text": time_text},
            missing_details=missing,
            source_message=message,
        )
    elif intent.intent == "list_reminders":
        status = compact_text(intent.slots.get("status")) or "pending"
        plan = AssistantActionPlan(
            intent="list_reminders",
            action="list_reminders",
            tool_name="list_reminders",
            target=status,
            params={"status": status},
            source_message=message,
        )
    elif intent.intent == "complete_reminder":
        query = compact_text(intent.slots.get("reminder_query"))
        plan = AssistantActionPlan(
            intent="complete_reminder",
            action="complete_reminder",
            tool_name="complete_reminder",
            target=query,
            params={"reminder_query": query},
            missing_details=[] if query else ["reminder_query"],
            source_message=message,
        )
    elif intent.intent == "cancel_reminder":
        query = compact_text(intent.slots.get("reminder_query"))
        plan = AssistantActionPlan(
            intent="cancel_reminder",
            action="cancel_reminder",
            tool_name="cancel_reminder",
            target=query,
            params={"reminder_query": query},
            missing_details=[] if query else ["reminder_query"],
            source_message=message,
        )
    elif intent.intent == "check_due_reminders":
        plan = AssistantActionPlan(
            intent="check_due_reminders",
            action="check_due_reminders",
            tool_name="check_due_reminders",
            target="reminders",
            params={},
            source_message=message,
        )
    elif intent.intent == "enable_startup":
        plan = AssistantActionPlan(
            intent="enable_startup",
            action="enable_startup",
            tool_name="enable_startup",
            target="windows startup",
            params={},
            requires_confirmation=True,
            risk_level="medium_confirmation",
            reason="Startup enable changes the current user's Windows Startup folder.",
            source_message=message,
        )
    elif intent.intent == "disable_startup":
        plan = AssistantActionPlan(
            intent="disable_startup",
            action="disable_startup",
            tool_name="disable_startup",
            target="windows startup",
            params={},
            source_message=message,
        )
    elif intent.intent == "startup_status":
        plan = AssistantActionPlan(
            intent="startup_status",
            action="startup_status",
            tool_name="startup_status",
            target="windows startup",
            params={},
            source_message=message,
        )
    elif intent.intent == "enable_voice_runtime":
        plan = AssistantActionPlan(
            intent="enable_voice_runtime",
            action="enable_voice_runtime",
            tool_name="enable_voice_runtime",
            target="voice runtime",
            params={},
            requires_confirmation=True,
            risk_level="medium_confirmation",
            reason="Voice runtime starts local wake-word listening.",
            source_message=message,
        )
    elif intent.intent == "disable_voice_runtime":
        plan = AssistantActionPlan(
            intent="disable_voice_runtime",
            action="disable_voice_runtime",
            tool_name="disable_voice_runtime",
            target="voice runtime",
            params={},
            source_message=message,
        )
    elif intent.intent == "voice_runtime_status":
        plan = AssistantActionPlan(
            intent="voice_runtime_status",
            action="voice_runtime_status",
            tool_name="voice_runtime_status",
            target="voice runtime",
            params={},
            source_message=message,
        )
    elif intent.intent == "remember_this":
        memory_text = compact_text(intent.slots.get("memory_text")) or message
        plan = AssistantActionPlan(
            intent="remember_this",
            action="remember_this",
            tool_name="remember_this",
            target="memory",
            params={"memory_text": memory_text, "implicit": bool(intent.slots.get("implicit"))},
            missing_details=[] if memory_text else ["memory_text"],
            source_message=message,
        )
    elif intent.intent == "list_memories":
        plan = AssistantActionPlan(
            intent="list_memories",
            action="list_memories",
            tool_name="list_memories",
            target="memory",
            params={},
            source_message=message,
        )
    elif intent.intent == "forget_memory":
        query = compact_text(intent.slots.get("memory_query"))
        plan = AssistantActionPlan(
            intent="forget_memory",
            action="forget_memory",
            tool_name="forget_memory",
            target=query,
            params={"memory_query": query},
            missing_details=[] if query else ["memory_query"],
            source_message=message,
        )
    elif intent.intent == "memory_status":
        plan = AssistantActionPlan(
            intent="memory_status",
            action="memory_status",
            tool_name="memory_status",
            target="memory",
            params={},
            source_message=message,
        )
    elif intent.intent == "review_memories":
        plan = AssistantActionPlan(
            intent="review_memories",
            action="review_memories",
            tool_name="review_memories",
            target="memory",
            params={},
            source_message=message,
        )
    elif intent.intent == "cleanup_memories":
        plan = AssistantActionPlan(
            intent="cleanup_memories",
            action="cleanup_memories",
            tool_name="cleanup_memories",
            target="memory",
            params={},
            source_message=message,
        )
    elif intent.intent == "memory_conflicts":
        plan = AssistantActionPlan(
            intent="memory_conflicts",
            action="memory_conflicts",
            tool_name="memory_conflicts",
            target="memory",
            params={},
            source_message=message,
        )
    elif intent.intent == "update_memory":
        category = compact_text(intent.slots.get("category"))
        key = compact_text(intent.slots.get("key"))
        value = compact_text(intent.slots.get("value"))
        missing = []
        if not key:
            missing.append("memory_key")
        if not value:
            missing.append("memory_value")
        plan = AssistantActionPlan(
            intent="update_memory",
            action="update_memory",
            tool_name="update_memory",
            target=key,
            params={"category": category, "key": key, "value": value},
            missing_details=missing,
            source_message=message,
        )
    elif intent.intent == "meeting_reminder":
        date_text = compact_text(intent.slots.get("date_text") or context.reminder_details.get("date_text"))
        topic = compact_text(intent.slots.get("topic") or context.reminder_details.get("topic"))
        time_text = compact_text(intent.slots.get("time_text") or context.reminder_details.get("time_text"))
        missing = []
        if not date_text:
            missing.append("meeting_date")
        if not time_text or not topic:
            missing.append("meeting_time_topic")
        title = compact_text(f"{topic or 'meeting'}")
        plan = AssistantActionPlan(
            intent="meeting_reminder",
            action="create_reminder",
            tool_name="create_reminder",
            target=title,
            params={
                "reminder_text": title,
                "time_text": compact_text(f"{date_text} {time_text}"),
                "topic": topic,
                "date_text": date_text,
                "source_conversation_summary": "User mentioned an upcoming meeting and completed missing reminder details.",
            },
            missing_details=missing,
            source_message=message,
        )
    elif intent.intent == "create_task":
        task_text = compact_text(intent.slots.get("task_text"))
        plan = AssistantActionPlan(
            intent="create_task",
            action="create_task",
            tool_name="create_task",
            target=task_text,
            params={"task_text": task_text},
            missing_details=list(intent.missing_details),
            source_message=message,
        )
    elif intent.intent == "system_diagnostics":
        plan = AssistantActionPlan(
            intent="system_diagnostics",
            action="system_diagnostics",
            tool_name="system_diagnostics",
            target="backend",
            params={},
            source_message=message,
        )
    elif intent.intent == "media_control":
        active = _active_window(screen_context)
        activity = compact_text(active.get("activity"))
        operation = compact_text(intent.slots.get("operation")) or "pause"
        if activity != "media":
            plan = AssistantActionPlan(
                intent="media_control",
                action="media_key",
                tool_name="media_key_control",
                target=active.get("app_name") or "media",
                params={"operation": operation},
                missing_details=["media_context"],
                source_message=message,
                reason="No active media app or video context was detected.",
            )
        else:
            plan = AssistantActionPlan(
                intent="media_control",
                action="media_key",
                tool_name="media_key_control",
                target=active.get("app_name") or active.get("domain") or "media",
                params={"operation": operation},
                source_message=message,
                reason="Active window looks like media context.",
            )
    elif intent.intent == "screen_read":
        plan = AssistantActionPlan(
            intent="screen_read",
            action="screen_read",
            tool_name="screen_read",
            target="screen",
            params={},
            source_message=message,
            reason="Explicit screen analysis request.",
        )
    elif intent.intent == "search_selected_google":
        plan = AssistantActionPlan(
            intent="search_selected_google",
            action="search_selected_google",
            tool_name="search_selected_google",
            target="selected text",
            params={},
            source_message=message,
            reason="Use clipboard or selected text only with safe local browser opening.",
        )
    elif intent.intent == "play_media_search":
        query = compact_text(intent.slots.get("query"))
        if not query:
            favorite_music = memory_manager.query_memories("", category="user_preferences", key="favorite_music", limit=1)
            query = compact_text(favorite_music[0].get("value")) if favorite_music else ""
        query = query or "relaxing music"
        active = _active_window(screen_context)
        if compact_text(active.get("activity")) == "media":
            url = "https://www.youtube.com/results?search_query=" + quote_plus(query)
        else:
            url = "https://www.youtube.com/results?search_query=" + quote_plus(query)
        plan = AssistantActionPlan(
            intent="play_media_search",
            action="open_url",
            tool_name="open_website",
            target=query,
            params={"url": url},
            source_message=message,
            reason="Open a safe YouTube search for requested music; no autoplay or account action.",
        )
    elif intent.intent == "adjust_volume":
        operation = compact_text(intent.slots.get("operation"))
        plan = AssistantActionPlan(
            intent="adjust_volume",
            action="adjust_volume",
            tool_name="volume_control",
            target="system volume",
            params={"operation": operation, "step": 10},
            missing_details=[] if operation else ["volume_operation"],
            source_message=message,
        )
    else:
        return None

    permission = _permission(_command_text(intent))
    plan.risk_level = permission.get("level", "LOW")
    plan.requires_confirmation = bool(permission.get("requires_confirmation")) and not plan.missing_details
    plan.reason = compact_text(permission.get("reason"))
    tool = get_tool(plan.tool_name)
    if tool is not None:
        if plan.risk_level in {"", "LOW"}:
            plan.risk_level = tool.risk_level
        if tool.confirmation_required and not plan.missing_details:
            plan.requires_confirmation = True
            if not plan.reason:
                plan.reason = tool.permission_requirement
    return plan
