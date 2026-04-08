from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from typing import Protocol


def compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


@dataclass
class ModuleRequest:
    command: str
    input_mode: str = "text"
    source: str = "command"
    installed_apps: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def normalized_command(self) -> str:
        return compact_text(self.command).lower()


@dataclass
class ModuleResult:
    handled: bool
    ok: bool = True
    module: str = ""
    intent: str = ""
    messages: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class CommandModule(Protocol):
    name: str

    def can_handle(self, request: ModuleRequest) -> bool:
        ...

    def handle(self, request: ModuleRequest) -> ModuleResult:
        ...
