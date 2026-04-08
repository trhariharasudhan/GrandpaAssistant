import importlib.util
import json
import os
import sys
from types import ModuleType

from utils.paths import backend_data_dir, backend_data_path, plugins_path

PLUGIN_DIR = plugins_path()
DATA_DIR = backend_data_dir()
PLUGIN_REGISTRY_PATH = backend_data_path("plugin_registry.json")

_PLUGIN_CACHE = {}
_PLUGIN_REGISTRY_CACHE = None


def _load_registry() -> dict:
    global _PLUGIN_REGISTRY_CACHE
    if _PLUGIN_REGISTRY_CACHE is not None:
        return dict(_PLUGIN_REGISTRY_CACHE)

    os.makedirs(DATA_DIR, exist_ok=True)
    default = {"disabled": []}
    if not os.path.exists(PLUGIN_REGISTRY_PATH):
        with open(PLUGIN_REGISTRY_PATH, "w", encoding="utf-8") as file:
            json.dump(default, file, indent=2)
        _PLUGIN_REGISTRY_CACHE = default
        return dict(default)

    try:
        with open(PLUGIN_REGISTRY_PATH, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:
        payload = default

    if not isinstance(payload, dict):
        payload = default
    disabled = payload.get("disabled", [])
    if not isinstance(disabled, list):
        disabled = []
    normalized = {"disabled": sorted({str(item).strip() for item in disabled if str(item).strip()})}
    _PLUGIN_REGISTRY_CACHE = normalized
    return dict(normalized)


def _save_registry(registry: dict) -> dict:
    global _PLUGIN_REGISTRY_CACHE
    os.makedirs(DATA_DIR, exist_ok=True)
    normalized = {
        "disabled": sorted({str(item).strip() for item in registry.get("disabled", []) if str(item).strip()}),
    }
    with open(PLUGIN_REGISTRY_PATH, "w", encoding="utf-8") as file:
        json.dump(normalized, file, indent=2)
    _PLUGIN_REGISTRY_CACHE = normalized
    return dict(normalized)


def _validate_plugin(module: ModuleType, file_path: str) -> None:
    required = ("name", "description", "execute")
    missing = [attribute for attribute in required if not hasattr(module, attribute)]
    if missing:
        raise ValueError(f"Plugin {file_path} is missing required attributes: {', '.join(missing)}")
    if not callable(module.execute):
        raise ValueError(f"Plugin {file_path} has a non-callable execute attribute")


def _plugin_metadata(module: ModuleType, file_path: str) -> dict:
    return {
        "name": str(getattr(module, "name", os.path.splitext(os.path.basename(file_path))[0])),
        "description": str(getattr(module, "description", "")).strip(),
        "version": str(getattr(module, "version", "1.0.0")).strip() or "1.0.0",
        "hooks": list(getattr(module, "hooks", []) or []),
        "config": getattr(module, "config", {}) if isinstance(getattr(module, "config", {}), dict) else {},
        "path": file_path,
    }


def _load_plugin_from_file(file_path: str) -> ModuleType:
    module_name = f"grandpa_plugin_{os.path.splitext(os.path.basename(file_path))[0]}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create import spec for {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    _validate_plugin(module, file_path)
    return module


def load_plugins(plugin_dir: str = PLUGIN_DIR) -> dict:
    global _PLUGIN_CACHE
    os.makedirs(plugin_dir, exist_ok=True)
    registry = _load_registry()
    disabled = {item.lower() for item in registry.get("disabled", [])}

    plugins = {}
    for file_name in sorted(os.listdir(plugin_dir)):
        if not file_name.endswith(".py") or file_name.startswith("_"):
            continue
        file_path = os.path.join(plugin_dir, file_name)
        module = _load_plugin_from_file(file_path)
        metadata = _plugin_metadata(module, file_path)
        plugins[metadata["name"]] = {
            "name": metadata["name"],
            "description": metadata["description"],
            "version": metadata["version"],
            "hooks": metadata["hooks"],
            "config": metadata["config"],
            "module": module,
            "path": file_path,
            "enabled": metadata["name"].lower() not in disabled,
        }

    _PLUGIN_CACHE = plugins
    return plugins


def run_plugin(name: str, input_data, plugin_dir: str = PLUGIN_DIR):
    plugins = _PLUGIN_CACHE or load_plugins(plugin_dir=plugin_dir)
    plugin = plugins.get(name)
    if not plugin:
        raise KeyError(f"Plugin not found: {name}")
    if not plugin.get("enabled", True):
        raise RuntimeError(f"Plugin is disabled: {name}")
    return plugin["module"].execute(input_data)


def list_plugins(plugin_dir: str = PLUGIN_DIR, include_disabled: bool = True) -> list[dict]:
    plugins = _PLUGIN_CACHE or load_plugins(plugin_dir=plugin_dir)
    items = []
    for plugin in sorted(plugins.values(), key=lambda item: item["name"].lower()):
        if not include_disabled and not plugin.get("enabled", True):
            continue
        items.append(
            {
                "name": plugin["name"],
                "description": plugin["description"],
                "version": plugin.get("version", "1.0.0"),
                "hooks": list(plugin.get("hooks", []) or []),
                "config": dict(plugin.get("config", {}) or {}),
                "path": plugin["path"],
                "enabled": bool(plugin.get("enabled", True)),
            }
        )
    return items


def reload_plugins(plugin_dir: str = PLUGIN_DIR) -> dict:
    global _PLUGIN_CACHE
    _PLUGIN_CACHE = {}
    return load_plugins(plugin_dir=plugin_dir)


def unload_plugin(name: str) -> bool:
    plugin = _PLUGIN_CACHE.pop(name, None)
    if not plugin:
        return False
    module_name = getattr(plugin.get("module"), "__name__", "")
    if module_name and module_name in sys.modules:
        sys.modules.pop(module_name, None)
    return True


def set_plugin_enabled(name: str, enabled: bool, plugin_dir: str = PLUGIN_DIR) -> tuple[bool, str]:
    plugins = _PLUGIN_CACHE or load_plugins(plugin_dir=plugin_dir)
    plugin = plugins.get(name)
    if not plugin:
        return False, f"Plugin not found: {name}"

    registry = _load_registry()
    disabled = {item.lower() for item in registry.get("disabled", [])}
    key = name.lower()
    if enabled:
        disabled.discard(key)
    else:
        disabled.add(key)
    _save_registry({"disabled": sorted(disabled)})
    reload_plugins(plugin_dir=plugin_dir)
    return True, f"Plugin {name} {'enabled' if enabled else 'disabled'}."


def plugin_status_payload(plugin_dir: str = PLUGIN_DIR) -> dict:
    plugins = list_plugins(plugin_dir=plugin_dir, include_disabled=True)
    return {
        "plugin_dir": plugin_dir,
        "total": len(plugins),
        "enabled": sum(1 for item in plugins if item.get("enabled")),
        "disabled": sum(1 for item in plugins if not item.get("enabled")),
        "plugins": plugins,
    }
