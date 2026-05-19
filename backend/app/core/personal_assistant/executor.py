from __future__ import annotations

import datetime
from typing import Any

try:
    from services import local_action_executor
except ImportError:  # pragma: no cover
    from backend.app.services import local_action_executor

try:
    from shared.backend_stability import build_backend_stability_payload, format_backend_stability_text
except ImportError:  # pragma: no cover
    try:
        from backend_stability import build_backend_stability_payload, format_backend_stability_text
    except ImportError:  # pragma: no cover
        build_backend_stability_payload = None
        format_backend_stability_text = None

try:
    from shared.productivity_store import load_task_payload, save_task_payload
except ImportError:  # pragma: no cover
    from productivity_store import load_task_payload, save_task_payload

from .context import AssistantActionPlan, ConversationContext, compact_text
from . import reminder_engine
from .tool_registry import execute_registered_tool, tool_debug_snapshot

try:
    from . import screen_context as screen_context_module
except Exception:  # pragma: no cover
    screen_context_module = None

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional runtime metric dependency
    psutil = None


def _default_task_payload() -> dict[str, list[dict[str, Any]]]:
    return {"tasks": [], "reminders": []}


def _parse_due_datetime(time_text: str) -> datetime.datetime | None:
    return reminder_engine.parse_due_datetime(time_text)


def _save_reminder(reminder_text: str, time_text: str) -> str:
    return _save_structured_reminder({"reminder_text": reminder_text, "time_text": time_text})


def _save_structured_reminder(details: dict[str, Any]) -> str:
    return _create_structured_reminder_result(details).get("message", "Reminder saved.")


def _create_structured_reminder_result(details: dict[str, Any]) -> dict[str, Any]:
    return reminder_engine.create_reminder(
        details,
        load_payload=load_task_payload,
        save_payload=save_task_payload,
    )


def _list_reminders_result(status: str = "pending") -> dict[str, Any]:
    return reminder_engine.list_reminders(status=status, load_payload=load_task_payload)


def _complete_reminder_result(query: str) -> dict[str, Any]:
    return reminder_engine.complete_reminder(query, load_payload=load_task_payload, save_payload=save_task_payload)


def _cancel_reminder_result(query: str) -> dict[str, Any]:
    return reminder_engine.cancel_reminder(query, load_payload=load_task_payload, save_payload=save_task_payload)


def _check_due_reminders_result(now: datetime.datetime | None = None) -> dict[str, Any]:
    return reminder_engine.check_due_reminders(now=now, load_payload=load_task_payload, save_payload=save_task_payload)


def _save_task(task_text: str) -> str:
    title = compact_text(task_text)
    payload = load_task_payload(default_factory=_default_task_payload)
    tasks = payload.setdefault("tasks", [])
    tasks.append(
        {
            "title": title,
            "completed": False,
            "recurrence": None,
            "priority": "normal",
            "category": "",
            "created_at": datetime.datetime.now().isoformat(),
        }
    )
    save_task_payload(payload, default_factory=_default_task_payload)
    return f"Task added: {title}"


def _diagnostics_summary() -> str:
    metric_parts = []
    recommendations = []
    if psutil is None:
        metric_parts.extend(
            [
                "CPU usage: not available.",
                "RAM usage: not available.",
                "Disk usage: not available.",
                "Top processes: not available.",
                "Battery: not available.",
            ]
        )
    else:
        try:
            cpu = psutil.cpu_percent(interval=0.05)
            metric_parts.append(f"CPU usage: {cpu:.0f} percent.")
            if cpu >= 85:
                recommendations.append("CPU is high; close heavy apps or wait for background work to finish.")
        except Exception:
            metric_parts.append("CPU usage: not available.")
        try:
            ram = psutil.virtual_memory()
            metric_parts.append(f"RAM usage: {ram.percent:.0f} percent.")
            if ram.percent >= 85:
                recommendations.append("RAM is high; close unused browser tabs or apps.")
        except Exception:
            metric_parts.append("RAM usage: not available.")
        try:
            disk = psutil.disk_usage("/")
            metric_parts.append(f"Disk usage: {disk.percent:.0f} percent.")
            if disk.percent >= 90:
                recommendations.append("Disk is nearly full; review Downloads and large files.")
        except Exception:
            metric_parts.append("Disk usage: not available.")
        try:
            processes = []
            for process in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
                try:
                    info = process.info
                    processes.append((float(info.get("cpu_percent") or 0), float(info.get("memory_percent") or 0), compact_text(info.get("name"))))
                except Exception:
                    continue
            processes.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
            names = [name for _cpu, _mem, name in processes[:3] if name]
            metric_parts.append("Top processes: " + (", ".join(names) if names else "not available") + ".")
        except Exception:
            metric_parts.append("Top processes: not available.")
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                metric_parts.append("Battery: not available.")
            else:
                state = "charging" if battery.power_plugged else "not charging"
                metric_parts.append(f"Battery: {battery.percent:.0f} percent, {state}.")
        except Exception:
            metric_parts.append("Battery: not available.")

    if build_backend_stability_payload is None or format_backend_stability_text is None:
        backend_text = "Backend health: not available because the backend stability adapter is missing."
    else:
        try:
            payload = build_backend_stability_payload()
            backend_text = "Backend health: " + format_backend_stability_text(payload)
        except Exception as error:
            backend_text = f"Backend health: not available ({compact_text(error)})."
    if not recommendations:
        recommendations.append("Recommendation: system metrics do not show an obvious critical issue from the available checks.")
    return "System diagnostics complete. " + " ".join(metric_parts + [backend_text, " ".join(recommendations[:2])])


def ask_for_missing_details(plan: AssistantActionPlan, context: ConversationContext) -> str:
    context.pending_plan = plan
    context.active_task = plan.intent
    context.missing_details = list(plan.missing_details)
    if plan.intent == "open_app":
        context.pending_question = "target_app"
        return "Which app should I open?"
    if plan.intent == "create_folder":
        context.pending_question = "folder_name"
        return "What should I name the folder?"
    if plan.intent == "create_reminder":
        context.reminder_details.update({key: value for key, value in plan.params.items() if value})
        if "reminder_text" in plan.missing_details and "reminder_time" in plan.missing_details:
            context.pending_question = "reminder_text_and_time"
            return "What should I remind you about, and when?"
        if "reminder_text" in plan.missing_details:
            context.pending_question = "reminder_text"
            return "What should I remind you about?"
        context.pending_question = "reminder_time"
        return "When should I remind you?"
    if plan.intent == "meeting_reminder":
        context.reminder_details.update({key: value for key, value in plan.params.items() if value})
        context.pending_question = "meeting_time_topic"
        return "What time is the meeting, and what topic should I use for the reminder?"
    if plan.intent == "create_task":
        context.pending_question = "task_text"
        return "What task should I add?"
    if plan.intent in {"complete_reminder", "cancel_reminder"}:
        context.pending_question = "reminder_match"
        return "Which reminder should I update?"
    if plan.intent == "close_target":
        context.pending_question = "close_target"
        return "Which app or window should I close?"
    if plan.intent == "media_control":
        context.pending_question = "media_context"
        return "I understood you want media control, but I do not see an active video or music window. Which app should I control?"
    return "I understood the intent, but I need one more detail before I can act."


def ask_for_confirmation(plan: AssistantActionPlan, context: ConversationContext) -> str:
    context.pending_plan = plan
    context.active_task = plan.intent
    context.chosen_action = plan.action
    target = plan.target or plan.params.get("app") or plan.params.get("url") or plan.intent
    return f"I can {plan.action.replace('_', ' ')} {target}. Should I go ahead?"


def execute_plan(plan: AssistantActionPlan, context: ConversationContext) -> dict[str, Any]:
    if plan.intent == "cancel_pending":
        context.pending_plan = None
        context.pending_question = ""
        context.missing_details = []
        return {"ok": True, "reply": "Cancelled. I will not do that.", "executed": False}
    if plan.intent == "context_question":
        if context.pending_question:
            return {"ok": True, "reply": f"I am waiting for: {context.pending_question.replace('_', ' ')}.", "executed": False}
        if context.last_executed_action:
            return {"ok": True, "reply": f"Last action: {context.last_executed_action.get('summary', 'completed')}", "executed": False}
        return {"ok": True, "reply": "No active task is pending right now.", "executed": False}
    if plan.tool_name in {
        "open_app",
        "open_website",
        "create_folder",
        "volume_control",
        "close_tracked_app",
        "media_key_control",
        "screen_read",
        "search_selected_google",
        "create_reminder",
        "list_reminders",
        "complete_reminder",
        "cancel_reminder",
        "check_due_reminders",
        "startup_status",
        "enable_startup",
        "disable_startup",
        "voice_runtime_status",
        "enable_voice_runtime",
        "disable_voice_runtime",
        "remember_this",
        "list_memories",
        "forget_memory",
        "memory_status",
        "memory_opt_out",
        "review_memories",
        "cleanup_memories",
        "update_memory",
        "memory_conflicts",
        "resolve_memory_conflict",
        "create_task",
        "system_diagnostics",
        "capability_discovery",
        "unsupported_action",
    }:
        result = execute_registered_tool(plan.tool_name, plan.params, context)
        reply = compact_text(result.get("message")) or ("Done." if result.get("ok") else "I could not complete that action.")
        if not result.get("ok") and plan.action in {"adjust_volume", "close_app"}:
            reply = f"I understood the intent ({plan.intent}), but the {plan.action} adapter failed: {reply}"
        if result.get("ok"):
            context.last_executed_action = {"action": plan.action, "tool_name": plan.tool_name, "summary": reply, "target": plan.target, "data": result.get("data", {})}
            if plan.intent == "open_app":
                context.target_app = plan.target
            elif plan.intent == "close_target" and context.target_app == plan.target:
                context.target_app = ""
            else:
                context.target_object = plan.target
        if plan.intent in {"create_reminder", "meeting_reminder"} and result.get("ok"):
            context.reminder_details = {}
        missing_adapter = ""
        if isinstance(result.get("data"), dict):
            missing_adapter = compact_text(result["data"].get("missing_adapter"))
        payload = {"ok": bool(result.get("ok")), "reply": reply, "executed": bool(result.get("ok")), "action_result": result, "tool_debug": tool_debug_snapshot(plan.tool_name, plan.params)}
        if missing_adapter:
            payload["missing_adapter"] = missing_adapter
        if plan.action == "screen_read" and isinstance(result.get("data"), dict):
            payload["screen_context"] = result["data"].get("screen_context")
            payload["executed"] = True
        return payload
    return {"ok": False, "reply": "I understood the intent, but the action adapter is not available yet.", "executed": False}
