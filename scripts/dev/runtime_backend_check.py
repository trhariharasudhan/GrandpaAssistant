from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PORTS_TO_CHECK = [8765, 8000]
ENDPOINTS_TO_CHECK = [
    "/api/health",
    "/api/backend/stability",
    "/api/debug/dashboard",
    "/api/debug/docs-summary",
]
STARTUP_TIMEOUT_SECONDS = 45
PREVIEW_LIMIT = 420


def find_project_root(start: str | os.PathLike[str] | None = None) -> Path:
    current = Path(start or __file__).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / "backend" / "desktop_backend_entry.py").exists() and (candidate / "scripts").exists():
            return candidate
    return Path(__file__).resolve().parents[2]


def resolve_python_exe(root: str | os.PathLike[str] | None = None) -> str:
    project_root = Path(root) if root else find_project_root()
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def backend_entry_path(root: str | os.PathLike[str] | None = None) -> str:
    project_root = Path(root) if root else find_project_root()
    return str(project_root / "backend" / "desktop_backend_entry.py")


def response_preview(value: Any, limit: int = PREVIEW_LIMIT) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=True, sort_keys=True)
    else:
        text = str(value or "")
    text = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    if len(text) > limit:
        return text[: max(0, limit - 15)] + "...[truncated]"
    return text


def endpoint_response_preview(endpoint: str, body: Any, error: str = "") -> str:
    if error and not body:
        return response_preview(error)
    if endpoint == "/api/health" and isinstance(body, str):
        service_match = re.search(r'"service"\s*:\s*"([^"]+)"', body)
        ok_match = re.search(r'"ok"\s*:\s*(true|false)', body, flags=re.IGNORECASE)
        if service_match or ok_match:
            return response_preview({
                "ok": ok_match.group(1).lower() == "true" if ok_match else None,
                "service": service_match.group(1) if service_match else None,
            })
    if not isinstance(body, dict):
        return response_preview(body or error)
    if endpoint == "/api/health":
        return response_preview({key: body.get(key) for key in ("ok", "service") if key in body})
    if endpoint == "/api/backend/stability":
        checks = body.get("checks") or []
        warnings = body.get("warnings") or []
        return response_preview({
            "overall_ok": body.get("overall_ok", body.get("ok")),
            "checks_count": len(checks) if isinstance(checks, list) else 0,
            "warnings_count": len(warnings) if isinstance(warnings, list) else 0,
        })
    if endpoint == "/api/debug/dashboard":
        return response_preview({
            "overall_ok": body.get("overall_ok"),
            "pending_approvals_count": body.get("pending_approvals_count"),
            "recent_audit_count": body.get("recent_audit_count"),
            "timeline_count": body.get("timeline_count"),
            "warnings_count": len(body.get("warnings") or []),
            "no_destructive_action": body.get("no_destructive_action"),
        })
    if endpoint == "/api/debug/docs-summary":
        return response_preview({key: body.get(key) for key in ("ok", "guide", "generator") if key in body})
    compact = {}
    for key, value in body.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            compact[key] = value
        elif isinstance(value, list):
            compact[key] = f"{len(value)} item(s)"
        elif isinstance(value, dict):
            compact[key] = f"{len(value)} field(s)"
    return response_preview(compact or body)


def _read_log_preview(path: str, limit: int = 1600) -> str:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return "Could not read process output."
    return response_preview(text[-limit:] if text else "No output captured.", limit=limit)


def _request_json(url: str, timeout: float = 5.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            status = int(getattr(response, "status", response.getcode()))
            raw = response.read(4096).decode("utf-8", errors="ignore")
        try:
            body: Any = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = raw
        return {"ok": 200 <= status < 300, "status": status, "body": body, "error": ""}
    except urllib.error.HTTPError as error:
        raw = error.read(4096).decode("utf-8", errors="ignore") if hasattr(error, "read") else ""
        return {"ok": False, "status": int(error.code), "body": raw, "error": str(error)}
    except Exception as error:
        return {"ok": False, "status": None, "body": "", "error": str(error)}


def check_endpoint(port: int, endpoint: str) -> dict[str, Any]:
    url = f"http://127.0.0.1:{port}{endpoint}"
    result = _request_json(url)
    required_ok = bool(result["ok"])
    if endpoint == "/api/health" and isinstance(result.get("body"), dict):
        required_ok = required_ok and bool(result["body"].get("ok"))
    return {
        "endpoint": endpoint,
        "url": url,
        "ok": required_ok,
        "status": result.get("status"),
        "preview": endpoint_response_preview(endpoint, result.get("body"), result.get("error", "")),
        "error": result.get("error", ""),
    }


def check_port(port: int) -> dict[str, Any]:
    endpoint_results = [check_endpoint(port, endpoint) for endpoint in ENDPOINTS_TO_CHECK]
    return {
        "port": port,
        "ok": all(item["ok"] for item in endpoint_results),
        "endpoints": endpoint_results,
    }


def _any_port_ready() -> dict[str, Any] | None:
    for port in PORTS_TO_CHECK:
        result = check_port(port)
        if result["ok"]:
            return result
    return None


def wait_for_backend(process: subprocess.Popen, timeout_seconds: int = STARTUP_TIMEOUT_SECONDS) -> dict[str, Any] | None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            return None
        ready = _any_port_ready()
        if ready:
            return ready
        time.sleep(1)
    return None


def start_backend(root: str | os.PathLike[str] | None = None):
    project_root = find_project_root(root)
    python_exe = resolve_python_exe(project_root)
    entry = backend_entry_path(project_root)
    stdout_file = tempfile.NamedTemporaryFile(delete=False, suffix=".runtime-backend.stdout.log", mode="w", encoding="utf-8")
    stderr_file = tempfile.NamedTemporaryFile(delete=False, suffix=".runtime-backend.stderr.log", mode="w", encoding="utf-8")
    stdout_file.close()
    stderr_file.close()
    stdout_handle = open(stdout_file.name, "w", encoding="utf-8")
    stderr_handle = open(stderr_file.name, "w", encoding="utf-8")
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
    process = subprocess.Popen(
        [python_exe, entry],
        cwd=str(project_root),
        stdout=stdout_handle,
        stderr=stderr_handle,
        stdin=subprocess.DEVNULL,
        text=True,
        creationflags=creationflags,
    )
    return {
        "process": process,
        "python": python_exe,
        "entry": entry,
        "stdout_path": stdout_file.name,
        "stderr_path": stderr_file.name,
        "stdout_handle": stdout_handle,
        "stderr_handle": stderr_handle,
    }


def stop_backend(process: subprocess.Popen, timeout_seconds: int = 8) -> str:
    if process.poll() is not None:
        return f"already exited with code {process.returncode}"
    process.terminate()
    try:
        process.wait(timeout=timeout_seconds)
        return f"terminated with code {process.returncode}"
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=timeout_seconds)
        return f"killed with code {process.returncode}"


def _cleanup_logs(paths: list[str]) -> None:
    for path in paths:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass


def run_runtime_check() -> dict[str, Any]:
    root = find_project_root()
    launch = start_backend(root)
    process = launch["process"]
    detected = None
    stopped = ""
    try:
        time.sleep(1)
        started = process.poll() is None
        detected = wait_for_backend(process) if started else None
        port_results = [detected] if detected else [check_port(port) for port in PORTS_TO_CHECK]
        overall_ok = bool(started and detected and detected.get("ok"))
        return {
            "overall_ok": overall_ok,
            "backend_process_started": started,
            "detected_port": detected.get("port") if detected else None,
            "port_results": port_results,
            "python": launch["python"],
            "entry": launch["entry"],
            "process_returncode": process.poll(),
            "stdout_preview": _read_log_preview(launch["stdout_path"]),
            "stderr_preview": _read_log_preview(launch["stderr_path"]),
            "stop_result": "",
        }
    finally:
        stopped = stop_backend(process)
        for key in ("stdout_handle", "stderr_handle"):
            try:
                launch[key].close()
            except Exception:
                pass
        # Preserve previews until after the report is built; caller receives text above.
        if detected is not None or process.poll() is not None:
            pass
        launch["stop_result"] = stopped
        _cleanup_logs([launch["stdout_path"], launch["stderr_path"]])


def print_report(result: dict[str, Any]) -> None:
    print("GrandpaAssistant runtime backend check")
    print(f"Project entry: {result.get('entry')}")
    print(f"Python: {result.get('python')}")
    print()
    print(f"backend process started: {'YES' if result.get('backend_process_started') else 'NO'}")
    print(f"detected port: {result.get('detected_port') or 'NONE'}")
    print()
    print("Endpoint checks:")
    for port_result in result.get("port_results") or []:
        if not port_result:
            continue
        print(f"  Port {port_result.get('port')}: {'PASS' if port_result.get('ok') else 'FAIL'}")
        for item in port_result.get("endpoints") or []:
            status = item.get("status") if item.get("status") is not None else "NO RESPONSE"
            print(f"    [{'PASS' if item.get('ok') else 'FAIL'}] {item.get('endpoint')} status={status}")
            print(f"      {item.get('preview') or item.get('error') or 'No response preview.'}")
    if not result.get("overall_ok"):
        print()
        print("Backend stdout preview:")
        print(result.get("stdout_preview") or "No stdout captured.")
        print()
        print("Backend stderr preview:")
        print(result.get("stderr_preview") or "No stderr captured.")
    print()
    print(f"overall: {'PASS' if result.get('overall_ok') else 'FAIL'}")


def main() -> int:
    result = run_runtime_check()
    print_report(result)
    return 0 if result.get("overall_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
