"""
Configuration for browser automation service.
"""

from enum import Enum
from typing import Optional


class BrowserAutomationConfig:
    """Configuration for browser automation."""

    # Session management
    MAX_CONCURRENT_SESSIONS = 5
    SESSION_TIMEOUT_MINUTES = 30
    SESSION_DATA_DIR = "browser_sessions"

    # Executor settings
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 1.0
    PAGE_LOAD_TIMEOUT_MS = 30000
    ACTION_TIMEOUT_MS = 10000

    # Navigation
    HUMAN_DELAY_MIN_MS = 200
    HUMAN_DELAY_MAX_MS = 1000
    PAGE_LOAD_WAIT = "networkidle"

    # Browser
    BROWSER_HEADLESS = False
    BROWSER_DISABLE_GPU = True
    BROWSER_NO_SANDBOX = True
    WINDOW_WIDTH = 1920
    WINDOW_HEIGHT = 1080
    DEFAULT_LOCALE = "en-US"
    DEFAULT_TIMEZONE = "America/New_York"

    # Memory
    MEMORY_DATA_DIR = "browser_memory"
    MAX_SNAPSHOTS_PER_SESSION = 50
    MAX_HISTORY_PER_SESSION = 200

    # Safety
    REQUIRE_CONFIRMATIONS = True
    SAFE_MODE_ENABLED = True

    # AI Planning
    OLLAMA_MODEL = "neural-chat"
    PLAN_CACHE_SIZE = 100

    # Logging
    LOG_SCREENSHOTS_ON_ERROR = True
    SCREENSHOT_DIR = "browser_screenshots"
