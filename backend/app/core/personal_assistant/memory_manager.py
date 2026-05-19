from __future__ import annotations

import datetime
import json
import os
import re
import tempfile
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from .context import compact_text

try:
    from shared.utils.paths import backend_data_path
except Exception:  # pragma: no cover - fallback for unusual import paths
    backend_data_path = None


MEMORY_PATH_ENV = "GRANDPA_PERSONAL_ASSISTANT_MEMORY_PATH"
MEMORY_SCHEMA_VERSION = 2
DEFAULT_MIN_CONFIDENCE = 0.55
STALE_AFTER_DAYS = 180
MIN_QUALITY_SCORE = 0.5

MEMORY_CATEGORIES = {
    "user_preferences",
    "recurring_tasks",
    "favorite_apps",
    "common_locations",
    "communication_preferences",
    "work_context",
    "assistant_behavior_preferences",
    "reminders_summary",
    "known_devices",
}

SENSITIVE_TERMS = {
    "password",
    "passcode",
    "token",
    "api key",
    "api_key",
    "secret",
    "credential",
    "otp",
    "pin",
    "private key",
    "bearer",
}


def _utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _memory_path() -> str:
    configured = compact_text(os.environ.get(MEMORY_PATH_ENV))
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    if backend_data_path is not None:
        return backend_data_path("personal_assistant_memory.json")
    return os.path.abspath(os.path.join("runtime", "data", "personal_assistant_memory.json"))


def _default_payload() -> dict[str, Any]:
    return {"schema_version": MEMORY_SCHEMA_VERSION, "memories": []}


def _load_payload() -> dict[str, Any]:
    path = _memory_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return _default_payload()
    except Exception:
        return _default_payload()
    if not isinstance(payload, dict):
        return _default_payload()
    memories = payload.get("memories")
    if not isinstance(memories, list):
        memories = []
    return {"schema_version": int(payload.get("schema_version") or MEMORY_SCHEMA_VERSION), "memories": [item for item in memories if isinstance(item, dict)]}


def _save_payload(payload: dict[str, Any]) -> None:
    path = _memory_path()
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    safe_payload = {"schema_version": MEMORY_SCHEMA_VERSION, "memories": list(payload.get("memories") or [])}
    fd, temp_path = tempfile.mkstemp(prefix=".personal-memory-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(safe_payload, handle, indent=2, ensure_ascii=False, sort_keys=True)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def _contains_sensitive(value: Any) -> bool:
    text = compact_text(value).lower()
    return any(term in text for term in SENSITIVE_TERMS)


def _normalize_category(category: str) -> str:
    normalized = compact_text(category).lower().replace(" ", "_")
    return normalized if normalized in MEMORY_CATEGORIES else "user_preferences"


def _normalize_key(key: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", compact_text(key).lower().replace("-", "_"))
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized[:80] or "memory"


def _safe_value(value: Any) -> str:
    return compact_text(value)[:1000]


@dataclass
class StructuredMemory:
    memory_id: str
    category: str
    key: str
    value: str
    source: str
    confidence: float
    created_at: str
    updated_at: str
    last_used_at: str
    pinned: bool = False
    manual: bool = False
    retention_policy: str = "long_term"
    status: str = "active"
    quality_score: float = 0.75
    conflict_status: str = ""
    history: list[dict[str, Any]] | None = None


def _coerce_memory(item: dict[str, Any]) -> dict[str, Any]:
    now = _utc_now()
    status = compact_text(item.get("status")) or "active"
    if status not in {"active", "archived"}:
        status = "active"
    history = item.get("history") if isinstance(item.get("history"), list) else []
    return {
        "memory_id": compact_text(item.get("memory_id")) or "mem_" + uuid.uuid4().hex,
        "category": _normalize_category(item.get("category") or "user_preferences"),
        "key": _normalize_key(item.get("key") or "memory"),
        "value": _safe_value(item.get("value")),
        "source": compact_text(item.get("source")) or "unknown",
        "confidence": max(0.0, min(float(item.get("confidence") or 0.0), 1.0)),
        "created_at": compact_text(item.get("created_at")) or now,
        "updated_at": compact_text(item.get("updated_at")) or now,
        "last_used_at": compact_text(item.get("last_used_at")) or "",
        "pinned": bool(item.get("pinned")),
        "manual": bool(item.get("manual")),
        "retention_policy": compact_text(item.get("retention_policy")) or "long_term",
        "status": status,
        "quality_score": max(0.0, min(float(item.get("quality_score") if item.get("quality_score") is not None else 0.75), 1.0)),
        "conflict_status": compact_text(item.get("conflict_status")),
        "pending_value": _safe_value(item.get("pending_value")),
        "history": [entry for entry in history if isinstance(entry, dict)][-10:],
    }


def _parse_timestamp(value: Any) -> datetime.datetime | None:
    text = compact_text(value).replace("Z", "+00:00")
    if not text:
        return None
    try:
        return datetime.datetime.fromisoformat(text)
    except Exception:
        return None


def is_memory_stale(memory: dict[str, Any], *, now: datetime.datetime | None = None) -> bool:
    if memory.get("pinned") or memory.get("manual"):
        return False
    updated = _parse_timestamp(memory.get("updated_at"))
    if updated is None:
        return False
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=datetime.timezone.utc)
    current = now or datetime.datetime.now(datetime.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=datetime.timezone.utc)
    return (current - updated).days >= STALE_AFTER_DAYS


def score_memory_quality(*, category: str, key: str, value: Any, source: str = "") -> dict[str, Any]:
    safe_value = _safe_value(value)
    normalized = safe_value.lower()
    reasons: list[str] = []
    score = 0.55
    if category in MEMORY_CATEGORIES:
        score += 0.1
    if _normalize_key(key) not in {"note", "memory"}:
        score += 0.15
    if len(safe_value) >= 3:
        score += 0.1
    if len(safe_value) > 120:
        score -= 0.1
        reasons.append("too_long")
    temporary_patterns = (
        r"\bnow\b",
        r"\btoday\b",
        r"\bright now\b",
        r"\bi am eating\b",
        r"\bi'm eating\b",
        r"\bi am tired\b",
        r"\bi'm tired\b",
        r"\bopen calculator\b",
        r"\bclose it\b",
    )
    if any(re.search(pattern, normalized) for pattern in temporary_patterns):
        score -= 0.35
        reasons.append("temporary_or_action_like")
    if "implicit" in compact_text(source).lower():
        score -= 0.05
    score = max(0.0, min(score, 1.0))
    durable = score >= MIN_QUALITY_SCORE
    return {"score": round(score, 3), "durable": durable, "reasons": reasons}


def _conflict_result(existing: dict[str, Any], *, new_value: str, source: str, confidence: float, quality: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "blocked": False,
        "conflict": True,
        "message": (
            f"I already remember your {existing['key'].replace('_', ' ')} as {existing['value']}. "
            f"Should I update it to {new_value}?"
        ),
        "memory": existing,
        "pending_value": new_value,
        "source": compact_text(source),
        "confidence": confidence,
        "quality": quality,
    }


def store_memory(
    *,
    category: str,
    key: str,
    value: Any,
    source: str = "user_explicit",
    confidence: float = 0.9,
    pinned: bool = False,
    manual: bool = False,
    retention_policy: str = "long_term",
    allow_sensitive: bool = False,
    force_update: bool = False,
) -> dict[str, Any]:
    safe_value = _safe_value(value)
    if not safe_value:
        return {"ok": False, "blocked": False, "message": "I need a useful detail before I can remember it.", "memory": {}}
    if _contains_sensitive(f"{key} {safe_value}") and not allow_sensitive:
        return {
            "ok": False,
            "blocked": True,
            "message": "I understood that as sensitive information, so I did not save it to memory.",
            "memory": {},
        }

    category = _normalize_category(category)
    key = _normalize_key(key)
    source_text = compact_text(source) or "user_explicit"
    quality = score_memory_quality(category=category, key=key, value=safe_value, source=source_text)
    if not quality["durable"] and not (manual or pinned):
        return {
            "ok": False,
            "blocked": False,
            "low_quality": True,
            "message": "I did not save that because it looks temporary or not useful as long-term memory.",
            "memory": {},
            "quality": quality,
        }
    now = _utc_now()
    payload = _load_payload()
    memories = [_coerce_memory(item) for item in payload.get("memories", [])]
    existing = next((item for item in memories if item["category"] == category and item["key"] == key), None)
    if existing:
        old_value = compact_text(existing.get("value"))
        is_different = old_value.lower() != safe_value.lower()
        if is_different and not (force_update or manual or (source_text == "user_explicit" and confidence >= 0.85)):
            existing["conflict_status"] = "unresolved"
            existing["pending_value"] = safe_value
            existing.setdefault("history", []).append({"at": now, "event": "conflict_detected", "old_value": old_value, "new_value": safe_value, "source": source_text})
            payload["memories"] = sorted(memories, key=lambda item: (item["category"], item["key"]))
            _save_payload(payload)
            return _conflict_result(existing, new_value=safe_value, source=source_text, confidence=confidence, quality=quality)
        existing.update(
            {
                "value": safe_value,
                "source": source_text or existing["source"],
                "confidence": max(0.0, min(float(confidence), 1.0)),
                "updated_at": now,
                "pinned": bool(pinned or existing.get("pinned")),
                "manual": bool(manual or existing.get("manual")),
                "retention_policy": compact_text(retention_policy) or existing["retention_policy"],
                "status": "active",
                "quality_score": quality["score"],
                "conflict_status": "",
                "pending_value": "",
            }
        )
        if is_different:
            existing.setdefault("history", []).append({"at": now, "event": "updated", "old_value": old_value, "new_value": safe_value, "source": source_text})
            existing["history"] = existing["history"][-10:]
        memory = existing
    else:
        memory = asdict(
            StructuredMemory(
                memory_id="mem_" + uuid.uuid4().hex,
                category=category,
                key=key,
                value=safe_value,
                source=source_text,
                confidence=max(0.0, min(float(confidence), 1.0)),
                created_at=now,
                updated_at=now,
                last_used_at="",
                pinned=bool(pinned),
                manual=bool(manual),
                retention_policy=compact_text(retention_policy) or "long_term",
                status="active",
                quality_score=quality["score"],
                conflict_status="",
                history=[],
            )
        )
        memories.append(memory)
    payload["memories"] = sorted(memories, key=lambda item: (item["category"], item["key"]))
    _save_payload(payload)
    return {"ok": True, "blocked": False, "message": f"I'll remember that your {key.replace('_', ' ')} is {safe_value}.", "memory": memory, "quality": quality}


def query_memories(
    query: str = "",
    *,
    category: str | None = None,
    key: str | None = None,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    limit: int = 10,
    mark_used: bool = True,
    include_archived: bool = False,
    include_conflicted: bool = False,
    include_stale: bool = False,
) -> list[dict[str, Any]]:
    text = compact_text(query).lower()
    tokens = {token for token in re.findall(r"[a-z0-9_]+", text) if len(token) >= 2}
    normalized_category = _normalize_category(category) if category else ""
    normalized_key = _normalize_key(key) if key else ""
    payload = _load_payload()
    memories = [_coerce_memory(item) for item in payload.get("memories", [])]
    matches: list[tuple[float, dict[str, Any]]] = []
    for memory in memories:
        if memory.get("status") == "archived" and not include_archived:
            continue
        if memory.get("conflict_status") and not include_conflicted:
            continue
        if memory.get("quality_score", 0.0) < MIN_QUALITY_SCORE and not memory.get("pinned"):
            continue
        if is_memory_stale(memory) and not include_stale:
            continue
        if memory["confidence"] < min_confidence and not memory.get("pinned"):
            continue
        if normalized_category and memory["category"] != normalized_category:
            continue
        if normalized_key and memory["key"] != normalized_key:
            continue
        haystack = f"{memory['category']} {memory['key']} {memory['value']}".lower()
        score = 1.0 if not tokens else sum(1 for token in tokens if token in haystack) / max(1, len(tokens))
        if score > 0 or normalized_category or normalized_key:
            item = dict(memory)
            item["match_score"] = round(score, 3)
            matches.append((score, item))
    matches.sort(key=lambda pair: (bool(pair[1].get("pinned")), bool(pair[1].get("manual")), pair[0], pair[1]["confidence"], pair[1]["updated_at"], pair[1]["key"]), reverse=True)
    selected = [item for _score, item in matches[: max(1, min(int(limit or 10), 50))]]
    if mark_used and selected:
        used_ids = {item["memory_id"] for item in selected}
        now = _utc_now()
        for memory in memories:
            if memory["memory_id"] in used_ids:
                memory["last_used_at"] = now
        payload["memories"] = memories
        _save_payload(payload)
    return selected


def list_memories(*, category: str | None = None, min_confidence: float = 0.0, include_archived: bool = False, include_conflicted: bool = False, include_stale: bool = True) -> list[dict[str, Any]]:
    return query_memories(
        "",
        category=category,
        min_confidence=min_confidence,
        limit=100,
        mark_used=False,
        include_archived=include_archived,
        include_conflicted=include_conflicted,
        include_stale=include_stale,
    )


def forget_memory(query: str = "", *, category: str | None = None, key: str | None = None) -> dict[str, Any]:
    payload = _load_payload()
    memories = [_coerce_memory(item) for item in payload.get("memories", [])]
    matches = query_memories(query, category=category, key=key, min_confidence=0.0, limit=10, mark_used=False, include_archived=True, include_conflicted=True, include_stale=True)
    if not matches:
        return {"ok": False, "message": "I could not find a matching memory to forget.", "forgotten": [], "matches": []}
    if len(matches) > 1 and not key:
        return {
            "ok": False,
            "ambiguous": True,
            "message": "I found multiple matching memories. Which one should I forget?",
            "forgotten": [],
            "matches": [{"memory_id": item["memory_id"], "category": item["category"], "key": item["key"], "value": item["value"]} for item in matches],
        }
    forget_id = matches[0]["memory_id"]
    for item in memories:
        if item["memory_id"] == forget_id:
            item["status"] = "archived"
            item.setdefault("history", []).append({"at": _utc_now(), "event": "archived"})
            item["history"] = item["history"][-10:]
    payload["memories"] = memories
    _save_payload(payload)
    forgotten = matches[0]
    return {"ok": True, "message": f"Forgot memory: {forgotten['key'].replace('_', ' ')}.", "forgotten": [forgotten], "matches": []}


def memory_status() -> dict[str, Any]:
    memories = list_memories(min_confidence=0.0, include_archived=True, include_conflicted=True, include_stale=True)
    by_category: dict[str, int] = {}
    for memory in memories:
        by_category[memory["category"]] = by_category.get(memory["category"], 0) + 1
    return {
        "ok": True,
        "path": _memory_path(),
        "schema_version": MEMORY_SCHEMA_VERSION,
        "memory_count": len(memories),
        "active_count": len([item for item in memories if item.get("status") == "active" and not item.get("conflict_status")]),
        "archived_count": len([item for item in memories if item.get("status") == "archived"]),
        "conflict_count": len([item for item in memories if item.get("conflict_status")]),
        "stale_count": len([item for item in memories if is_memory_stale(item)]),
        "categories": by_category,
        "local_only": True,
        "cloud_sync": False,
    }


def memory_conflicts() -> dict[str, Any]:
    memories = list_memories(min_confidence=0.0, include_archived=False, include_conflicted=True, include_stale=True)
    conflicts = [item for item in memories if item.get("conflict_status")]
    if not conflicts:
        return {"ok": True, "conflicts": [], "message": "I do not see any unresolved memory conflicts."}
    message = "Memory conflicts: " + "; ".join(
        f"{item['key'].replace('_', ' ')} is {item['value']} but may need update to {item.get('pending_value')}" for item in conflicts[:5]
    )
    return {"ok": True, "conflicts": conflicts, "message": message}


def review_memories() -> dict[str, Any]:
    memories = list_memories(min_confidence=0.0, include_archived=True, include_conflicted=True, include_stale=True)
    active = [item for item in memories if item.get("status") == "active" and not item.get("conflict_status")]
    stale = [item for item in active if is_memory_stale(item)]
    low_quality = [item for item in active if item.get("quality_score", 0.0) < MIN_QUALITY_SCORE]
    conflicts = [item for item in memories if item.get("conflict_status")]
    suggestions = []
    if conflicts:
        suggestions.append(f"Resolve {len(conflicts)} memory conflict(s).")
    if stale:
        suggestions.append(f"Review {len(stale)} stale memory item(s).")
    if low_quality:
        suggestions.append(f"Archive {len(low_quality)} low-quality memory item(s).")
    if not suggestions:
        suggestions.append("No cleanup needed right now.")
    return {
        "ok": True,
        "message": f"Memory review: {len(active)} active, {len(conflicts)} conflicted, {len(stale)} stale. " + " ".join(suggestions),
        "active": active,
        "conflicts": conflicts,
        "stale": stale,
        "low_quality": low_quality,
        "suggestions": suggestions,
    }


def cleanup_memory_suggestions() -> dict[str, Any]:
    review = review_memories()
    candidates = []
    for item in review.get("stale", []):
        candidates.append({"memory_id": item["memory_id"], "category": item["category"], "key": item["key"], "value": item["value"], "reason": "stale"})
    for item in review.get("low_quality", []):
        if not any(existing["memory_id"] == item["memory_id"] for existing in candidates):
            candidates.append({"memory_id": item["memory_id"], "category": item["category"], "key": item["key"], "value": item["value"], "reason": "low_quality"})
    message = "No cleanup suggestions right now." if not candidates else f"I found {len(candidates)} memory cleanup suggestion(s). I will not delete them unless you confirm exactly what to forget."
    return {"ok": True, "message": message, "suggestions": candidates, "requires_confirmation": len(candidates) > 1}


def update_memory(category: str, key: str, value: Any, *, source: str = "user_explicit", confidence: float = 0.95) -> dict[str, Any]:
    return store_memory(category=category, key=key, value=value, source=source, confidence=confidence, manual=True, force_update=True)


def resolve_conflict(memory_id: str, decision: str) -> dict[str, Any]:
    normalized_id = compact_text(memory_id)
    normalized_decision = compact_text(decision).lower()
    if normalized_decision not in {"update", "keep_old", "cancel"}:
        return {"ok": False, "message": "I did not understand how to resolve that memory conflict.", "memory": {}, "stale": False}
    payload = _load_payload()
    memories = [_coerce_memory(item) for item in payload.get("memories", [])]
    memory = next((item for item in memories if item["memory_id"] == normalized_id), None)
    if memory is None or memory.get("status") == "archived":
        return {"ok": False, "message": "That memory conflict is no longer available, so I cleared the pending conflict.", "memory": {}, "stale": True}
    if not memory.get("conflict_status"):
        return {"ok": False, "message": "That memory no longer has a pending conflict.", "memory": memory, "stale": True}

    now = _utc_now()
    old_value = compact_text(memory.get("value"))
    pending_value = compact_text(memory.get("pending_value"))
    history = memory.setdefault("history", [])
    if normalized_decision == "update":
        if not pending_value:
            memory["conflict_status"] = ""
            memory["pending_value"] = ""
            history.append({"at": now, "event": "conflict_missing_pending_value", "old_value": old_value})
            message = "The pending memory value was missing, so I kept the existing memory."
        else:
            memory["value"] = pending_value
            memory["updated_at"] = now
            memory["last_used_at"] = now
            memory["manual"] = True
            memory["confidence"] = max(float(memory.get("confidence") or 0.0), 0.95)
            memory["conflict_status"] = ""
            memory["pending_value"] = ""
            history.append({"at": now, "event": "conflict_resolved_update", "old_value": old_value, "new_value": pending_value})
            message = f"Updated memory: {memory['key'].replace('_', ' ')} is now {pending_value}."
    elif normalized_decision == "keep_old":
        memory["conflict_status"] = ""
        memory["pending_value"] = ""
        memory["updated_at"] = now
        history.append({"at": now, "event": "conflict_resolved_keep_old", "kept_value": old_value, "rejected_value": pending_value})
        message = f"Kept the existing memory: {memory['key'].replace('_', ' ')} is still {old_value}."
    else:
        memory["conflict_status"] = ""
        memory["pending_value"] = ""
        history.append({"at": now, "event": "conflict_resolution_cancelled", "kept_value": old_value, "pending_value": pending_value})
        message = "Cancelled the memory update and kept the existing memory."

    memory["history"] = history[-10:]
    payload["memories"] = memories
    _save_payload(payload)
    return {"ok": True, "message": message, "memory": memory, "decision": normalized_decision, "stale": False}


def clear_memories_for_tests() -> None:
    path = _memory_path()
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _candidate(category: str, key: str, value: str, *, confidence: float, source: str, manual: bool = False) -> dict[str, Any]:
    return {
        "category": _normalize_category(category),
        "key": _normalize_key(key),
        "value": _safe_value(value),
        "confidence": confidence,
        "source": source,
        "manual": manual,
        "retention_policy": "long_term",
    }


def extract_memory_candidates(message: str) -> list[dict[str, Any]]:
    text = compact_text(message)
    normalized = text.lower()
    if not text or "don't remember this" in normalized or "dont remember this" in normalized or "do not remember this" in normalized:
        return []
    if _contains_sensitive(text):
        return []

    candidates: list[dict[str, Any]] = []
    explicit_match = re.search(r"\bremember(?: that| this|:)?\s+(.+)$", text, flags=re.IGNORECASE)
    explicit_text = compact_text(explicit_match.group(1)) if explicit_match else ""

    target = explicit_text or text
    target_lower = target.lower()

    name_match = re.search(r"\b(?:call me|my name is)\s+(.+)$", target, flags=re.IGNORECASE)
    if name_match:
        candidates.append(_candidate("user_preferences", "preferred_name", name_match.group(1), confidence=0.98, source="user_explicit", manual=bool(explicit_text)))

    editor_match = re.search(r"\b(?:i usually use|i use|my preferred editor is|my favorite editor is)\s+(?:the\s+)?(.+?)(?:\s+for\s+coding|\s+to\s+code)?$", target, flags=re.IGNORECASE)
    if editor_match and any(word in target_lower for word in ("vs code", "vscode", "visual studio code", "editor", "coding", "code")):
        value = editor_match.group(1)
        if "vs code" in target_lower or "vscode" in target_lower:
            value = "VS Code"
        candidates.append(_candidate("favorite_apps", "preferred_code_editor", value, confidence=0.88, source="implicit_preference", manual=bool(explicit_text)))

    prefer_match = re.search(r"\b(?:i prefer|i like|i usually prefer)\s+(.+)$", target, flags=re.IGNORECASE)
    if prefer_match:
        value = prefer_match.group(1)
        if "dark mode" in target_lower:
            candidates.append(_candidate("assistant_behavior_preferences", "interface_theme", "dark mode", confidence=0.82, source="implicit_preference", manual=bool(explicit_text)))
        elif "short" in target_lower or "concise" in target_lower:
            candidates.append(_candidate("communication_preferences", "response_style", "concise", confidence=0.82, source="implicit_preference", manual=bool(explicit_text)))
        elif "tamil" in target_lower or "tanglish" in target_lower:
            candidates.append(_candidate("communication_preferences", "language_style", value, confidence=0.82, source="implicit_preference", manual=bool(explicit_text)))

    work_match = re.search(r"\b(?:i work at|i work for|my company is)\s+(.+)$", target, flags=re.IGNORECASE)
    if work_match:
        candidates.append(_candidate("work_context", "company", work_match.group(1), confidence=0.86, source="implicit_preference", manual=bool(explicit_text)))

    music_match = re.search(r"\b(?:my favorite music is|i like listening to|i usually listen to)\s+(.+)$", target, flags=re.IGNORECASE)
    if music_match:
        candidates.append(_candidate("user_preferences", "favorite_music", music_match.group(1), confidence=0.84, source="implicit_preference", manual=bool(explicit_text)))

    return [candidate for candidate in candidates if candidate["value"] and not _contains_sensitive(f"{candidate['key']} {candidate['value']}")]


def remember_from_message(message: str, *, explicit: bool = False) -> dict[str, Any]:
    candidates = extract_memory_candidates(message)
    if explicit and not candidates:
        raw = re.sub(r"^\s*remember(?: that| this|:)?\s+", "", compact_text(message), flags=re.IGNORECASE)
        if raw and _contains_sensitive(raw):
            return {"ok": False, "stored": [], "blocked": [{"category": "blocked", "key": "sensitive", "value": ""}], "message": "I did not save that because it looks sensitive."}
        if raw:
            quality = score_memory_quality(category="user_preferences", key="note", value=raw, source="user_explicit")
            if not quality["durable"]:
                return {
                    "ok": False,
                    "stored": [],
                    "blocked": [],
                    "conflicts": [],
                    "low_quality": True,
                    "message": "I did not save that because it looks temporary or not useful as long-term memory.",
                    "quality": quality,
                }
            candidates = [_candidate("user_preferences", "note", raw, confidence=0.7, source="user_explicit", manual=True)]
    stored = []
    blocked = []
    conflicts = []
    for candidate in candidates:
        result = store_memory(**candidate)
        if result.get("ok"):
            stored.append(result["memory"])
        elif result.get("blocked"):
            blocked.append(candidate)
        elif result.get("conflict"):
            conflicts.append(result)
    if stored:
        labels = ", ".join(item["key"].replace("_", " ") for item in stored[:3])
        return {"ok": True, "stored": stored, "blocked": blocked, "message": f"I'll remember: {labels}."}
    if blocked:
        return {"ok": False, "stored": [], "blocked": blocked, "message": "I did not save that because it looks sensitive."}
    if conflicts:
        return {
            "ok": False,
            "stored": [],
            "blocked": [],
            "conflicts": conflicts,
            "message": compact_text(conflicts[0].get("message")) or "I found a possible memory conflict. Please confirm the update.",
        }
    return {"ok": False, "stored": [], "blocked": [], "conflicts": [], "message": "I did not find a useful long-term memory to save from that."}


def relevant_memory_hints(message: str, *, limit: int = 5) -> list[dict[str, Any]]:
    text = compact_text(message)
    memories = query_memories(text, min_confidence=DEFAULT_MIN_CONFIDENCE, limit=limit)
    # Add a few common preferences for planning even when the query is vague.
    for category, key in (
        ("user_preferences", "preferred_name"),
        ("favorite_apps", "preferred_code_editor"),
        ("user_preferences", "favorite_music"),
        ("communication_preferences", "response_style"),
    ):
        for item in query_memories("", category=category, key=key, min_confidence=DEFAULT_MIN_CONFIDENCE, limit=1):
            if not any(existing["memory_id"] == item["memory_id"] for existing in memories):
                memories.append(item)
    return memories[: max(1, min(int(limit or 5), 10))]
