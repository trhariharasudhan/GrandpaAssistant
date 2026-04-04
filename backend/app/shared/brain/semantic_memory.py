import datetime
import hashlib
import json
import threading

from brain.database import get_memory_rows
from utils.config import get_setting


DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
_LOCK = threading.Lock()
_BACKEND_CACHE = {
    "loaded": False,
    "backend": "lazy",
    "model_name": DEFAULT_MODEL_NAME,
    "model": None,
    "faiss": None,
    "faiss_available": False,
    "error": "",
}
_INDEX_CACHE = {
    "signature": None,
    "items": [],
    "index": None,
    "vectors": None,
    "backend": "lazy",
    "ready": False,
    "fallback_active": False,
    "entry_count": 0,
    "built_at": None,
    "error": "",
}


def _compact_text(value):
    return " ".join(str(value or "").split()).strip()


def _safe_int_setting(path, default):
    try:
        return max(1, int(get_setting(path, default)))
    except Exception:
        return default


def _safe_float_setting(path, default):
    try:
        return float(get_setting(path, default))
    except Exception:
        return default


def _tokenize(text):
    tokens = []
    for raw in _compact_text(text).lower().split():
        cleaned = "".join(char for char in raw if char.isalnum())
        if len(cleaned) >= 2:
            tokens.append(cleaned)
    return tokens


def _humanize_path(path):
    label = str(path or "").split(".")[-1].replace("_", " ").strip()
    return label or "saved field"


def _display_value(value):
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                values = [
                    _compact_text(inner_value)
                    for inner_value in item.values()
                    if _compact_text(inner_value)
                ]
                if values:
                    parts.append(", ".join(values))
            else:
                part = _compact_text(item)
                if part:
                    parts.append(part)
        return ", ".join(parts) or "empty"

    if isinstance(value, dict):
        parts = []
        for key, item_value in value.items():
            item_text = _compact_text(item_value)
            if not item_text:
                continue
            parts.append(f"{key.replace('_', ' ')}: {item_text}")
        return ", ".join(parts) or "empty"

    return _compact_text(value) or "empty"


def _row_signature(rows):
    digest = hashlib.sha1()
    for row in rows:
        digest.update(str(row.get("path") or "").encode("utf-8"))
        digest.update(str(row.get("updated_at") or "").encode("utf-8"))
        digest.update(
            json.dumps(
                row.get("value"),
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            ).encode("utf-8")
        )
    return digest.hexdigest()


def _status_payload(*, entry_count, indexed_count, ready, backend, fallback_active, error="", lazy=False):
    enabled = bool(get_setting("memory.semantic_search_enabled", True))
    model_name = _compact_text(get_setting("memory.semantic_search_model", DEFAULT_MODEL_NAME)) or DEFAULT_MODEL_NAME
    if not enabled:
        summary = "Semantic memory is disabled in settings."
    elif lazy:
        summary = "Semantic memory is configured and will load on first memory query."
    elif ready and indexed_count:
        summary = f"Semantic memory is ready with {indexed_count} indexed item(s) using {backend}."
    elif ready:
        summary = "Semantic memory is ready, but there are no saved memory items to index yet."
    elif error:
        summary = f"Semantic memory is not ready yet. {error}"
    else:
        summary = "Semantic memory is not ready yet."

    return {
        "enabled": enabled,
        "lazy": lazy,
        "ready": ready,
        "backend": backend,
        "model_name": model_name,
        "entry_count": entry_count,
        "indexed_count": indexed_count,
        "fallback_active": fallback_active,
        "faiss_available": bool(_BACKEND_CACHE.get("faiss_available")),
        "last_indexed_at": _INDEX_CACHE.get("built_at"),
        "error": error,
        "summary": summary,
    }


def _load_backend():
    with _LOCK:
        if _BACKEND_CACHE["loaded"]:
            return _BACKEND_CACHE

        model_name = _compact_text(get_setting("memory.semantic_search_model", DEFAULT_MODEL_NAME)) or DEFAULT_MODEL_NAME
        backend = {
            "loaded": True,
            "backend": "keyword-fallback",
            "model_name": model_name,
            "model": None,
            "faiss": None,
            "faiss_available": False,
            "error": "",
        }

        try:
            import faiss  # type: ignore

            backend["faiss"] = faiss
            backend["faiss_available"] = True
        except Exception:
            backend["faiss"] = None
            backend["faiss_available"] = False

        try:
            from sentence_transformers import SentenceTransformer

            backend["model"] = SentenceTransformer(model_name, device="cpu", local_files_only=True)
            backend["backend"] = "sentence-transformers"
        except Exception as error:
            backend["error"] = f"Could not load {model_name} locally, so keyword fallback is active: {error}"

        _BACKEND_CACHE.update(backend)
        return _BACKEND_CACHE


def _normalize_vectors(vectors):
    import numpy as np

    vectors = np.asarray(vectors, dtype="float32")
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def _encode_texts(model, texts):
    vectors = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return _normalize_vectors(vectors)


def _build_items(rows):
    items = []
    for row in rows:
        path = _compact_text(row.get("path"))
        if not path:
            continue
        value = row.get("value")
        if value is None:
            continue
        display = _display_value(value)
        if not display or display == "empty":
            continue
        label = _humanize_path(path)
        text = f"{label}. Saved path {path.replace('.', ' ')}. Saved value {display}."
        items.append(
            {
                "path": path,
                "label": label,
                "value": value,
                "display_value": display,
                "updated_at": row.get("updated_at"),
                "text": text,
                "tokens": set(_tokenize(text)),
            }
        )
    return items


def _ensure_index():
    enabled = bool(get_setting("memory.semantic_search_enabled", True))
    rows = get_memory_rows()
    entry_count = len(rows)

    if not enabled:
        with _LOCK:
            _INDEX_CACHE.update(
                {
                    "signature": None,
                    "items": [],
                    "index": None,
                    "vectors": None,
                    "backend": "disabled",
                    "ready": False,
                    "fallback_active": False,
                    "entry_count": entry_count,
                    "built_at": None,
                    "error": "",
                }
            )
        return _status_payload(
            entry_count=entry_count,
            indexed_count=0,
            ready=False,
            backend="disabled",
            fallback_active=False,
        )

    signature = _row_signature(rows)
    with _LOCK:
        if _INDEX_CACHE["signature"] == signature:
            return _status_payload(
                entry_count=_INDEX_CACHE["entry_count"],
                indexed_count=len(_INDEX_CACHE["items"]),
                ready=_INDEX_CACHE["ready"],
                backend=_INDEX_CACHE["backend"],
                fallback_active=_INDEX_CACHE["fallback_active"],
                error=_INDEX_CACHE["error"],
            )

    backend = _load_backend()
    items = _build_items(rows)
    index = None
    vectors = None
    backend_name = backend["backend"]
    ready = True
    fallback_active = backend_name != "sentence-transformers"
    error = backend.get("error", "")

    if items and backend_name == "sentence-transformers":
        try:
            vectors = _encode_texts(backend["model"], [item["text"] for item in items])
            if backend.get("faiss_available"):
                index = backend["faiss"].IndexFlatIP(vectors.shape[1])
                index.add(vectors)
                backend_name = "sentence-transformers+faiss"
            else:
                backend_name = "sentence-transformers+numpy"
        except Exception as encode_error:
            index = None
            vectors = None
            backend_name = "keyword-fallback"
            fallback_active = True
            error = f"Semantic embeddings were unavailable, so keyword fallback is active: {encode_error}"

    with _LOCK:
        _INDEX_CACHE.update(
            {
                "signature": signature,
                "items": items,
                "index": index,
                "vectors": vectors,
                "backend": backend_name,
                "ready": ready,
                "fallback_active": fallback_active,
                "entry_count": entry_count,
                "built_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "error": error,
            }
        )

    return _status_payload(
        entry_count=entry_count,
        indexed_count=len(items),
        ready=ready,
        backend=backend_name,
        fallback_active=fallback_active,
        error=error,
    )


def semantic_memory_status(*, prewarm=False):
    if prewarm:
        return _ensure_index()

    rows = get_memory_rows()
    with _LOCK:
        if _INDEX_CACHE["signature"] is not None:
            return _status_payload(
                entry_count=_INDEX_CACHE["entry_count"],
                indexed_count=len(_INDEX_CACHE["items"]),
                ready=_INDEX_CACHE["ready"],
                backend=_INDEX_CACHE["backend"],
                fallback_active=_INDEX_CACHE["fallback_active"],
                error=_INDEX_CACHE["error"],
            )

    return _status_payload(
        entry_count=len(rows),
        indexed_count=0,
        ready=False,
        backend="lazy",
        fallback_active=False,
        lazy=True,
    )


def _keyword_matches(items, query, limit):
    query_tokens = set(_tokenize(query))
    query_text = query.lower()
    scored = []
    for item in items:
        overlap = len(query_tokens & item["tokens"])
        contains_query = 1.0 if query_text and query_text in item["text"].lower() else 0.0
        contains_value = 0.4 if query_text and query_text in item["display_value"].lower() else 0.0
        score = (overlap / max(1, len(query_tokens))) + (0.25 * contains_query) + (0.15 * contains_value)
        if score <= 0:
            continue
        scored.append((score, item))

    scored.sort(key=lambda entry: entry[0], reverse=True)
    return scored[:limit]


def _result_payload(item, score):
    return {
        "path": item["path"],
        "label": item["label"],
        "value": item["value"],
        "display_value": item["display_value"],
        "updated_at": item.get("updated_at"),
        "score": round(float(score), 4),
        "is_plural": isinstance(item["value"], list),
    }


def search_semantic_memory(query, limit=None, min_score=None):
    cleaned_query = _compact_text(query)
    if not cleaned_query or not bool(get_setting("memory.semantic_search_enabled", True)):
        return []

    _ensure_index()
    with _LOCK:
        items = list(_INDEX_CACHE["items"])
        backend = _INDEX_CACHE["backend"]
        index = _INDEX_CACHE["index"]
        vectors = _INDEX_CACHE["vectors"]
        model = _BACKEND_CACHE.get("model")

    if not items:
        return []

    limit = max(1, min(int(limit or _safe_int_setting("memory.semantic_search_top_k", 4)), 8))
    threshold = float(min_score if min_score is not None else _safe_float_setting("memory.semantic_search_min_score", 0.3))
    scored = []

    if backend.startswith("sentence-transformers") and model is not None:
        try:
            query_vector = _encode_texts(model, [cleaned_query])
            if index is not None:
                scores, indices = index.search(query_vector, min(limit * 2, len(items)))
                for score, index_pos in zip(scores[0], indices[0]):
                    if index_pos < 0:
                        continue
                    scored.append((float(score), items[int(index_pos)]))
            elif vectors is not None:
                import numpy as np

                similarities = np.dot(vectors, query_vector[0])
                best_indices = similarities.argsort()[::-1][: min(limit * 2, len(items))]
                for index_pos in best_indices:
                    scored.append((float(similarities[int(index_pos)]), items[int(index_pos)]))
        except Exception:
            scored = []

    if not scored:
        scored = _keyword_matches(items, cleaned_query, limit * 2)
        threshold = min(threshold, 0.2)

    results = []
    seen_paths = set()
    for score, item in scored:
        if score < threshold:
            continue
        if item["path"] in seen_paths:
            continue
        seen_paths.add(item["path"])
        results.append(_result_payload(item, score))
        if len(results) >= limit:
            break
    return results


def get_semantic_memory_lines(query, limit=None):
    lines = []
    for item in search_semantic_memory(query, limit=limit):
        lines.append(f"{item['label']}: {item['display_value']}")
    return lines


def build_semantic_memory_context(query, max_items=None, max_chars=None):
    if not bool(get_setting("memory.semantic_context_enabled", True)):
        return None

    max_items = max(1, min(int(max_items or _safe_int_setting("memory.semantic_context_top_k", 3)), 6))
    max_chars = max(200, int(max_chars or _safe_int_setting("memory.semantic_context_max_chars", 900)))
    results = search_semantic_memory(query, limit=max_items)
    if not results:
        return None

    lines = []
    used_chars = 0
    for item in results:
        line = f"- {item['label']}: {item['display_value']}"
        if used_chars + len(line) > max_chars and lines:
            break
        lines.append(line)
        used_chars += len(line)

    if not lines:
        return None

    return (
        "Relevant saved memory for this user. Use these details only when they help answer the question.\n"
        + "\n".join(lines)
    )


def semantic_memory_search_summary(query, limit=3):
    results = search_semantic_memory(query, limit=limit)
    if not results:
        return "I could not find a strongly matching saved memory for that."

    first = results[0]
    verb = "are" if first["is_plural"] else "is"
    summary = f"I found this saved memory: your {first['label']} {verb} {first['display_value']}."
    related = []
    for item in results[1:]:
        item_verb = "are" if item["is_plural"] else "is"
        related.append(f"{item['label']} {item_verb} {item['display_value']}")
    if related:
        summary += " Related saved details: " + " | ".join(related) + "."
    return summary


def semantic_memory_status_summary():
    status = semantic_memory_status(prewarm=False)
    return status["summary"]
