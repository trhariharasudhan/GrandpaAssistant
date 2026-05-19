from __future__ import annotations

import logging
import re
import datetime
from typing import Any

from .context import clear_personal_assistant_contexts_for_tests, compact_text, get_conversation_context
from .executor import ask_for_confirmation, ask_for_missing_details, execute_plan
from .intent_engine import IntentCandidate, detect_intent
from . import llm_planner
from . import memory_manager
from .planner import build_action_plan
from .screen_context import get_screen_context, summarize_for_debug
from .reminder_scheduler import get_reminder_scheduler_status
from .voice_runtime import get_voice_runtime_status
from .tool_registry import tool_debug_snapshot

logger = logging.getLogger(__name__)


def _debug_metadata(
    candidate: IntentCandidate,
    plan=None,
    result: dict[str, Any] | None = None,
    screen_context: dict[str, Any] | None = None,
    *,
    planner_source: str = "deterministic",
    llm_planner_outcome: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = {
        "detected_intent": candidate.intent,
        "confidence": candidate.confidence,
        "planner_source": planner_source,
        "llm_planner": {},
        "resolved_context_target": "",
        "planned_action": "",
        "selected_tool": "",
        "tool_availability": {},
        "missing_fields": [],
        "permission_decision": {},
        "executor_result": {},
        "active_window": summarize_for_debug(screen_context).get("active_window", {}),
        "detected_screen_context": (screen_context or {}).get("screen_context", {}) if isinstance(screen_context, dict) else {},
        "screenshot_ocr_summary": (summarize_for_debug(screen_context).get("screenshot") or {}),
        "planner_reasoning_summary": "",
        "chosen_action_source": "",
        "reminder_scheduler": get_reminder_scheduler_status(),
        "voice_runtime": get_voice_runtime_status(),
        "memory": {
            "extracted_candidates": [],
            "selected_memories_used": [],
            "ignored": [],
        },
    }
    if plan is not None:
        try:
            hints = memory_manager.relevant_memory_hints(plan.source_message or candidate.normalized_message, limit=5)
        except Exception:
            hints = []
        metadata.update(
            {
                "resolved_context_target": compact_text(plan.target),
                "planned_action": compact_text(plan.action),
                "selected_tool": compact_text(plan.tool_name),
                "tool_availability": tool_debug_snapshot(plan.tool_name, plan.params) if plan.tool_name else {},
                "missing_fields": list(plan.missing_details),
                "permission_decision": {
                    "risk_level": compact_text(plan.risk_level),
                    "requires_confirmation": bool(plan.requires_confirmation),
                    "reason": compact_text(plan.reason),
                },
                "planner_reasoning_summary": compact_text(plan.reason),
                "chosen_action_source": "screen_context" if plan.intent in {"media_control", "close_current_window", "screen_read", "search_selected_google", "play_media_search"} else "conversation",
            }
        )
        metadata["memory"]["selected_memories_used"] = [
            {
                "category": compact_text(item.get("category")),
                "key": compact_text(item.get("key")),
                "confidence": item.get("confidence"),
                "reason": "relevant_active_memory",
            }
            for item in hints
            if isinstance(item, dict)
        ]
        if not hints:
            metadata["memory"]["ignored"].append("no_relevant_active_memory")
    if isinstance(llm_planner_outcome, dict):
        metadata["llm_planner"] = {
            "attempted": True,
            "ok": bool(llm_planner_outcome.get("ok")),
            "raw_plan": compact_text(llm_planner_outcome.get("raw_plan")),
            "parsed_plan": llm_planner_outcome.get("parsed_plan") if isinstance(llm_planner_outcome.get("parsed_plan"), dict) else {},
            "validated_plan": llm_planner_outcome.get("validated_plan") if isinstance(llm_planner_outcome.get("validated_plan"), dict) else {},
            "validation_errors": list(llm_planner_outcome.get("validation_errors") or []),
            "validation_warnings": list(llm_planner_outcome.get("validation_warnings") or []),
        }
    if isinstance(result, dict):
        metadata["executor_result"] = {
            "ok": bool(result.get("ok")),
            "executed": bool(result.get("executed")),
            "missing_adapter": compact_text(result.get("missing_adapter")),
            "action": compact_text((result.get("action_result") or {}).get("action") if isinstance(result.get("action_result"), dict) else ""),
            "tool": compact_text(((result.get("tool_debug") or {}).get("tool_name")) if isinstance(result.get("tool_debug"), dict) else ""),
        }
        action_result = result.get("action_result") if isinstance(result.get("action_result"), dict) else {}
        data = action_result.get("data") if isinstance(action_result.get("data"), dict) else {}
        if isinstance(data, dict):
            stored = data.get("stored") if isinstance(data.get("stored"), list) else []
            memories = data.get("memories") if isinstance(data.get("memories"), list) else []
            metadata["memory"]["selected_memories_used"] = [
                {
                    "category": compact_text(item.get("category")),
                    "key": compact_text(item.get("key")),
                    "confidence": item.get("confidence"),
                    "reason": "memory_tool_result",
                }
                for item in (stored or memories[:5])
                if isinstance(item, dict)
            ] or metadata["memory"]["selected_memories_used"]
            if data.get("blocked"):
                metadata["memory"]["ignored"].append("sensitive_or_blocked")
    try:
        metadata["memory"]["extracted_candidates"] = [
            {"category": item["category"], "key": item["key"], "confidence": item["confidence"]}
            for item in memory_manager.extract_memory_candidates(candidate.normalized_message or "")
        ]
    except Exception:
        metadata["memory"]["ignored"].append("candidate_extraction_failed")
    return metadata


def _with_debug(payload: dict[str, Any], debug: dict[str, Any], include_debug: bool) -> dict[str, Any]:
    logger.info(
        "personal_assistant planner=%s intent=%s target=%s action=%s tool=%s missing=%s risk=%s executed=%s ok=%s",
        debug.get("planner_source"),
        debug.get("detected_intent"),
        debug.get("resolved_context_target"),
        debug.get("planned_action"),
        debug.get("selected_tool"),
        ",".join(debug.get("missing_fields") or []),
        (debug.get("permission_decision") or {}).get("risk_level", ""),
        (debug.get("executor_result") or {}).get("executed", False),
        payload.get("ok"),
    )
    if include_debug:
        payload["debug"] = debug
    return payload


def _utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _memory_conflict_decision(normalized: str) -> str:
    if normalized in {"yes", "yep", "yeah", "ok", "okay", "sure", "confirm"}:
        return "update"
    if any(phrase in normalized for phrase in ("yes update", "use new", "use the new", "change it", "update it", "new one")):
        return "update"
    if normalized in {"no", "nope"}:
        return "keep_old"
    if any(phrase in normalized for phrase in ("keep old", "keep the old", "keep previous", "keep the previous", "don't change", "dont change", "old one")):
        return "keep_old"
    if normalized in {"cancel", "stop", "never mind", "nevermind"}:
        return "cancel"
    return ""


def _store_pending_memory_conflict(context, result: dict[str, Any]) -> None:
    action_result = result.get("action_result") if isinstance(result.get("action_result"), dict) else {}
    data = action_result.get("data") if isinstance(action_result.get("data"), dict) else {}
    conflicts = data.get("conflicts") if isinstance(data.get("conflicts"), list) else []
    if not conflicts:
        return
    conflict = conflicts[0] if isinstance(conflicts[0], dict) else {}
    memory = conflict.get("memory") if isinstance(conflict.get("memory"), dict) else {}
    memory_id = compact_text(memory.get("memory_id"))
    if not memory_id:
        return
    context.pending_memory_conflict = {
        "memory_id": memory_id,
        "category": compact_text(memory.get("category")),
        "key": compact_text(memory.get("key")),
        "old_value": compact_text(memory.get("value")),
        "pending_value": compact_text(conflict.get("pending_value") or memory.get("pending_value")),
        "created_at": _utc_now(),
    }
    context.pending_plan = None
    context.active_task = "memory_conflict"
    context.pending_question = "memory_conflict"


def _merge_follow_up(candidate: IntentCandidate, context, message: str) -> IntentCandidate:
    normalized = compact_text(message).lower()
    if context.pending_memory_conflict:
        decision = _memory_conflict_decision(normalized)
        if decision:
            details = dict(context.pending_memory_conflict)
            details["decision"] = decision
            return IntentCandidate("resolve_memory_conflict", 0.95, details, [], normalized)
    if candidate.intent == "open_app" and "target_app" in candidate.missing_details and context.target_app:
        return IntentCandidate("open_app", 0.72, {"app": context.target_app}, [], normalized)
    if context.pending_question == "reminder_time" and candidate.intent == "unknown":
        if any(token in normalized for token in ("tomorrow", "naalai", "today", "morning", "evening", "in ", " at ")):
            details = dict(context.reminder_details)
            details["time_text"] = message
            missing = [] if details.get("reminder_text") else ["reminder_text"]
            return IntentCandidate("create_reminder", 0.78, details, missing, normalized)
    if context.pending_question == "reminder_text" and candidate.intent == "unknown":
        details = dict(context.reminder_details)
        details["reminder_text"] = message
        missing = [] if details.get("time_text") else ["reminder_time"]
        return IntentCandidate("create_reminder", 0.78, details, missing, normalized)
    if context.pending_question == "meeting_time_topic":
        details = dict(context.reminder_details)
        time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", normalized)
        if time_match:
            details["time_text"] = time_match.group(0)
            topic = compact_text(normalized.replace(time_match.group(0), " "))
            if topic:
                details["topic"] = topic
        elif candidate.intent == "unknown":
            details["topic"] = message
        missing = []
        if not details.get("date_text"):
            missing.append("meeting_date")
        if not details.get("time_text") or not details.get("topic"):
            missing.append("meeting_time_topic")
        return IntentCandidate("meeting_reminder", 0.78, details, missing, normalized)
    if context.pending_question == "target_app" and candidate.intent == "unknown":
        return IntentCandidate("open_app", 0.72, {"app": normalized}, [], normalized)
    if normalized == "check everything" and context.active_task:
        return IntentCandidate("system_diagnostics", 0.92, normalized_message=normalized)
    return candidate


def handle_personal_assistant_message(message: str, *, session_id: str | None = None, include_debug: bool = False) -> dict[str, Any]:
    user_message = compact_text(message)
    context = get_conversation_context(session_id)
    candidate = detect_intent(user_message)
    screen_context = get_screen_context(include_screenshot=candidate.intent == "screen_read")
    candidate = _merge_follow_up(candidate, context, user_message)
    plan = build_action_plan(candidate, context, user_message, screen_context=screen_context)
    planner_source = "deterministic"
    llm_outcome: dict[str, Any] | None = None
    if plan is None:
        if llm_planner.should_attempt_llm_planner(candidate, user_message):
            llm_outcome = llm_planner.build_llm_assisted_plan(user_message=user_message, context=context, screen_context=screen_context)
            planner_source = "llm_planner"
            if llm_outcome.get("ok") and llm_outcome.get("plan") is not None:
                plan = llm_outcome["plan"]
                parsed = llm_outcome.get("parsed_plan") if isinstance(llm_outcome.get("parsed_plan"), dict) else {}
                try:
                    confidence = float(parsed.get("confidence") or 0.0)
                except Exception:
                    confidence = 0.0
                parameters = parsed.get("parameters") if isinstance(parsed.get("parameters"), dict) else {}
                candidate = IntentCandidate(plan.intent, confidence, dict(parameters), list(plan.missing_details), compact_text(user_message))
            else:
                result = {"ok": False, "executed": False, "missing_adapter": "llm_planner", "reply": llm_planner.invalid_plan_reply(list(llm_outcome.get("validation_errors") or []))}
                payload = {
                    "handled": True,
                    "ok": False,
                    "reply": result["reply"],
                    "route": "personal-assistant",
                    "intent": candidate.intent,
                    "executed": False,
                    "missing_adapter": "llm_planner",
                    "session_id": context.session_id,
                }
                return _with_debug(
                    payload,
                    _debug_metadata(candidate, None, result, screen_context, planner_source=planner_source, llm_planner_outcome=llm_outcome),
                    include_debug,
                )
        else:
            payload = {"handled": False, "intent": candidate.intent, "session_id": context.session_id}
            return _with_debug(payload, _debug_metadata(candidate, screen_context=screen_context), include_debug)

    if plan.intent == "cancel_pending":
        result = execute_plan(plan, context)
        context.remember_event(user_message=user_message, intent=plan.intent, outcome=result["reply"])
        payload = {"handled": True, "ok": result["ok"], "reply": result["reply"], "route": "personal-assistant", "intent": plan.intent, "session_id": context.session_id}
        return _with_debug(payload, _debug_metadata(candidate, plan, result, screen_context, planner_source=planner_source, llm_planner_outcome=llm_outcome), include_debug)

    if plan.missing_details:
        reply = ask_for_missing_details(plan, context)
        context.remember_event(user_message=user_message, intent=plan.intent, outcome="missing_details", target=plan.target)
        payload = {
            "handled": True,
            "ok": True,
            "reply": reply,
            "route": "personal-assistant",
            "intent": plan.intent,
            "missing_details": list(plan.missing_details),
            "session_id": context.session_id,
        }
        return _with_debug(
            payload,
            _debug_metadata(candidate, plan, {"ok": True, "executed": False}, screen_context, planner_source=planner_source, llm_planner_outcome=llm_outcome),
            include_debug,
        )

    if plan.requires_confirmation:
        reply = ask_for_confirmation(plan, context)
        context.remember_event(user_message=user_message, intent=plan.intent, outcome="confirmation_required", target=plan.target)
        payload = {
            "handled": True,
            "ok": True,
            "reply": reply,
            "route": "personal-assistant",
            "intent": plan.intent,
            "requires_confirmation": True,
            "risk_level": plan.risk_level,
            "session_id": context.session_id,
        }
        return _with_debug(
            payload,
            _debug_metadata(candidate, plan, {"ok": True, "executed": False}, screen_context, planner_source=planner_source, llm_planner_outcome=llm_outcome),
            include_debug,
        )

    result = execute_plan(plan, context)
    _store_pending_memory_conflict(context, result)
    context.pending_plan = None
    if plan.intent == "resolve_memory_conflict" or not context.pending_memory_conflict:
        context.pending_question = ""
    context.missing_details = []
    context.active_task = "" if result.get("executed") else context.active_task
    context.chosen_action = ""
    if plan.intent == "resolve_memory_conflict":
        context.pending_memory_conflict = {}
        context.pending_plan = None
        context.active_task = ""
    context.remember_event(user_message=user_message, intent=plan.intent, outcome=result.get("reply", ""), target=plan.target)
    payload = {
        "handled": True,
        "ok": bool(result.get("ok")),
        "reply": result.get("reply", ""),
        "route": "personal-assistant",
        "intent": plan.intent,
        "executed": bool(result.get("executed")),
        "missing_adapter": result.get("missing_adapter", ""),
        "session_id": context.session_id,
    }
    if isinstance(result.get("screen_context"), dict):
        screen_context = result["screen_context"]
    return _with_debug(payload, _debug_metadata(candidate, plan, result, screen_context, planner_source=planner_source, llm_planner_outcome=llm_outcome), include_debug)
