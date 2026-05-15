from .base import PromptBuildRequest
from .builder import build_prompt, build_terminal_prompt
from .language_style import detect_language_style, language_instruction
from .route_adapters import build_chat_api_prompt, build_streaming_chat_prompt, build_web_api_chat_prompt

try:
    from ..runtime_prompt_adapter import get_runtime_system_prompt
except ImportError:  # pragma: no cover - package import shape can differ in scripts
    get_runtime_system_prompt = None

__all__ = [
    "PromptBuildRequest",
    "build_chat_api_prompt",
    "build_prompt",
    "build_streaming_chat_prompt",
    "build_terminal_prompt",
    "build_web_api_chat_prompt",
    "detect_language_style",
    "get_runtime_system_prompt",
    "language_instruction",
]
