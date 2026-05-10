from __future__ import annotations

import argparse
import json
import os
import sys

from backend.app.core.chatbot import ChatbotEngine


APP_TITLE = "GrandpaAssistant Terminal Chat"


HELP_TEXT = """Commands:
/exit or /quit       Stop chat
/clear               Clear current session messages
/history             Show recent conversation
/reset               Start a new session
/help                Show this help
/provider            Show current AI provider
/model               Show current model
/memory              Show saved memory facts
/save <fact>         Save a memory fact
/forget <keyword>    Forget matching memory facts
/config              Show config without secrets
"""


def _print_header(engine: ChatbotEngine) -> None:
    print(APP_TITLE)
    print(f"Provider: {engine.provider_name()}")
    print("Type /help for commands\n")


def _handle_slash_command(engine: ChatbotEngine, text: str) -> tuple[bool, bool]:
    command = text.strip()
    lowered = command.lower()
    if lowered in {"/exit", "/quit"}:
        print("Grandpa: Bye da, take care.")
        return True, True
    if lowered == "/help":
        print(HELP_TEXT)
        return True, False
    if lowered == "/clear":
        engine.clear_current_session()
        os.system("cls" if os.name == "nt" else "clear")
        _print_header(engine)
        print("Grandpa: Screen and current session cleared.")
        return True, False
    if lowered == "/history":
        print(engine.recent_history_text())
        return True, False
    if lowered == "/reset":
        new_session = engine.reset_session()
        print(f"Grandpa: New session started: {new_session}")
        return True, False
    if lowered == "/provider":
        print(f"Grandpa: Current provider is {engine.provider_name()}.")
        return True, False
    if lowered == "/model":
        print(f"Grandpa: Current model is {engine.model_name()}.")
        return True, False
    if lowered == "/memory":
        print(f"Grandpa: {engine.memory_summary()}")
        return True, False
    if lowered.startswith("/save "):
        print(f"Grandpa: {engine.save_memory(command[6:].strip())}")
        return True, False
    if lowered.startswith("/forget "):
        print(f"Grandpa: {engine.forget_memory(command[8:].strip())}")
        return True, False
    if lowered == "/config":
        print(json.dumps(engine.config_summary(), indent=2))
        return True, False
    if lowered.startswith("/"):
        print("Grandpa: Unknown command. Type /help.")
        return True, False
    return False, False


def run_chat(session_id: str | None = None, smoke_message: str | None = None) -> int:
    engine = ChatbotEngine(session_id=session_id)
    _print_header(engine)

    if smoke_message:
        print(f"You: {smoke_message}")
        print(f"Grandpa: {engine.reply(smoke_message)}")
        return 0

    while True:
        try:
            user_text = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGrandpa: Bye da, take care.")
            return 0
        if not user_text:
            continue
        handled, should_exit = _handle_slash_command(engine, user_text)
        if should_exit:
            return 0
        if handled:
            continue
        print(f"Grandpa: {engine.reply(user_text)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Terminal-only GrandpaAssistant chatbot.")
    parser.add_argument("--session-id", help="Use a fixed chat session id.")
    parser.add_argument("--smoke", help="Send one message and exit.")
    args = parser.parse_args(argv)
    return run_chat(session_id=args.session_id, smoke_message=args.smoke)


if __name__ == "__main__":
    raise SystemExit(main())
