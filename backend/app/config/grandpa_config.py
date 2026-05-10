from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_dotenv(path: str | Path | None = None) -> None:
    env_path = Path(path) if path else project_root() / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#") or "=" not in entry:
            continue
        key, value = entry.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_root() / path


@dataclass
class GrandpaConfig:
    provider: str = "fallback"
    model: str = "rules"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    openai_base_url: str = "https://api.openai.com/v1"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    db_path: str = "runtime/data/grandpa_chat.db"
    log_level: str = "INFO"
    log_path: str = "runtime/logs/grandpa.log"
    history_turns: int = 10
    timeout_seconds: float = 30.0
    config_path: str = ""

    def safe_summary(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "ollama_base_url": self.ollama_base_url,
            "db_path": self.db_path,
            "log_level": self.log_level,
            "log_path": self.log_path,
            "history_turns": self.history_turns,
            "openai_api_key": "set" if self.openai_api_key else "missing",
            "gemini_api_key": "set" if self.gemini_api_key else "missing",
        }


def _json_config_path() -> Path:
    return project_root() / "backend" / "app" / "config" / "terminal_chat.json"


def _load_json_defaults() -> dict[str, Any]:
    path = _json_config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_config() -> GrandpaConfig:
    load_dotenv()
    defaults = _load_json_defaults()
    providers = defaults.get("providers") or {}
    selected_provider = os.getenv("AI_PROVIDER") or defaults.get("provider") or "fallback"
    provider_defaults = providers.get(str(selected_provider).lower(), {})
    ollama_defaults = providers.get("ollama") or {}
    model = os.getenv("AI_MODEL") or provider_defaults.get("model") or defaults.get("model") or "rules"
    return GrandpaConfig(
        provider=str(selected_provider).strip().lower() or "fallback",
        model=str(model),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        gemini_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", ""),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL") or ollama_defaults.get("base_url") or "http://localhost:11434",
        openai_base_url=os.getenv("OPENAI_BASE_URL") or (providers.get("openai") or {}).get("base_url") or "https://api.openai.com/v1",
        gemini_base_url=os.getenv("GEMINI_BASE_URL") or (providers.get("gemini") or {}).get("base_url") or "https://generativelanguage.googleapis.com/v1beta",
        db_path=os.getenv("GRANDPA_DB_PATH") or defaults.get("database_path") or "runtime/data/grandpa_chat.db",
        log_level=os.getenv("GRANDPA_LOG_LEVEL") or "INFO",
        log_path=os.getenv("GRANDPA_LOG_PATH") or "runtime/logs/grandpa.log",
        history_turns=int(defaults.get("history_turns") or 10),
        timeout_seconds=float(provider_defaults.get("timeout_seconds") or 30),
        config_path=str(_json_config_path()),
    )
