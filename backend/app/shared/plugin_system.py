import importlib.util
import os
import sys
from types import ModuleType


PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "plugins",
)

_PLUGIN_CACHE = {}


def _validate_plugin(module: ModuleType, file_path: str) -> None:
    required = ("name", "description", "execute")
    missing = [attribute for attribute in required if not hasattr(module, attribute)]
    if missing:
        raise ValueError(f"Plugin {file_path} is missing required attributes: {', '.join(missing)}")
    if not callable(module.execute):
        raise ValueError(f"Plugin {file_path} has a non-callable execute attribute")


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

    plugins = {}
    for file_name in sorted(os.listdir(plugin_dir)):
        if not file_name.endswith(".py") or file_name.startswith("_"):
            continue
        file_path = os.path.join(plugin_dir, file_name)
        module = _load_plugin_from_file(file_path)
        plugins[module.name] = {
            "name": module.name,
            "description": module.description,
            "module": module,
            "path": file_path,
        }

    _PLUGIN_CACHE = plugins
    return plugins


def run_plugin(name: str, input_data, plugin_dir: str = PLUGIN_DIR):
    plugins = _PLUGIN_CACHE or load_plugins(plugin_dir=plugin_dir)
    plugin = plugins.get(name)
    if not plugin:
        raise KeyError(f"Plugin not found: {name}")
    return plugin["module"].execute(input_data)
