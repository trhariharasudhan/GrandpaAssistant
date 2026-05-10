from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config.grandpa_config import GrandpaConfig
from backend.app.core.chatbot import ChatbotEngine
from backend.app.core.chatbot.intent_router import route_intent


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        config = GrandpaConfig(
            provider="fallback",
            model="rules",
            db_path=str(Path(tmp) / "grandpa_chat.db"),
            log_path=str(Path(tmp) / "grandpa.log"),
            log_level="INFO",
        )
        engine = ChatbotEngine(config=config, session_id="smoke")
        try:
            assert_true(engine.provider_name() == "fallback", "fallback provider should load")
            reply = engine.reply("hi da")
            assert_true("Hi da" in reply, "greeting intent should reply locally")
            assert_true(route_intent("what is time now").handled, "time intent should be handled")
            assert_true(route_intent("2+2").reply == "4", "math intent should calculate")
            assert_true("python -m backend.app.cli.chat" in engine.reply("GrandpaAssistant terminal help"), "project help should work")
            assert_true(engine.save_memory("my name is Hari") == "Saved da.", "memory save should work")
            assert_true("my name is Hari" in engine.memory_summary(), "memory summary should include saved fact")
            history = engine.memory.recent_messages("smoke", limit_turns=10)
            assert_true(any(item["role"] == "user" for item in history), "chat memory should store user messages")
            assert_true(Path(config.db_path).exists(), "database should be created")
        finally:
            engine.close()

    print("[PASS] imports work")
    print("[PASS] DB initializes")
    print("[PASS] fallback provider replies")
    print("[PASS] chat memory insert/read works")
    print("[PASS] config loads")
    print("[PASS] intent router handles greeting/time/math")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
