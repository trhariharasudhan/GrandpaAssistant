from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


TRUE_VALUES = {"1", "true", "yes", "on"}
VOICE_RUNTIME_ENV = "GRANDPA_VOICE_RUNTIME_ENABLED"
TESSERACT_PATH_ENV = "TESSERACT_PATH"
DEFAULT_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
PLAYWRIGHT_BROWSER_INSTALL_HINT = "python -m playwright install chromium"


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, AttributeError, ValueError):
        return False


def _truthy_env(name: str) -> bool:
    return str(os.getenv(name) or "").strip().lower() in TRUE_VALUES


def _compact(value: Any, limit: int = 240) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _status(ready: bool, warnings: list[str]) -> str:
    if ready and not warnings:
        return "ok"
    return "warning"


def _playwright_version() -> str:
    if not _module_available("playwright"):
        return ""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "--version"],
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except Exception:
        return ""
    if result.returncode != 0:
        return ""
    return _compact(result.stdout or result.stderr, 80)


def _playwright_executable_paths() -> dict[str, str]:
    if not _module_available("playwright"):
        return {}
    try:
        from playwright.sync_api import sync_playwright

        manager = sync_playwright().start()
        try:
            return {
                "chromium": str(manager.chromium.executable_path),
                "firefox": str(manager.firefox.executable_path),
                "webkit": str(manager.webkit.executable_path),
            }
        finally:
            manager.stop()
    except Exception:
        return {}


def _voice_readiness() -> dict[str, Any]:
    speech_recognition = _module_available("speech_recognition")
    pyttsx3 = _module_available("pyttsx3")
    runtime_enabled = _truthy_env(VOICE_RUNTIME_ENV)
    warnings: list[str] = []
    setup_hints: list[str] = []
    if not speech_recognition:
        warnings.append("speech_recognition_missing")
        setup_hints.append("Install SpeechRecognition to enable speech-to-text readiness checks.")
    if not pyttsx3:
        warnings.append("pyttsx3_missing")
        setup_hints.append("Install pyttsx3 to enable local Windows TTS.")
    if not runtime_enabled:
        warnings.append("voice_runtime_disabled")
        setup_hints.append(f"Set {VOICE_RUNTIME_ENV}=1 only when background voice mode is needed.")
    return {
        "status": _status(speech_recognition and pyttsx3 and runtime_enabled, warnings),
        "ready": speech_recognition and pyttsx3 and runtime_enabled,
        "speech_recognition_installed": speech_recognition,
        "pyttsx3_installed": pyttsx3,
        "voice_runtime_enabled": runtime_enabled,
        "voice_runtime_env_var": VOICE_RUNTIME_ENV,
        "warnings": warnings,
        "setup_hints": setup_hints,
    }


def _tesseract_candidates() -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    configured = os.getenv(TESSERACT_PATH_ENV, "").strip()
    if configured:
        candidates.append({"source": "configured_path", "path": configured})
    candidates.append({"source": "common_windows_path", "path": DEFAULT_TESSERACT_PATH})
    path_match = shutil.which("tesseract")
    if path_match:
        candidates.append({"source": "path", "path": path_match})
    return candidates


def _ocr_readiness() -> dict[str, Any]:
    pytesseract = _module_available("pytesseract")
    candidates = _tesseract_candidates()
    detected = next((item for item in candidates if item["path"] and Path(item["path"]).exists()), None)
    warnings: list[str] = []
    setup_hints: list[str] = []
    if not pytesseract:
        warnings.append("pytesseract_missing")
        setup_hints.append("Install the Python OCR adapter with: pip install pytesseract")
    if not detected:
        warnings.append("tesseract_executable_missing")
        setup_hints.append("Install Tesseract OCR and set TESSERACT_PATH or add tesseract.exe to PATH.")
    return {
        "status": _status(pytesseract and detected is not None, warnings),
        "ready": pytesseract and detected is not None,
        "pytesseract_installed": pytesseract,
        "tesseract_executable_detected": detected is not None,
        "tesseract_path": detected["path"] if detected else "",
        "tesseract_path_source": detected["source"] if detected else "",
        "tesseract_candidates_checked": candidates,
        "warnings": warnings,
        "setup_hints": setup_hints,
        "ocr_action_performed": False,
    }


def _browser_readiness() -> dict[str, Any]:
    package_installed = _module_available("playwright")
    version = _playwright_version()
    executable_paths = _playwright_executable_paths()
    runtimes = {}
    for name in ("chromium", "firefox", "webkit"):
        path = executable_paths.get(name, "")
        runtimes[name] = {
            "installed": bool(path and Path(path).exists()),
            "executable_path": path,
        }
    missing = [name for name, item in runtimes.items() if not item["installed"]]
    warnings: list[str] = []
    setup_hints: list[str] = []
    if not package_installed:
        warnings.append("playwright_package_missing")
        setup_hints.append("Install Playwright with: pip install playwright")
    if package_installed and missing:
        warnings.append("playwright_browser_runtime_missing")
        setup_hints.append(f"Install a browser runtime with: {PLAYWRIGHT_BROWSER_INSTALL_HINT}")
    return {
        "status": _status(package_installed and not missing, warnings),
        "ready": package_installed and not missing,
        "playwright_package_installed": package_installed,
        "playwright_version": version,
        "browser_runtimes": runtimes,
        "missing_browser_runtimes": missing,
        "warnings": warnings,
        "setup_hints": setup_hints,
        "browser_launched": False,
    }


def collect_daily_use_readiness() -> dict[str, Any]:
    """Return safe daily-use readiness without using hardware, OCR, or browser pages."""

    voice = _voice_readiness()
    ocr = _ocr_readiness()
    browser = _browser_readiness()
    sections = {
        "voice": voice,
        "ocr": ocr,
        "browser": browser,
    }
    warnings = [
        f"{section}_{warning}"
        for section, payload in sections.items()
        for warning in payload.get("warnings", [])
    ]
    ready_count = sum(1 for payload in sections.values() if payload.get("ready"))
    return {
        "ok": True,
        "status": "ok" if not warnings else "warning",
        "safe_to_expose": True,
        "read_only": True,
        "warnings_count": len(warnings),
        "ready_count": ready_count,
        "section_count": len(sections),
        "warnings": warnings,
        "voice": voice,
        "ocr": ocr,
        "browser": browser,
        "actions_performed": {
            "browser_launched": False,
            "microphone_accessed": False,
            "camera_accessed": False,
            "ocr_ran": False,
        },
    }
