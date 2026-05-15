from __future__ import annotations

import time
from collections.abc import Callable

from .base import LLMProvider


ProviderFactory = Callable[[], LLMProvider]


class LLMProviderRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, ProviderFactory] = {}
        self._health_cache: dict[str, tuple[float, dict]] = {}
        self.health_ttl_seconds = 30.0

    def register(self, name: str, factory: ProviderFactory) -> None:
        normalized = self.normalize_name(name)
        self._factories[normalized] = factory

    def names(self) -> list[str]:
        return sorted(self._factories)

    def get(self, name: str) -> LLMProvider:
        normalized = self.normalize_name(name)
        if normalized not in self._factories:
            raise KeyError(f"Unknown LLM provider: {name}")
        return self._factories[normalized]()

    def health_check(self, name: str, *, force: bool = False) -> dict:
        normalized = self.normalize_name(name)
        now = time.time()
        cached = self._health_cache.get(normalized)
        if cached and not force and now - cached[0] < self.health_ttl_seconds:
            return dict(cached[1])
        try:
            health = self.get(normalized).health_check()
        except Exception as error:
            health = {"ok": False, "provider": normalized, "error": str(error)}
        self._health_cache[normalized] = (now, dict(health))
        return health

    @staticmethod
    def normalize_name(name: str | None) -> str:
        return str(name or "").strip().lower()
