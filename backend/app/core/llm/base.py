from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol


@dataclass
class LLMRequest:
    prompt: str
    history: list[dict] = field(default_factory=list)
    system_prompt: str | None = None
    model: str | None = None
    temperature: float = 0.7
    metadata: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    ok: bool
    text: str
    provider: str
    model: str
    error: str = ""
    metadata: dict = field(default_factory=dict)


class LLMProvider(Protocol):
    name: str
    model: str

    def generate(self, request: LLMRequest) -> LLMResponse:
        ...

    def stream_generate(self, request: LLMRequest) -> Iterable[str]:
        ...

    def health_check(self) -> dict:
        ...

    def model_info(self) -> dict:
        ...
