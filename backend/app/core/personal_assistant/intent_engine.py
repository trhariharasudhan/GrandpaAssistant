from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from .context import compact_text
from . import memory_manager


APP_ALIASES = {
    "calc": "calculator",
    "calculator": "calculator",
    "kanakku": "calculator",
    "notepad": "notepad",
    "notes": "notepad",
    "paint": "paint",
    "mspaint": "paint",
    "explorer": "explorer",
    "file explorer": "explorer",
}

OPEN_WORDS = {"open", "launch", "start", "run", "thirakkavum"}
CONFIRM_YES = {"yes", "yep", "yeah", "ok", "okay", "sure", "confirm", "do it", "go ahead", "seri", "aama", "ama", "pannu"}
CONFIRM_NO = {"no", "nope", "cancel", "stop", "don't", "dont", "vendam", "illa"}


@dataclass
class IntentCandidate:
    intent: str
    confidence: float
    slots: dict[str, Any] = field(default_factory=dict)
    missing_details: list[str] = field(default_factory=list)
    normalized_message: str = ""


def _lower(message: str) -> str:
    return compact_text(message).lower()


def _contains_any(text: str, words: set[str] | tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _extract_app(normalized: str) -> str:
    cleaned = normalized
    cleaned = re.sub(r"\b(please|pls|can you|could you|would you|grandpa|da|bro)\b", " ", cleaned)
    cleaned = re.sub(r"\b(open|launch|start|run|pannu|pannunga|thira|thirakkavum)\b", " ", cleaned)
    cleaned = compact_text(cleaned)
    for alias, app in sorted(APP_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", cleaned):
            return app
    if cleaned and cleaned not in {"it", "that", "this", "app", "application"}:
        return cleaned
    return ""


def _extract_url(normalized: str) -> str:
    match = re.search(r"https?://[^\s]+", normalized)
    if match:
        return match.group(0)
    domain = re.search(r"\b(?:www\.)?[a-z0-9-]+\.(?:com|org|net|io|dev|in|ai)(?:/[^\s]*)?\b", normalized)
    if not domain:
        return ""
    candidate = domain.group(0)
    if not candidate.startswith(("http://", "https://")):
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    return candidate if parsed.netloc else ""


def _extract_folder_details(message: str, normalized: str) -> dict[str, str]:
    name = ""
    parent = ""
    match = re.search(
        r"(?:create|make|new)\s+(?:a\s+)?folder(?:\s+(?:named|called))?\s+(.+?)(?:\s+\b(?:in|inside|under)\b\s+(.+))?$",
        message,
        flags=re.IGNORECASE,
    )
    if match:
        name = compact_text(match.group(1)).strip("\"'")
        parent = compact_text(match.group(2)).strip("\"'") if match.group(2) else ""
    if not name and "folder" in normalized:
        after = re.split(r"\bfolder\b", message, flags=re.IGNORECASE, maxsplit=1)
        if len(after) > 1:
            name = compact_text(after[1]).strip("\"'")
    return {"name": name, "parent": parent}


def _split_reminder_text_and_time(message: str, normalized: str) -> tuple[str, str]:
    text = message
    text = re.sub(r"^\s*(please\s+)?(?:remind me|set a reminder|set reminder|add reminder|reminder)\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*to\s+", "", text, flags=re.IGNORECASE)
    time_phrases = [
        r"\btomorrow\s+morning\b",
        r"\btomorrow\s+evening\b",
        r"\btomorrow\s+afternoon\b",
        r"\btomorrow\b",
        r"\bnaalai\s+morning\b",
        r"\bnaalai\b",
        r"\btoday\s+evening\b",
        r"\btoday\b",
        r"\bin\s+\d+\s+(?:minute|minutes|hour|hours|day|days|week|weeks)\b",
        r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b",
    ]
    found_time = ""
    for pattern in time_phrases:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            found_time = compact_text(match.group(0))
            text = compact_text(text[: match.start()] + " " + text[match.end() :])
            break
    text = re.sub(r"^\s*to\s+", "", text, flags=re.IGNORECASE)
    if not found_time:
        # Patterns where the date appears before the task: "tomorrow morning to call amma".
        for pattern in time_phrases:
            match = re.match(pattern + r"\s+(?:to\s+)?(.+)$", text, flags=re.IGNORECASE)
            if match:
                found_time = compact_text(match.group(0).replace(match.group(1), ""))
                text = compact_text(match.group(1))
                break
    if "remind me" in normalized and not text:
        text = ""
    return compact_text(text), compact_text(found_time)


def _parse_meeting_hint(message: str, normalized: str) -> dict[str, str]:
    date_text = ""
    topic = ""
    if "tomorrow" in normalized:
        date_text = "tomorrow"
    elif "naalai" in normalized:
        date_text = "naalai"
    elif "today" in normalized:
        date_text = "today"
    if "morning" in normalized:
        date_text = compact_text(f"{date_text} morning")
    elif "afternoon" in normalized:
        date_text = compact_text(f"{date_text} afternoon")
    elif "evening" in normalized:
        date_text = compact_text(f"{date_text} evening")
    topic_match = re.search(r"\b(?:meeting|call|discussion)\s+(?:about|for|on)\s+(.+)$", message, flags=re.IGNORECASE)
    if topic_match:
        topic = compact_text(topic_match.group(1))
    return {"date_text": date_text, "topic": topic}


def _parse_volume_operation(normalized: str) -> str:
    if "unmute" in normalized:
        return "unmute"
    if "mute" in normalized:
        return "mute"
    if any(token in normalized for token in ("increase", "raise", "higher", "volume up", "sound up", "adhigam", "increase pannu")):
        return "increase"
    if any(token in normalized for token in ("reduce", "decrease", "lower", "down", "kammi", "korai", "volume konjam kammi")):
        return "decrease"
    return ""


def _is_diagnostics_request(normalized: str) -> bool:
    if normalized in {"check everything", "check all", "diagnostics", "assistant doctor", "doctor"}:
        return True
    return any(
        phrase in normalized
        for phrase in (
            "run diagnostics",
            "system diagnostics",
            "backend stability",
            "health check",
            "check system",
            "check backend",
            "everything ok",
        )
    )


def _extract_reminder_update_query(message: str, normalized: str, *, action: str) -> str:
    text = compact_text(message)
    if action == "complete":
        text = re.sub(r"\b(mark|set)\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\b(done|complete|completed|finished)\b", " ", text, flags=re.IGNORECASE)
    if action == "cancel":
        text = re.sub(r"\b(cancel|delete|remove)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(my|the|this|that|a|an)\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(reminder|reminders)\b", " ", text, flags=re.IGNORECASE)
    query = compact_text(text)
    if not query and any(word in normalized for word in ("this reminder", "that reminder")):
        return "this reminder"
    return query


def detect_intent(message: str) -> IntentCandidate:
    normalized = _lower(message)
    if not normalized:
        return IntentCandidate("empty", 1.0, normalized_message=normalized)
    if any(phrase in normalized for phrase in ("don't remember this", "dont remember this", "do not remember this")):
        return IntentCandidate("memory_opt_out", 0.94, normalized_message=normalized)
    if any(
        phrase in normalized
        for phrase in (
            "what can you do",
            "what are your tools",
            "available tools",
            "available actions",
            "what actions can you do",
            "help capabilities",
        )
    ):
        return IntentCandidate("capability_discovery", 0.9, normalized_message=normalized)
    if normalized in CONFIRM_YES:
        return IntentCandidate("confirmation_yes", 1.0, normalized_message=normalized)
    if normalized in CONFIRM_NO:
        return IntentCandidate("confirmation_no", 1.0, normalized_message=normalized)
    if normalized in {"do it", "do that", "yes do it", "go ahead", "seri pannu"}:
        return IntentCandidate("follow_up_execute", 1.0, normalized_message=normalized)
    if any(phrase in normalized for phrase in ("what do you remember", "list memories", "show memories", "what you remember about me")):
        return IntentCandidate("list_memories", 0.91, normalized_message=normalized)
    if any(phrase in normalized for phrase in ("review my memories", "review memories", "memory review")):
        return IntentCandidate("review_memories", 0.9, normalized_message=normalized)
    if any(phrase in normalized for phrase in ("clean old memories", "cleanup memories", "clean up memories", "memory cleanup")):
        return IntentCandidate("cleanup_memories", 0.88, normalized_message=normalized)
    if any(phrase in normalized for phrase in ("memory conflicts", "memory conflict", "any memory conflicts", "do you have any memory conflicts")):
        return IntentCandidate("memory_conflicts", 0.9, normalized_message=normalized)
    if any(phrase in normalized for phrase in ("yes update it", "use new one", "use the new one", "change it", "keep old one", "keep the old one", "keep previous one", "keep the previous one", "don't change", "dont change")):
        return IntentCandidate("memory_conflict_follow_up", 0.7, normalized_message=normalized)
    update_editor = re.search(r"\bupdate\s+(?:my\s+)?(?:preferred\s+)?(?:editor|code editor)\s+to\s+(.+)$", message, flags=re.IGNORECASE)
    if update_editor:
        return IntentCandidate(
            "update_memory",
            0.91,
            {"category": "favorite_apps", "key": "preferred_code_editor", "value": compact_text(update_editor.group(1))},
            normalized_message=normalized,
        )
    update_name = re.search(r"\bupdate\s+(?:my\s+)?(?:name|preferred name)\s+to\s+(.+)$", message, flags=re.IGNORECASE)
    if update_name:
        return IntentCandidate("update_memory", 0.9, {"category": "user_preferences", "key": "preferred_name", "value": compact_text(update_name.group(1))}, normalized_message=normalized)
    if any(phrase in normalized for phrase in ("memory status", "memory health", "personal memory status")):
        return IntentCandidate("memory_status", 0.9, normalized_message=normalized)
    if re.search(r"\b(forget|delete|remove)\b.*\b(memory|remember|preference|about me|old office|location|company|name|music|editor)\b", normalized):
        query = re.sub(r"\b(forget|delete|remove|memory|remember|preference|about me|my)\b", " ", message, flags=re.IGNORECASE)
        return IntentCandidate("forget_memory", 0.88, {"memory_query": compact_text(query)}, ["memory_query"] if not compact_text(query) else [], normalized)
    if normalized.startswith("remember ") or normalized.startswith("remember that ") or normalized.startswith("remember this"):
        return IntentCandidate("remember_this", 0.92, {"memory_text": message}, normalized_message=normalized)
    memory_candidates = memory_manager.extract_memory_candidates(message)
    if memory_candidates:
        return IntentCandidate("remember_this", 0.78, {"memory_text": message, "implicit": True}, normalized_message=normalized)
    if normalized in {"close it", "close that", "stop it", "adhe close pannu"}:
        return IntentCandidate("close_target", 0.9, normalized_message=normalized)
    if normalized in {"close this", "close current app", "close current window", "close this window"}:
        return IntentCandidate("close_current_window", 0.88, normalized_message=normalized)
    if normalized in {"pause it", "pause this", "pause video", "pause music", "play it", "resume it"}:
        operation = "pause" if "pause" in normalized else "play"
        return IntentCandidate("media_control", 0.86, {"operation": operation}, normalized_message=normalized)
    if normalized in {"what is on my screen", "what's on my screen", "read this error", "analyze this page", "what does this popup say", "read screen"}:
        return IntentCandidate("screen_read", 0.9, normalized_message=normalized)
    if "search this on google" in normalized or "google this" in normalized:
        return IntentCandidate("search_selected_google", 0.84, normalized_message=normalized)
    if "play relaxing music" in normalized or "play calm music" in normalized:
        return IntentCandidate("play_media_search", 0.82, {"query": "relaxing music"}, normalized_message=normalized)
    if "play my favorite music" in normalized or "play music" == normalized or "play some music" in normalized:
        return IntentCandidate("play_media_search", 0.8, {"query": ""}, normalized_message=normalized)
    if any(
        phrase in normalized
        for phrase in (
            "start grandpaassistant when windows starts",
            "start grandpa assistant when windows starts",
            "enable startup",
            "enable assistant startup",
            "enable windows startup",
            "launch on startup",
            "open on startup",
            "run on startup",
            "start on windows startup",
        )
    ):
        return IntentCandidate("enable_startup", 0.88, normalized_message=normalized)
    if any(
        phrase in normalized
        for phrase in (
            "stop opening on startup",
            "disable startup",
            "disable assistant startup",
            "disable windows startup",
            "turn off startup",
            "do not open on startup",
            "don't open on startup",
        )
    ):
        return IntentCandidate("disable_startup", 0.88, normalized_message=normalized)
    if any(
        phrase in normalized
        for phrase in (
            "check startup status",
            "startup status",
            "windows startup status",
            "assistant startup status",
            "show startup command",
            "startup command",
        )
    ):
        return IntentCandidate("startup_status", 0.9, normalized_message=normalized)
    if any(phrase in normalized for phrase in ("enable voice mode", "start voice mode", "enable voice runtime", "start voice runtime")):
        return IntentCandidate("enable_voice_runtime", 0.88, normalized_message=normalized)
    if any(phrase in normalized for phrase in ("disable voice mode", "stop voice mode", "disable voice runtime", "stop voice runtime")):
        return IntentCandidate("disable_voice_runtime", 0.88, normalized_message=normalized)
    if any(phrase in normalized for phrase in ("is voice mode running", "voice runtime status", "voice mode status", "is voice runtime running")):
        return IntentCandidate("voice_runtime_status", 0.9, normalized_message=normalized)
    if re.search(r"\b(close|quit|exit)\b", normalized):
        target = compact_text(re.sub(r"\b(close|quit|exit)\b", " ", normalized)).strip()
        return IntentCandidate("close_target", 0.82, {"target": target}, [] if target else ["target"], normalized)
    volume_operation = _parse_volume_operation(normalized)
    if volume_operation and any(token in normalized for token in ("volume", "sound", "audio", "mute", "kammi")):
        return IntentCandidate("adjust_volume", 0.9, {"operation": volume_operation}, normalized_message=normalized)
    if _is_diagnostics_request(normalized):
        return IntentCandidate("system_diagnostics", 0.92, normalized_message=normalized)
    if any(phrase in normalized for phrase in ("laptop is slow", "system slow", "pc slow", "computer slow", "running slow", "full check")):
        return IntentCandidate("system_diagnostics", 0.9, {"diagnostic_scope": "performance"}, normalized_message=normalized)
    if any(
        phrase in normalized
        for phrase in (
            "what reminders do i have",
            "show pending reminders",
            "show reminders",
            "list reminders",
            "pending reminders",
            "reminders list",
        )
    ):
        return IntentCandidate("list_reminders", 0.9, {"status": "pending"}, normalized_message=normalized)
    if any(phrase in normalized for phrase in ("check due reminders", "any reminders due", "due reminders", "reminders due now")):
        return IntentCandidate("check_due_reminders", 0.9, normalized_message=normalized)
    if "reminder" in normalized and re.search(r"\b(done|complete|completed|finished)\b", normalized):
        query = _extract_reminder_update_query(message, normalized, action="complete")
        return IntentCandidate("complete_reminder", 0.86, {"reminder_query": query}, [] if query else ["reminder_query"], normalized)
    if "reminder" in normalized and re.search(r"\b(cancel|delete|remove)\b", normalized):
        query = _extract_reminder_update_query(message, normalized, action="cancel")
        return IntentCandidate("cancel_reminder", 0.86, {"reminder_query": query}, [] if query else ["reminder_query"], normalized)
    if re.search(r"\b(i have|there is|got)\s+(?:a\s+)?(meeting|call|discussion)\b", normalized):
        hint = _parse_meeting_hint(message, normalized)
        missing = []
        if not hint.get("date_text"):
            missing.append("meeting_date")
        missing.append("meeting_time_topic")
        return IntentCandidate("meeting_reminder", 0.86, hint, missing, normalized)
    if "remind" in normalized or "reminder" in normalized:
        reminder_text, time_text = _split_reminder_text_and_time(message, normalized)
        missing = []
        if not reminder_text:
            missing.append("reminder_text")
        if not time_text:
            missing.append("reminder_time")
        return IntentCandidate(
            "create_reminder",
            0.92,
            {"reminder_text": reminder_text, "time_text": time_text},
            missing,
            normalized,
        )
    if re.search(r"\b(task|todo)\b", normalized) and re.search(r"\b(add|create|remember)\b", normalized):
        task_text = re.sub(r"^\s*(?:add|create|remember)\s+(?:a\s+)?(?:task|todo)\s*", "", message, flags=re.IGNORECASE)
        return IntentCandidate("create_task", 0.84, {"task_text": compact_text(task_text)}, ["task_text"] if not compact_text(task_text) else [], normalized)
    url = _extract_url(normalized)
    if url and (_contains_any(normalized, OPEN_WORDS) or "go to" in normalized):
        return IntentCandidate("open_url", 0.9, {"url": url}, normalized_message=normalized)
    if _contains_any(normalized, OPEN_WORDS) or re.search(r"\b(open|launch|start|run)\b", normalized) or "open pannu" in normalized:
        app = _extract_app(normalized)
        missing = [] if app else ["target_app"]
        return IntentCandidate("open_app", 0.86 if app else 0.68, {"app": app}, missing, normalized)
    if re.search(r"\b(create|make|new)\b.*\bfolder\b", normalized):
        details = _extract_folder_details(message, normalized)
        missing = []
        if not details.get("name"):
            missing.append("folder_name")
        return IntentCandidate("create_folder", 0.84, details, missing, normalized)
    if normalized in {"what next", "what should i do", "what now", "next step"}:
        return IntentCandidate("context_question", 0.78, normalized_message=normalized)
    if any(token in normalized for token in ("pay", "payment", "buy", "order", "purchase", "transfer money")):
        return IntentCandidate("unsupported_action", 0.82, {"capability": "payments or purchases"}, normalized_message=normalized)
    if re.search(r"\b(send|message|email|mail)\b", normalized):
        return IntentCandidate("unsupported_action", 0.78, {"capability": "external communication"}, normalized_message=normalized)
    if re.search(r"\b(delete|remove|format|wipe)\b", normalized):
        return IntentCandidate("unsupported_action", 0.84, {"capability": "destructive file or system action"}, normalized_message=normalized)
    return IntentCandidate("unknown", 0.0, normalized_message=normalized)
