import importlib as _importlib
import sys as _sys

_module = _importlib.import_module("system.windows_voice_control_module")
_sys.modules[__name__] = _module
