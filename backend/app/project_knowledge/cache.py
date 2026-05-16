from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from .config import CACHE_DIRECTORY, CACHE_INDEX_TYPE, CACHE_SCHEMA_VERSION
from .content_reader import redact_obvious_secrets
from .file_discovery import discover_project_files


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _mtime_value(value: Any) -> float:
    try:
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value or "").strip()
        if not text:
            return 0.0
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).timestamp()
    except (TypeError, ValueError, OSError):
        return 0.0


def _safe_root(project_root: Any) -> Path | None:
    try:
        root = Path(project_root).resolve()
    except (OSError, TypeError, ValueError):
        return None
    if not root.exists() or not root.is_dir():
        return None
    return root


def _project_cache_key(project_root: Path) -> str:
    return sha256(str(project_root).lower().encode("utf-8")).hexdigest()[:16]


def get_cache_dir() -> Path:
    return Path.cwd() / CACHE_DIRECTORY


def get_cache_paths(project_root: Any) -> dict:
    root = _safe_root(project_root)
    if root is None:
        key = "invalid"
    else:
        key = _project_cache_key(root)
    base = get_cache_dir() / key
    return {
        "cache_dir": base,
        "manifest": base / "manifest.json",
        "chunks": base / "chunks.json",
        "index": base / "lexical_index.json",
    }


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as handle:
        temp_path = Path(handle.name)
        json.dump(data, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    temp_path.replace(path)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sanitize_chunk(chunk: dict) -> dict:
    clean = dict(chunk)
    text, _changed = redact_obvious_secrets(str(clean.get("text") or ""))
    clean["text"] = text
    return clean


def _sanitize_index(index: dict) -> dict:
    clean = dict(index or {})
    documents = clean.get("documents") if isinstance(clean.get("documents"), dict) else {}
    sanitized_documents: dict[str, dict] = {}
    for key, value in documents.items():
        if not isinstance(value, dict):
            continue
        item = dict(value)
        text, _changed = redact_obvious_secrets(str(item.get("text") or ""))
        item["text"] = text
        sanitized_documents[str(key)] = item
    clean["documents"] = sanitized_documents
    return clean


def build_cache_manifest(project_root: Any, *, files: list[dict] | None = None, chunks: list[dict] | None = None) -> dict:
    root = _safe_root(project_root)
    root_text = str(root) if root is not None else ""
    safe_files = files if files is not None else (discover_project_files(root) if root is not None else [])
    safe_chunks = chunks or []
    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        "created_at": _utc_now(),
        "project_root": root_text,
        "file_count": len(safe_files),
        "chunk_count": len(safe_chunks),
        "index_type": CACHE_INDEX_TYPE,
        "safe": True,
        "files": [
            {
                "relative_path": str(item.get("relative_path") or ""),
                "size_bytes": int(item.get("size_bytes") or 0),
                "modified_time": item.get("modified_time"),
                "modified_time_epoch": _mtime_value(item.get("modified_time")),
                "extension": str(item.get("extension") or ""),
            }
            for item in safe_files
            if isinstance(item, dict)
        ],
    }


def load_project_cache(project_root: Any) -> dict:
    paths = get_cache_paths(project_root)
    try:
        manifest = _load_json(paths["manifest"])
        chunks = _load_json(paths["chunks"])
        index = _load_json(paths["index"])
        return {
            "ok": True,
            "manifest": manifest if isinstance(manifest, dict) else {},
            "chunks": chunks if isinstance(chunks, list) else [],
            "lexical_index": index if isinstance(index, dict) else {},
            "cache_dir": str(paths["cache_dir"]),
            "error": None,
        }
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "ok": False,
            "manifest": {},
            "chunks": [],
            "lexical_index": {},
            "cache_dir": str(paths["cache_dir"]),
            "error": type(exc).__name__,
        }


def save_project_cache(project_root: Any, data: dict) -> dict:
    paths = get_cache_paths(project_root)
    try:
        manifest = data.get("manifest") if isinstance(data.get("manifest"), dict) else build_cache_manifest(project_root)
        chunks = data.get("chunks") if isinstance(data.get("chunks"), list) else []
        index = data.get("lexical_index") if isinstance(data.get("lexical_index"), dict) else {}
        safe_chunks = [_sanitize_chunk(chunk) for chunk in chunks if isinstance(chunk, dict)]
        safe_index = _sanitize_index(index)
        _atomic_write_json(paths["manifest"], manifest)
        _atomic_write_json(paths["chunks"], safe_chunks)
        _atomic_write_json(paths["index"], safe_index)
        return {"ok": True, "cache_dir": str(paths["cache_dir"]), "error": None}
    except (OSError, TypeError, ValueError) as exc:
        return {"ok": False, "cache_dir": str(paths["cache_dir"]), "error": type(exc).__name__}


def clear_project_cache(project_root: Any) -> dict:
    paths = get_cache_paths(project_root)
    try:
        if paths["cache_dir"].exists():
            shutil.rmtree(paths["cache_dir"])
        return {"ok": True, "cache_dir": str(paths["cache_dir"]), "cleared": True, "error": None}
    except OSError as exc:
        return {"ok": False, "cache_dir": str(paths["cache_dir"]), "cleared": False, "error": type(exc).__name__}


def is_cache_valid(project_root: Any, manifest: dict) -> bool:
    root = _safe_root(project_root)
    if root is None or not isinstance(manifest, dict):
        return False
    if int(manifest.get("schema_version") or 0) != CACHE_SCHEMA_VERSION:
        return False
    if str(manifest.get("index_type") or "") != CACHE_INDEX_TYPE:
        return False
    if str(manifest.get("project_root") or "") != str(root):
        return False

    cached_files = manifest.get("files") if isinstance(manifest.get("files"), list) else []
    cached_by_path = {
        str(item.get("relative_path") or ""): item
        for item in cached_files
        if isinstance(item, dict) and item.get("relative_path")
    }
    current_files = discover_project_files(root)
    if len(current_files) != len(cached_by_path):
        return False

    for current in current_files:
        relative_path = str(current.get("relative_path") or "")
        cached = cached_by_path.get(relative_path)
        if not cached:
            return False
        if int(current.get("size_bytes") or 0) != int(cached.get("size_bytes") or 0):
            return False
        current_mtime = _mtime_value(current.get("modified_time"))
        cached_mtime = _mtime_value(cached.get("modified_time_epoch") or cached.get("modified_time"))
        if current_mtime > cached_mtime + 0.001:
            return False
    return True
