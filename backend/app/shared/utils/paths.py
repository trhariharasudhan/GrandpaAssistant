from __future__ import annotations

import os


def _normalize_path(value: str) -> str:
    return os.path.abspath(os.path.expanduser(str(value or "")))


_CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
_SHARED_DIR = os.path.dirname(_CURRENT_DIR)
_APP_DIR = os.path.dirname(_SHARED_DIR)
_DEFAULT_BACKEND_DIR = os.path.dirname(_APP_DIR)
_DEFAULT_PROJECT_ROOT = os.path.dirname(_DEFAULT_BACKEND_DIR)
_DEFAULT_RUNTIME_DIR = os.path.join(_DEFAULT_PROJECT_ROOT, "runtime")

PROJECT_ROOT = _normalize_path(
    os.environ.get("GRANDPA_ASSISTANT_PROJECT_ROOT", _DEFAULT_PROJECT_ROOT)
)
BACKEND_DIR = _normalize_path(
    os.environ.get("GRANDPA_ASSISTANT_BACKEND_DIR", os.path.join(PROJECT_ROOT, "backend"))
)
RUNTIME_DIR = _normalize_path(
    os.environ.get("GRANDPA_ASSISTANT_RUNTIME_DIR", os.path.join(PROJECT_ROOT, "runtime"))
)
DATA_DIR = _normalize_path(
    os.environ.get("GRANDPA_ASSISTANT_DATA_DIR", os.path.join(RUNTIME_DIR, "data"))
)
LOGS_DIR = _normalize_path(
    os.environ.get("GRANDPA_ASSISTANT_LOGS_DIR", os.path.join(RUNTIME_DIR, "logs"))
)
MODELS_DIR = _normalize_path(
    os.environ.get("GRANDPA_ASSISTANT_MODELS_DIR", os.path.join(RUNTIME_DIR, "models"))
)
CONFIG_DIR = _normalize_path(
    os.environ.get("GRANDPA_ASSISTANT_CONFIG_DIR", os.path.join(RUNTIME_DIR, "config"))
)
CACHE_DIR = _normalize_path(
    os.environ.get("GRANDPA_ASSISTANT_CACHE_DIR", os.path.join(RUNTIME_DIR, "cache"))
)
ARTIFACTS_DIR = _normalize_path(os.path.join(RUNTIME_DIR, "artifacts"))


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _rooted_path(root: str, *parts: str) -> str:
    _ensure_dir(root)
    return os.path.join(root, *parts)


def project_root(*parts: str) -> str:
    return os.path.join(PROJECT_ROOT, *parts)


def runtime_root(*parts: str) -> str:
    return _rooted_path(RUNTIME_DIR, *parts)


def data_path(*parts: str) -> str:
    return _rooted_path(DATA_DIR, *parts)


def logs_path(*parts: str) -> str:
    return _rooted_path(LOGS_DIR, *parts)


def models_path(*parts: str) -> str:
    return _rooted_path(MODELS_DIR, *parts)


def cache_path(*parts: str) -> str:
    return _rooted_path(CACHE_DIR, *parts)


def config_path(*parts: str) -> str:
    return _rooted_path(CONFIG_DIR, *parts)


def artifacts_path(*parts: str) -> str:
    return _rooted_path(ARTIFACTS_DIR, *parts)


def project_path(*parts: str) -> str:
    return project_root(*parts)


def backend_path(*parts: str) -> str:
    return os.path.join(BACKEND_DIR, *parts)


def runtime_path(*parts: str) -> str:
    return runtime_root(*parts)


def backend_data_dir() -> str:
    return data_path()


def ensure_backend_data_dir() -> str:
    return data_path()


def backend_data_path(*parts: str) -> str:
    return data_path(*parts)


def docs_path(*parts: str) -> str:
    return project_root("docs", *parts)


def runtime_config_path(*parts: str) -> str:
    return config_path(*parts)


def runtime_cache_path(*parts: str) -> str:
    return cache_path(*parts)


def plugins_path(*parts: str) -> str:
    return project_root("plugins", *parts)
