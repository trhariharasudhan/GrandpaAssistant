from __future__ import annotations

import re
from typing import Any


CODING_EXTENSIONS = re.compile(r"\.(?:py|js|jsx|ts|tsx|html|css|sql|json|yaml|yml|toml|md)\b", re.IGNORECASE)
CODE_COMMANDS = re.compile(r"\b(?:python\s+-m|pip\s+install|npm\s+(?:run|install|test)|uvicorn|pytest|unittest|git\s+(?:status|diff|log|commit|push|pull|add))\b", re.IGNORECASE)
CLEAR_PHRASES = (
    "fix this code",
    "debug this",
    "stack trace",
    "traceback",
    "import error",
    "syntax error",
    "type error",
    "runtime error",
    "unit test",
    "write a function",
    "create a function",
    "write code",
    "code bug",
    "bug in",
)
CODING_TERMS = {
    "python",
    "fastapi",
    "javascript",
    "typescript",
    "react",
    "html",
    "css",
    "sql",
    "pytest",
    "unittest",
    "function",
    "class",
    "module",
    "api",
    "endpoint",
    "bug",
    "code",
}
CONTEXT_TERMS = {
    "fix",
    "debug",
    "error",
    "failing",
    "fails",
    "test",
    "tests",
    "issue",
    "exception",
    "implement",
    "build",
    "write",
    "create",
}
PLANNING_PHRASES = (
    "make a plan",
    "break this into steps",
    "step by step plan",
    "architecture plan",
    "roadmap",
    "implementation plan",
    "task decomposition",
    "decompose this",
    "plan my day",
    "today agenda",
    "my agenda",
    "today plan",
    "daily plan",
    "schedule my day",
    "what should i do now",
    "what should i do today",
    "prioritize my day",
    "day plan",
)


def _clean_message(message: Any) -> str:
    return " ".join(str(message or "").split()).strip().lower()


def detect_planning_intent(message: str | None) -> bool:
    text = _clean_message(message)
    if not text:
        return False
    return any(phrase in text for phrase in PLANNING_PHRASES)


def resolve_prompt_mode(message: str | None, default: str = "default", *, allow_planning: bool = False) -> str:
    """Resolve a conservative runtime prompt mode for chat_service.

    By default this returns only ``default`` or ``coding`` for chat_service.
    ``planning`` is dormant unless a caller explicitly opts in with
    ``allow_planning=True``.
    """
    text = _clean_message(message)
    if not text:
        return default or "default"

    if allow_planning and detect_planning_intent(text):
        return "planning"

    if CODING_EXTENSIONS.search(text) or CODE_COMMANDS.search(text):
        return "coding"

    if any(phrase in text for phrase in CLEAR_PHRASES):
        return "coding"

    tokens = set(re.findall(r"[a-z0-9_+#.-]+", text))
    if {"stack", "trace"}.issubset(tokens):
        return "coding"

    if tokens.intersection(CODING_TERMS) and tokens.intersection(CONTEXT_TERMS):
        return "coding"

    return default or "default"
