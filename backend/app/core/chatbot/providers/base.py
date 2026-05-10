from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ProviderResult:
    ok: bool
    text: str
    provider: str
    model: str
    error: str = ""


class ChatProvider(Protocol):
    name: str
    model: str

    def generate(self, prompt: str) -> ProviderResult:
        ...
