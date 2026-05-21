from __future__ import annotations

from dataclasses import dataclass, field

try:
    from utils.paths import runtime_path
except Exception:  # pragma: no cover
    runtime_path = None


SUPPORTED_BROWSERS = {"chrome", "edge", "firefox", "chromium"}
DEFAULT_BROWSER = "chrome"
DANGEROUS_ACTION_KEYWORDS = {
    "buy",
    "purchase",
    "pay",
    "checkout",
    "order",
    "book",
    "submit",
    "send",
    "post",
    "delete",
    "cancel subscription",
    "apply",
}
SENSITIVE_FIELD_HINTS = {"password", "otp", "pin", "cvv", "card", "ssn", "secret", "token", "api_key"}


def browser_runtime_dir() -> str:
    if runtime_path is not None:
        return runtime_path("browser_automation")
    return "runtime/browser_automation"


@dataclass
class BrowserAutomationConfig:
    default_browser: str = DEFAULT_BROWSER
    headless: bool = False
    human_delay_ms: int = 350
    navigation_timeout_ms: int = 30000
    retry_attempts: int = 2
    screenshot_debugging: bool = True
    safe_mode: bool = True
    downloads_enabled: bool = True
    allowed_browsers: set[str] = field(default_factory=lambda: set(SUPPORTED_BROWSERS))
