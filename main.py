import os
import runpy
import subprocess
import sys
import traceback


ROOT_DIR = os.path.dirname(__file__)
BACKEND_MAIN = os.path.join(os.path.dirname(__file__), "backend", "main.py")
BACKEND_DIR = os.path.dirname(BACKEND_MAIN)
FASTAPI_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "backend")
LOG_DIR = os.path.join(FASTAPI_BACKEND_DIR, "logs")
STARTUP_ERROR_LOG = os.path.join(LOG_DIR, "main_startup_error.log")
_APP = None


def _enable_line_buffering():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(line_buffering=True)
            except Exception:
                pass


def _log_startup_exception(error):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(STARTUP_ERROR_LOG, "a", encoding="utf-8") as file:
            file.write("\n===== Grandpa Assistant startup error =====\n")
            traceback.print_exception(type(error), error, error.__traceback__, file=file)
    except Exception:
        pass


def _normalize_path(path):
    return os.path.normcase(os.path.abspath(path))


def _project_python_candidates():
    return [
        os.path.join(ROOT_DIR, ".python311", "python.exe"),
        os.path.join(ROOT_DIR, ".venv", "Scripts", "python.exe"),
    ]


def _should_relaunch_with_project_python():
    if os.environ.get("GRANDPA_ASSISTANT_BOOTSTRAPPED") == "1":
        return None

    current_executable = _normalize_path(sys.executable)
    for candidate in _project_python_candidates():
        if not os.path.exists(candidate):
            continue
        if _normalize_path(candidate) == current_executable:
            return None
        return candidate
    return None


def _maybe_relaunch_with_project_python():
    preferred_python = _should_relaunch_with_project_python()
    if not preferred_python:
        return

    env = os.environ.copy()
    env["GRANDPA_ASSISTANT_BOOTSTRAPPED"] = "1"
    command = [preferred_python, os.path.abspath(__file__), *sys.argv[1:]]
    try:
        exit_code = subprocess.call(command, cwd=ROOT_DIR, env=env)
    except KeyboardInterrupt:
        raise SystemExit(0)
    raise SystemExit(exit_code)


def _load_fastapi_app():
    global _APP
    if _APP is None:
        if FASTAPI_BACKEND_DIR not in sys.path:
            sys.path.insert(0, FASTAPI_BACKEND_DIR)
        from fastapi_chat import app as fastapi_app

        _APP = fastapi_app
    return _APP

if FASTAPI_BACKEND_DIR not in sys.path:
    sys.path.insert(0, FASTAPI_BACKEND_DIR)

app = _load_fastapi_app() if __name__ != "__main__" else None

if __name__ == "__main__":
    _enable_line_buffering()
    _maybe_relaunch_with_project_python()
    if BACKEND_DIR not in sys.path:
        sys.path.insert(0, BACKEND_DIR)
    sys.argv[0] = BACKEND_MAIN
    try:
        runpy.run_path(BACKEND_MAIN, run_name="__main__")
    except BaseException as error:
        _log_startup_exception(error)
        print("Grandpa Assistant failed to start.", file=sys.stderr)
        print(f"See log: {STARTUP_ERROR_LOG}", file=sys.stderr)
        raise
