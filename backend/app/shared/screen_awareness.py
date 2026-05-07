from __future__ import annotations

import datetime
import re
from typing import Any

from vision import screen_reader


NO_TEXT_MESSAGE = "Readable text was not clearly detected on the screen."
OCR_UNAVAILABLE_MESSAGE = "Tesseract OCR is not installed or not available in PATH."
ERROR_PATTERNS = (
    r"\berror\b",
    r"\bexception\b",
    r"\bfailed\b",
    r"\bfailure\b",
    r"\btraceback\b",
    r"\bcrash(?:ed)?\b",
    r"\bdenied\b",
    r"\bnot found\b",
    r"\bunable to\b",
    r"\bcannot\b",
    r"\bcan't\b",
    r"\bwarning\b",
)


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _looks_tamil(text: str) -> bool:
    raw = str(text or "")
    return any("\u0b80" <= char <= "\u0bff" for char in raw) or any(
        token in raw.lower()
        for token in (" enna ", " iruku", " irukku", " sollu", " padichu", "screen la")
    )


def _resolve_language(language: str, text: str = "") -> str:
    requested = str(language or "auto").strip().lower()
    if requested in {"ta", "tamil"}:
        return "ta"
    if requested in {"en", "english"}:
        return "en"
    return "ta" if _looks_tamil(text) else "en"


def _safe_warning(message: str, *, language: str = "en") -> dict[str, Any]:
    tamil = _resolve_language(language) == "ta"
    friendly = (
        "திரையை படிக்க OCR அல்லது screenshot வசதி தயார் இல்லை."
        if tamil
        else "I cannot read the screen right now because OCR or screenshot capture is not ready."
    )
    return {
        "ok": False,
        "warning": True,
        "message": friendly,
        "detail": _compact_text(message),
        "timestamp": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


def capture_screen_snapshot() -> dict[str, Any]:
    pyautogui = getattr(screen_reader, "pyautogui", None)
    if pyautogui is None:
        return _safe_warning("Screen capture dependency pyautogui is not available.")
    try:
        screenshot = pyautogui.screenshot()
        size = getattr(screenshot, "size", None)
        width, height = size if isinstance(size, tuple) and len(size) == 2 else (None, None)
        try:
            close = getattr(screenshot, "close", None)
            if callable(close):
                close()
        except Exception:
            pass
        return {
            "ok": True,
            "captured": True,
            "stored": False,
            "width": width,
            "height": height,
            "timestamp": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
    except Exception as error:
        return _safe_warning(str(error) or "Screen capture failed.")


def extract_screen_text() -> dict[str, Any]:
    try:
        text = screen_reader.read_screen_text()
    except Exception as error:
        return {
            **_safe_warning(str(error) or "OCR failed."),
            "text": "",
            "lines": [],
        }
    clean_text = str(text or "").strip()
    if clean_text in {OCR_UNAVAILABLE_MESSAGE, NO_TEXT_MESSAGE}:
        return {
            **_safe_warning(clean_text),
            "text": "",
            "lines": [],
        }
    lines = [_compact_text(line) for line in clean_text.splitlines() if _compact_text(line)]
    return {
        "ok": True,
        "warning": False,
        "text": "\n".join(lines),
        "lines": lines,
        "line_count": len(lines),
        "timestamp": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }


def detect_error_like_text(text: str | None = None) -> dict[str, Any]:
    if text is None:
        payload = extract_screen_text()
        text = payload.get("text", "")
    raw = str(text or "")
    matches = []
    for pattern in ERROR_PATTERNS:
        if re.search(pattern, raw, flags=re.IGNORECASE):
            matches.append(pattern.strip("\\b"))
    lines = []
    for line in raw.splitlines():
        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in ERROR_PATTERNS):
            lines.append(_compact_text(line))
    return {
        "has_error_like_text": bool(matches),
        "matches": sorted(set(matches)),
        "lines": lines[:8],
    }


def _summary_from_lines(lines: list[str], *, language: str) -> str:
    trimmed = [_compact_text(line) for line in lines if _compact_text(line)]
    if not trimmed:
        return (
            "திரையில் தெளிவான உரை தெரியவில்லை."
            if language == "ta"
            else "I cannot see clear readable text on the screen."
        )
    preview = "; ".join(trimmed[:5])
    if language == "ta":
        return f"திரையில் படிக்கக்கூடிய உரை தெரிகிறது: {preview}"
    return f"I can read this on the screen: {preview}"


def summarize_screen_context(language: str = "auto") -> dict[str, Any]:
    text_payload = extract_screen_text()
    resolved_language = _resolve_language(language, text_payload.get("text", ""))
    if not text_payload.get("ok"):
        warning = _safe_warning(text_payload.get("detail") or text_payload.get("message"), language=resolved_language)
        return {
            **warning,
            "language": resolved_language,
            "text": "",
            "lines": [],
            "error_detection": {"has_error_like_text": False, "matches": [], "lines": []},
            "summary": warning["message"],
        }
    error_detection = detect_error_like_text(text_payload.get("text", ""))
    summary = _summary_from_lines(text_payload.get("lines", []), language=resolved_language)
    if error_detection["has_error_like_text"]:
        if resolved_language == "ta":
            summary += " இதில் பிழை அல்லது warning போல ஒரு செய்தி இருக்கலாம்."
        else:
            summary += " I also see text that looks like an error or warning."
    return {
        "ok": True,
        "warning": False,
        "language": resolved_language,
        "text": text_payload.get("text", ""),
        "lines": text_payload.get("lines", []),
        "summary": summary,
        "error_detection": error_detection,
        "timestamp": text_payload.get("timestamp"),
    }


def explain_screen(language: str = "auto") -> str:
    payload = summarize_screen_context(language=language)
    if not payload.get("ok"):
        return payload.get("summary") or payload.get("message") or "I cannot read the screen right now."
    error_detection = payload.get("error_detection", {})
    if error_detection.get("has_error_like_text"):
        first_error = (error_detection.get("lines") or [""])[0]
        if payload.get("language") == "ta":
            return f"{payload['summary']} முக்கியமான வரி: {first_error}" if first_error else payload["summary"]
        return f"{payload['summary']} The likely issue is around: {first_error}" if first_error else payload["summary"]
    return payload["summary"]
