from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .config import DEFAULT_LIMITS
from .file_filters import is_safe_to_index, normalize_project_path, should_ignore_directory


_SENSITIVE_KEY_RE = re.compile(
    r"(?i)(([\"']?\b(?:password|token|api[_-]?key|secret|credential|otp|pin)\b[\"']?\s*[:=]\s*)([\"']?))([^\"'\s,}#]+)([\"']?)"
)
_BEARER_RE = re.compile(r"(?i)(\bbearer\s+)([A-Za-z0-9._~+/=-]+)")
_PRIVATE_KEY_RE = re.compile(r"(?i)(private\s+key|-----BEGIN [A-Z ]*PRIVATE KEY-----)")


def _empty_result(path: Any = "", error: str | None = None) -> dict:
    return {
        "ok": False,
        "relative_path": normalize_project_path(path),
        "encoding": "",
        "text": "",
        "truncated": False,
        "redacted": False,
        "size_bytes": 0,
        "error": error,
    }


def _relative_path(path: Path, project_root: Path | None) -> str:
    if project_root is not None:
        try:
            return normalize_project_path(path.resolve().relative_to(project_root.resolve()))
        except (OSError, ValueError):
            pass
    return normalize_project_path(path.name)


def _is_inside_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def is_probably_binary(path: Any) -> bool:
    try:
        candidate = Path(path)
        with candidate.open("rb") as handle:
            sample = handle.read(DEFAULT_LIMITS.binary_detection_bytes)
        return b"\x00" in sample
    except (OSError, TypeError, ValueError):
        return True


def redact_obvious_secrets(text: str) -> tuple[str, bool]:
    redacted = False
    output_lines: list[str] = []
    for line in str(text or "").splitlines(keepends=True):
        updated = line
        if _PRIVATE_KEY_RE.search(updated):
            updated = re.sub(r"[^\r\n]+", "[REDACTED_PRIVATE_KEY_LINE]", updated)
        updated = _SENSITIVE_KEY_RE.sub(r"\1[REDACTED]\5", updated)
        updated = _BEARER_RE.sub(r"\1[REDACTED]", updated)
        if updated != line:
            redacted = True
        output_lines.append(updated)
    return "".join(output_lines), redacted


def read_text_file_safely(path: Any, project_root: Any | None = None) -> dict:
    try:
        candidate = Path(path)
        root = Path(project_root) if project_root is not None else None
    except (TypeError, ValueError):
        return _empty_result(path, "malformed_path")

    relative_path = _relative_path(candidate, root)
    result = _empty_result(relative_path)
    result["relative_path"] = relative_path

    try:
        if root is not None and not _is_inside_root(candidate, root):
            result["error"] = "outside_project_root"
            return result
        if should_ignore_directory(candidate.parent) or not is_safe_to_index(candidate):
            result["error"] = "unsupported_or_unsafe_file"
            return result
        stat = candidate.stat()
        result["size_bytes"] = int(stat.st_size)
        if is_probably_binary(candidate):
            result["error"] = "binary_file"
            return result

        truncated = result["size_bytes"] > DEFAULT_LIMITS.max_read_bytes
        with candidate.open("rb") as handle:
            raw = handle.read(DEFAULT_LIMITS.max_read_bytes)

        encoding = "utf-8"
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            encoding = "utf-8-replace"
            text = raw.decode("utf-8", errors="replace")

        text, redacted = redact_obvious_secrets(text)
        result.update(
            {
                "ok": True,
                "encoding": encoding,
                "text": text,
                "truncated": truncated,
                "redacted": redacted,
                "error": None,
            }
        )
        return result
    except (OSError, TypeError, ValueError) as exc:
        result["error"] = exc.__class__.__name__
        return result
