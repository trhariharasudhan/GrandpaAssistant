from __future__ import annotations

import os
from typing import Any

from .prompt_loader import list_available_prompts
from .prompt_modes import list_supported_modes
from .runtime_prompt_adapter import RUNTIME_PROMPT_ENV, TRUE_VALUES
from .prompt_runtime_observability import PromptRuntimeMetadata


EXPECTED_PROMPT_FILES = [
    "base/core.txt",
    "safety/automation_safety.txt",
    "tools/tool_rules.txt",
    "modes/default.txt",
    "modes/coding.txt",
    "modes/voice.txt",
    "modes/vision.txt",
    "modes/research.txt",
    "modes/planning.txt",
]


def _runtime_enabled() -> bool:
    return os.getenv(RUNTIME_PROMPT_ENV, "").strip().lower() in TRUE_VALUES


def _metadata_fields() -> list[str]:
    return list(PromptRuntimeMetadata.__annotations__.keys())


def get_prompt_runtime_status() -> dict[str, Any]:
    """Return safe internal prompt-runtime status without prompt bodies."""
    available = list_available_prompts()
    available_set = set(available)
    missing = [path for path in EXPECTED_PROMPT_FILES if path not in available_set]
    return {
        "runtime_enabled": _runtime_enabled(),
        "env_var": RUNTIME_PROMPT_ENV,
        "supported_modes": list_supported_modes(),
        "active_consumer": "chat_service",
        "available_prompt_files": available,
        "missing_expected_prompt_files": missing,
        "metadata_fields": _metadata_fields(),
        "reference_folder_used": False,
        "safe_to_expose": True,
    }
