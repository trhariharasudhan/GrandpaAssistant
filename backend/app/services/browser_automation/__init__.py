"""
Browser automation service package.

Heavy Playwright-backed modules are imported lazily so API import remains safe
when Playwright is not installed. Real browser execution still requires the
`playwright` package and installed browser runtimes.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS = {
    "BrowserActionPlanner": ".action_planner",
    "BrowserMemory": ".memory",
    "BrowserSafetyLayer": ".safety_layer",
    "BrowserOperations": ".operations",
    "BrowserExecutor": ".executor",
    "BrowserSessionManager": ".session_manager",
    "BrowserAutomationService": ".service",
    "get_browser_automation_service": ".service",
    "sse_events": ".service",
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(name)
    module = import_module(_EXPORTS[name], __name__)
    return getattr(module, name)


__all__ = sorted(_EXPORTS)
