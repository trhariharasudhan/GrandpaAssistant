from __future__ import annotations

import logging
from pathlib import Path
import uuid

from backend.app.config.grandpa_config import GrandpaConfig, load_config, resolve_path
from .intent_router import route_intent
from .memory import ChatMemory, compact_text
from .prompt_builder import build_system_prompt
from .providers import FallbackProvider, GeminiProvider, OllamaProvider, OpenAIProvider
from .providers.base import ProviderResult


FALLBACK_REPLY = "I couldn't get an answer right now. Please try again."


def configure_logging(config: GrandpaConfig) -> logging.Logger:
    log_path = resolve_path(config.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("grandpa_terminal_chat")
    logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
    for existing in list(logger.handlers):
        if isinstance(existing, logging.FileHandler):
            logger.removeHandler(existing)
            existing.close()
    handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


class ChatbotEngine:
    def __init__(self, config: GrandpaConfig | None = None, session_id: str | None = None):
        self.config = config or load_config()
        self.logger = configure_logging(self.config)
        self.memory = ChatMemory(self.config.db_path)
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.logger.info("startup config=%s", self.config.safe_summary())

    def close(self) -> None:
        for handler in list(self.logger.handlers):
            if isinstance(handler, logging.FileHandler):
                self.logger.removeHandler(handler)
                handler.close()

    def _provider(self):
        provider = (self.config.provider or "fallback").lower()
        model = self.config.model
        if provider == "openai":
            return OpenAIProvider(self.config.openai_api_key, model, self.config.openai_base_url, self.config.timeout_seconds)
        if provider == "gemini":
            return GeminiProvider(self.config.gemini_api_key, model, self.config.gemini_base_url, self.config.timeout_seconds)
        if provider == "ollama":
            return OllamaProvider(model, self.config.ollama_base_url, self.config.timeout_seconds)
        return FallbackProvider(model="rules")

    def provider_name(self) -> str:
        return self._provider().name

    def model_name(self) -> str:
        return self._provider().model

    def config_summary(self) -> dict:
        return self.config.safe_summary()

    def reset_session(self) -> str:
        self.memory.clear_session(self.session_id)
        self.session_id = uuid.uuid4().hex[:12]
        return self.session_id

    def clear_current_session(self) -> None:
        self.memory.clear_session(self.session_id)

    def recent_history_text(self, limit_turns: int = 10) -> str:
        items = self.memory.recent_messages(self.session_id, limit_turns=limit_turns)
        if not items:
            return "No conversation history yet."
        lines = []
        for item in items:
            label = "You" if item["role"] == "user" else "Grandpa"
            lines.append(f"{label}: {item['message']}")
        return "\n".join(lines)

    def memory_summary(self) -> str:
        memories = self.memory.list_memories(limit=50)
        if not memories:
            return "No saved memories yet."
        lines = ["Saved memories:"]
        for index, item in enumerate(memories, start=1):
            lines.append(f"{index}. {item['fact']}")
        return "\n".join(lines)

    def save_memory(self, fact: str) -> str:
        _ok, message = self.memory.save_fact(fact)
        return message

    def forget_memory(self, keyword: str) -> str:
        count = self.memory.forget(keyword)
        return f"Forgot {count} matching memorie(s)." if count else "No matching memory found."

    def reply(self, user_message: str) -> str:
        message = compact_text(user_message)
        self.memory.add_message(self.session_id, "user", message)
        intent = route_intent(message)
        if intent.handled:
            reply = intent.reply
            provider = "local-intent"
            model = intent.intent
            self.memory.add_message(self.session_id, "assistant", reply, provider=provider, model=model)
            self.logger.info("chat route=%s session_id=%s provider=%s model=%s", intent.intent, self.session_id, provider, model)
            return reply

        memories = self.memory.list_memories(limit=20)
        recent = self.memory.recent_messages(self.session_id, limit_turns=self.config.history_turns)
        prompt = build_system_prompt(message, memories=memories, recent_messages=recent)
        provider = self._provider()
        result: ProviderResult = provider.generate(prompt)
        if not result.ok:
            self.logger.error("provider_error provider=%s model=%s error=%s", result.provider, result.model, result.error)
            fallback = FallbackProvider()
            result = fallback.generate(prompt)
            if not result.text:
                result.text = FALLBACK_REPLY
        reply = compact_text(result.text) or FALLBACK_REPLY
        if reply.lower().strip(" ?!.") == message.lower().strip(" ?!."):
            reply = FALLBACK_REPLY
        self.memory.add_message(self.session_id, "assistant", reply, provider=result.provider, model=result.model)
        self.logger.info("chat route=provider session_id=%s provider=%s model=%s", self.session_id, result.provider, result.model)
        return reply
