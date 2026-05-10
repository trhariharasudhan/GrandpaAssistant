from __future__ import annotations

import ast
import datetime as _dt
import operator
import re
from dataclasses import dataclass

from .language import detect_language_style


@dataclass
class IntentResult:
    handled: bool
    intent: str = "general"
    reply: str = ""


_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 10:
            raise ValueError("Exponent too large")
        return _OPS[type(node.op)](left, right)
    raise ValueError("Unsupported expression")


def _calculator(text: str) -> str | None:
    cleaned = text.strip().lower().replace("×", "*").replace("÷", "/")
    cleaned = re.sub(r"^(?:what\s+is|calculate|calc|solve)\s+", "", cleaned).strip()
    if not re.fullmatch(r"[\d\s+\-*/().%]+", cleaned):
        return None
    if not re.search(r"\d\s*[\-+*/%]\s*\d", cleaned):
        return None
    try:
        value = _safe_eval(ast.parse(cleaned, mode="eval"))
    except Exception:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value)


def _is_harmful(text: str) -> bool:
    lowered = text.lower()
    harmful = [
        "steal password",
        "hack into",
        "malware",
        "phishing",
        "bypass login",
        "credit card dump",
        "make a bomb",
    ]
    return any(item in lowered for item in harmful)


def route_intent(message: str) -> IntentResult:
    cleaned = " ".join(str(message or "").split()).strip()
    lowered = cleaned.lower()
    style = detect_language_style(cleaned)
    if not cleaned:
        return IntentResult(True, "empty", "Type something da, I am listening.")
    if _is_harmful(cleaned):
        return IntentResult(True, "safety", "I cannot help with harmful or illegal stuff. I can help with a safe alternative.")
    if lowered in {"hi", "hello", "hey", "hi da", "hello da", "vanakkam"}:
        if lowered == "vanakkam":
            reply = "Vanakkam da! Enna help venum?"
        else:
            reply = "Hi da! Enna help venum?" if style in {"tamil", "tanglish"} else "Hi! What can I help with?"
        return IntentResult(True, "greeting", reply)
    if re.search(r"\b(time|current time|time now)\b", lowered) or "what is time now" in lowered:
        now = _dt.datetime.now().strftime("%I:%M %p")
        return IntentResult(True, "time", f"Current time is {now}.")
    if re.search(r"\b(date|today's date|today date)\b", lowered):
        today = _dt.datetime.now().strftime("%B %d, %Y")
        return IntentResult(True, "date", f"Today's date is {today}.")
    math_reply = _calculator(cleaned)
    if math_reply is not None:
        return IntentResult(True, "calculator", math_reply)
    if "grandpaassistant" in lowered and any(word in lowered for word in {"run", "start", "terminal", "install", "project", "help"}):
        return IntentResult(
            True,
            "project_help",
            "Use python -m backend.app.cli.chat to run terminal chat. Use python scripts/smoke_test_terminal_chat.py for a quick smoke test.",
        )
    if any(word in lowered for word in {"latest", "today news", "current news", "live update"}):
        return IntentResult(True, "live_info_warning", "I may need live search for latest info. Share a source and I can help summarize it.")
    return IntentResult(False)
