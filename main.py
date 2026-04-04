import os
import runpy
import sys


BACKEND_MAIN = os.path.join(os.path.dirname(__file__), "backend", "main.py")
BACKEND_DIR = os.path.dirname(BACKEND_MAIN)
FASTAPI_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")

if FASTAPI_BACKEND_DIR not in sys.path:
    sys.path.insert(0, FASTAPI_BACKEND_DIR)

from fastapi_chat import app

if __name__ == "__main__":
    if BACKEND_DIR not in sys.path:
        sys.path.insert(0, BACKEND_DIR)
    sys.argv[0] = BACKEND_MAIN
    runpy.run_path(BACKEND_MAIN, run_name="__main__")
