import os
import sys

import uvicorn


BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
APP_DIR = os.path.join(BACKEND_DIR, "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")

for path in [BACKEND_DIR, APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

from app.api import web_api  # noqa: E402


def _env_port() -> int:
    try:
        return int(str(os.environ.get("GRANDPA_ASSISTANT_PORT", "8765")).strip())
    except Exception:
        return 8765


def _env_host() -> str:
    return str(os.environ.get("GRANDPA_ASSISTANT_HOST", "127.0.0.1")).strip() or "127.0.0.1"


def _env_log_level() -> str:
    value = str(os.environ.get("GRANDPA_ASSISTANT_LOG_LEVEL", "warning")).strip().lower()
    return value if value in {"critical", "error", "warning", "info", "debug"} else "warning"


def main() -> None:
    web_api._initialize_web_runtime()
    uvicorn.run(web_api.app, host=_env_host(), port=_env_port(), log_level=_env_log_level())


if __name__ == "__main__":
    main()
