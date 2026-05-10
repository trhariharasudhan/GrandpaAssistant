from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class UIElement:
    type: str
    label: str = ""
    bbox: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    confidence: float = 0.0
    source: str = "heuristic"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UIActionPlan:
    action: str
    target: str
    confidence: float
    requires_confirmation: bool = False
    blocked: bool = False
    reason: str = ""
    element: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()
