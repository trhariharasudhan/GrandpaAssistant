"""Backend application package root.

This package still supports a legacy flat-import style such as
`from agents.runtime import ...` and `from modules.task_module import ...`.
Bootstrapping those paths here keeps direct package imports working without
requiring every entry point to mutate `sys.path` first.
"""

import os
import sys


APP_DIR = os.path.abspath(os.path.dirname(__file__))
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")

for path in (APP_DIR, SHARED_DIR, FEATURES_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)
