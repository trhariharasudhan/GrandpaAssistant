import datetime
import importlib
import importlib.util
import json
import os
import py_compile
import subprocess
import sys
import traceback
from dataclasses import dataclass
from typing import Any


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
BACKEND_DIR = os.path.join(ROOT, "backend")
APP_DIR = os.path.join(BACKEND_DIR, "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
DATA_DIR = os.path.join(ROOT, "runtime", "data")
LAST_STATUS_PATH = os.path.join(DATA_DIR, "last_backend_validation.json")

for path in [ROOT, BACKEND_DIR, APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

try:
    from utils.paths import backend_data_path

    LAST_STATUS_PATH = backend_data_path("last_backend_validation.json")
    DATA_DIR = os.path.dirname(LAST_STATUS_PATH)
except Exception:
    pass


@dataclass
class SectionResult:
    name: str
    ok: bool
    detail: str = ""
    warning: bool = False


def _now_text() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _print_section(result: SectionResult) -> None:
    tag = "PASS" if result.ok else "FAIL"
    if result.warning and result.ok:
        tag = "WARN"
    print(f"[{tag}] {result.name}")
    if result.detail:
        for line in str(result.detail).splitlines():
            print(f"  {line}")


def _run_subprocess(name: str, args: list[str], *, timeout_seconds: int) -> SectionResult:
    try:
        completed = subprocess.run(
            args,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        return SectionResult(name, False, f"Timed out after {timeout_seconds}s.\n{error.stdout or ''}".strip())
    except Exception as error:
        return SectionResult(name, False, str(error))

    output = (completed.stdout or "").strip()
    if completed.returncode == 0:
        detail = _last_lines(output, 8)
        return SectionResult(name, True, detail)
    return SectionResult(name, False, _last_lines(output, 40))


def _last_lines(text: str, count: int) -> str:
    lines = str(text or "").splitlines()
    return "\n".join(lines[-count:]) if lines else ""


def run_unittests() -> SectionResult:
    return _run_subprocess(
        "unittest discover",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        timeout_seconds=300,
    )


def run_startup_smoke() -> SectionResult:
    return _run_subprocess(
        "startup smoke check",
        [sys.executable, os.path.join("scripts", "dev", "startup_smoke_check.py")],
        timeout_seconds=120,
    )


def run_py_compile() -> SectionResult:
    files = []
    for root, _dirs, names in os.walk(BACKEND_DIR):
        for name in names:
            if name.endswith(".py"):
                files.append(os.path.join(root, name))

    failures = []
    for path in files:
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as error:
            failures.append(f"{os.path.relpath(path, ROOT)}: {error.msg}")
        except Exception as error:
            failures.append(f"{os.path.relpath(path, ROOT)}: {error}")

    if failures:
        return SectionResult("backend py_compile", False, "\n".join(failures[:20]))
    return SectionResult("backend py_compile", True, f"Compiled {len(files)} backend Python files.")


def run_import_checks() -> SectionResult:
    modules = [
        "backend.desktop_backend_entry",
        "backend.main",
        "backend.fastapi_chat",
        "app.api.web_api",
        "app.api.chat_api",
        "core.command_router",
        "startup_diagnostics",
        "llm_client",
        "offline_multi_model",
        "brain.memory_engine",
        "brain.semantic_memory",
        "voice.listen",
        "voice.speak",
        "vision.object_detection",
        "vision.screen_reader",
        "security.permission_engine",
        "security.auth_manager",
        "app_auth",
    ]
    failures = []
    imported = []
    for module_name in modules:
        try:
            importlib.import_module(module_name)
            imported.append(module_name)
        except Exception:
            failures.append(f"{module_name}: {traceback.format_exc(limit=1).strip()}")

    if failures:
        return SectionResult("core backend import check", False, "\n".join(failures))
    return SectionResult("core backend import check", True, f"Imported {len(imported)} core backend modules.")


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def run_optional_dependency_summary() -> SectionResult:
    try:
        import startup_diagnostics

        diagnostics = startup_diagnostics.collect_startup_diagnostics(use_cache=False, allow_create_dirs=False)
        warning_items = [
            item for item in diagnostics.get("items", [])
            if item.get("status") == "warning"
        ]
        error_items = [
            item for item in diagnostics.get("items", [])
            if item.get("status") == "error"
        ]
        hardware_keys = {"voice_input", "camera_vision", "tesseract", "python_modules", "piper_tts", "ollama_api", "ollama_models"}
        blocking_errors = [item for item in error_items if item.get("key") not in hardware_keys]
        nonblocking_errors = [item for item in error_items if item.get("key") in hardware_keys]
        lines = [diagnostics.get("summary", "No diagnostics summary.")]
        for item in warning_items[:12]:
            lines.append(f"WARN {item.get('title')}: {item.get('detail')}")
        for item in nonblocking_errors[:12]:
            lines.append(f"WARN {item.get('title')}: {item.get('detail')}")
        for item in blocking_errors[:12]:
            lines.append(f"FAIL {item.get('title')}: {item.get('detail')}")
        if blocking_errors:
            return SectionResult("optional dependency readiness summary", False, "\n".join(lines))
        return SectionResult(
            "optional dependency readiness summary",
            True,
            "\n".join(lines),
            warning=bool(warning_items or nonblocking_errors),
        )
    except Exception as error:
        return SectionResult("optional dependency readiness summary", False, str(error))


def _next_action(results: list[SectionResult]) -> str:
    failed = [item.name for item in results if not item.ok]
    if "unittest discover" in failed:
        return "Fix the failing regression test first; it is the clearest behavioral signal."
    if "startup smoke check" in failed:
        return "Inspect startup output, then verify the backend still launches through python backend\\desktop_backend_entry.py and main.py."
    if "backend py_compile" in failed or "core backend import check" in failed:
        return "Fix syntax/import errors before changing runtime behavior."
    if failed:
        return "Start with the first failed section above and rerun this script."
    warnings = [item.name for item in results if item.warning]
    if warnings:
        return "Release lock is clear, but review hardware/optional dependency warnings before testing device features."
    return "Release lock is clear. Safe next step: make the smallest feature change with a regression test."


def _write_last_status(results: list[SectionResult], next_action: str) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    payload: dict[str, Any] = {
        "checked_at": _now_text(),
        "overall_ok": all(item.ok for item in results),
        "failed_sections": [item.name for item in results if not item.ok],
        "warning_sections": [item.name for item in results if item.warning],
        "next_action": next_action,
        "sections": [
            {
                "name": item.name,
                "ok": item.ok,
                "warning": item.warning,
                "detail": item.detail,
            }
            for item in results
        ],
    }
    with open(LAST_STATUS_PATH, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def main() -> int:
    results = [
        run_unittests(),
        run_startup_smoke(),
        run_py_compile(),
        run_import_checks(),
        run_optional_dependency_summary(),
    ]
    next_action = _next_action(results)
    _write_last_status(results, next_action)

    print("GrandpaAssistant full backend validation")
    print(f"Checked at: {_now_text()}")
    print("")
    for result in results:
        _print_section(result)
    failed = [item.name for item in results if not item.ok]
    warnings = [item.name for item in results if item.warning]
    print("")
    print("Summary:")
    print(f"overall_ok={not failed}")
    print(f"failed_sections={failed}")
    print(f"warning_sections={warnings}")
    print(f"last_status_file={LAST_STATUS_PATH}")
    print(f"next_action={next_action}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
