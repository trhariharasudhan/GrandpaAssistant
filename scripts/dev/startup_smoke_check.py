import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PYTHON_EXE = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
MAIN_PATH = os.path.join(ROOT, "main.py")
HEALTH_URL = "http://127.0.0.1:8765/api/health"


def _print_result(name, ok, details=""):
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}")
    if details:
        print(f"  {details}")


def _health_ok():
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8", errors="ignore"))
        return bool(payload.get("ok"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return False


def _wait_for_health(timeout_seconds=25):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _health_ok():
            return True
        time.sleep(1)
    return False


def _resolve_python():
    if os.path.exists(PYTHON_EXE):
        return PYTHON_EXE
    return sys.executable


def _safe_remove(path, retries=5, delay_seconds=0.2):
    for _ in range(retries):
        try:
            if os.path.exists(path):
                os.remove(path)
            return
        except PermissionError:
            time.sleep(delay_seconds)
    # Best effort cleanup. It is okay to leave a temp log behind in rare lock races.


def run_startup_flow():
    checks = []
    details = {}

    pre_existing = _health_ok()
    checks.append(("No pre-existing API server", not pre_existing))
    if pre_existing:
        details["startup_log_excerpt"] = "API already running on 127.0.0.1:8765 before startup smoke."
        return False, checks, details

    python_exe = _resolve_python()
    temp_log = tempfile.NamedTemporaryFile(delete=False, suffix=".startup.log", mode="w", encoding="utf-8")
    temp_log_path = temp_log.name
    temp_log.close()

    process = None
    exited_cleanly = False
    forced_stop = False
    health_ready = False

    try:
        with open(temp_log_path, "w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                [python_exe, MAIN_PATH],
                cwd=ROOT,
                stdin=subprocess.PIPE,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )

            # Give process a brief moment to fail fast if there is a startup exception.
            time.sleep(2)
            running_after_boot = process.poll() is None
            checks.append(("Main process stays alive after launch", running_after_boot))

            if running_after_boot:
                health_ready = _wait_for_health(timeout_seconds=25)
            checks.append(("API health becomes ready", health_ready))

            if process.poll() is None:
                try:
                    # Move from mode prompt into text mode, then exit.
                    process.stdin.write("2\n")
                    process.stdin.flush()
                    time.sleep(0.8)
                    process.stdin.write("exit\n")
                    process.stdin.flush()
                except OSError:
                    pass

            try:
                process.wait(timeout=15)
                exited_cleanly = process.returncode == 0
            except subprocess.TimeoutExpired:
                forced_stop = True
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

        checks.append(("Graceful shutdown after smoke", exited_cleanly or forced_stop))

    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    try:
        with open(temp_log_path, "r", encoding="utf-8", errors="ignore") as log_file:
            full_log = log_file.read()
        excerpt = full_log[-1200:] if full_log else "No startup output captured."
    except OSError:
        excerpt = "Could not read startup log."
    finally:
        _safe_remove(temp_log_path)

    details["startup_log_excerpt"] = excerpt.replace("\n", " ")

    overall_ok = all(flag for _, flag in checks[:3])  # Core startup success signals.
    return overall_ok, checks, details


def main():
    overall_ok, checks, details = run_startup_flow()
    _print_result("Startup flow", overall_ok)
    for name, ok in checks:
        _print_result(name, ok)
    _print_result("Startup log excerpt", True, details.get("startup_log_excerpt", ""))

    print("\nSummary:")
    print(f"overall_ok={overall_ok}")
    if not overall_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
