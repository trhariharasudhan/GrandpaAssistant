from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CommandResult:
    handled: bool
    reply: str = ""
    route: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def not_handled(cls) -> "CommandResult":
        return cls(handled=False)
