"""Command handler helpers used by the legacy command router."""

from .context import CommandContext
from .registry import CommandHandlerRegistry
from .result import CommandResult

__all__ = ["CommandContext", "CommandHandlerRegistry", "CommandResult"]
