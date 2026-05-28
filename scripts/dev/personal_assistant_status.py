from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
for path in (ROOT, APP_DIR, SHARED_DIR):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


TRUE_VALUES = {"1", "true", "yes", "on"}
DEBUG_ENV = "GRANDPA_ASSISTANT_DEBUG"
LLM_PLANNER_ENV = "GRANDPA_ASSISTANT_ENABLE_LLM_PLANNER"
LLM_PLANNER_PROVIDER_ENV = "GRANDPA_ASSISTANT_PLANNER_PROVIDER"
PERSONAL_ASSISTANT_PACKAGE = APP_DIR / "core" / "personal_assistant"
REMINDER_SCHEDULER_ENV = "GRANDPA_REMINDER_SCHEDULER_ENABLED"
REMINDER_INTERVAL_ENV = "GRANDPA_REMINDER_CHECK_INTERVAL_SECONDS"


def _truthy_env(name: str) -> bool:
    return str(os.getenv(name) or "").strip().lower() in TRUE_VALUES


def _safe_error(error: BaseException) -> str:
    return str(error).strip().replace("\n", " ")[:240]


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _ensure_personal_assistant_package() -> None:
    """Allow safe leaf-module imports without executing personal_assistant.__init__."""

    package_name = "core.personal_assistant"
    existing = sys.modules.get(package_name)
    if existing is not None and getattr(existing, "__path__", None):
        return
    module = types.ModuleType(package_name)
    module.__file__ = str(PERSONAL_ASSISTANT_PACKAGE / "__init__.py")
    module.__path__ = [str(PERSONAL_ASSISTANT_PACKAGE)]  # type: ignore[attr-defined]
    module.__package__ = package_name
    sys.modules[package_name] = module


def _status_error(error: BaseException) -> dict[str, Any]:
    return {"ok": False, "available": False, "error": _safe_error(error)}


def _tool_status(verbose_safe: bool = False) -> dict[str, Any]:
    try:
        _ensure_personal_assistant_package()
        from core.personal_assistant.tool_registry import list_available_tools

        tools = list_available_tools()
        names = sorted(str(tool.get("tool_name") or "") for tool in tools if tool.get("tool_name"))
        status: dict[str, Any] = {
            "ok": bool(names),
            "tool_count": len(names),
            "tool_names": names,
        }
        if verbose_safe:
            risk_counts: dict[str, int] = {}
            unavailable: list[str] = []
            for tool in tools:
                risk = str(tool.get("risk_level") or "unknown")
                risk_counts[risk] = risk_counts.get(risk, 0) + 1
                if not tool.get("available"):
                    unavailable.append(str(tool.get("tool_name") or "unknown"))
            status["risk_counts"] = risk_counts
            status["unavailable_tools"] = sorted(unavailable)
        return status
    except Exception as error:
        return _status_error(error)


def _scheduler_status() -> dict[str, Any]:
    raw_interval = str(os.getenv(REMINDER_INTERVAL_ENV) or "").strip()
    try:
        interval = max(1.0, float(raw_interval)) if raw_interval else 30.0
    except Exception:
        interval = 30.0
    return {
        "ok": True,
        "enabled": _truthy_env(REMINDER_SCHEDULER_ENV),
        "running": False,
        "interval_seconds": interval,
        "ticks": 0,
        "last_ok": None,
        "last_notification_count": 0,
        "last_due_count": 0,
        "last_error": "",
        "env_var": REMINDER_SCHEDULER_ENV,
        "interval_env_var": REMINDER_INTERVAL_ENV,
        "status_source": "configuration_only",
    }


def _voice_status(verbose_safe: bool = False) -> dict[str, Any]:
    try:
        _ensure_personal_assistant_package()
        from core.personal_assistant import voice_runtime

        raw = voice_runtime.get_voice_runtime_status()
        stt = raw.get("stt_provider") if isinstance(raw.get("stt_provider"), dict) else {}
        safe = {
            "ok": True,
            "enabled": bool(raw.get("enabled")),
            "running": bool(raw.get("running")),
            "wake_word_configured": bool(raw.get("wake_word")),
            "listen_timeout_seconds": raw.get("listen_timeout_seconds"),
            "idle_sleep_seconds": raw.get("idle_sleep_seconds"),
            "wake_events": int(raw.get("wake_events") or 0),
            "commands_handled": int(raw.get("commands_handled") or 0),
            "last_event": str(raw.get("last_event") or ""),
            "last_error": str(raw.get("last_error") or "")[:240],
            "last_intent": str(raw.get("last_intent") or ""),
            "last_selected_tool": str(raw.get("last_selected_tool") or ""),
            "stt_provider": {
                "available": bool(stt.get("available")),
                "resolved_backend": str(stt.get("resolved_backend") or ""),
                "configured_backend": str(stt.get("configured_backend") or ""),
                "last_error_present": bool(stt.get("last_error")),
                "whisper_load_error_present": bool(stt.get("whisper_load_error")),
            },
            "env_var": raw.get("env_var"),
            "wake_word_env_var": raw.get("wake_word_env_var"),
            "listen_timeout_env_var": raw.get("listen_timeout_env_var"),
        }
        if verbose_safe:
            safe["wake_word"] = str(raw.get("wake_word") or "")
        return safe
    except Exception as error:
        return _status_error(error)


def _memory_status() -> dict[str, Any]:
    try:
        _ensure_personal_assistant_package()
        from core.personal_assistant import memory_manager

        raw = memory_manager.memory_status()
        return {
            "ok": bool(raw.get("ok")),
            "memory_file_path": raw.get("path"),
            "schema_version": raw.get("schema_version"),
            "memory_count": int(raw.get("memory_count") or 0),
            "active_count": int(raw.get("active_count") or 0),
            "archived_count": int(raw.get("archived_count") or 0),
            "conflict_count": int(raw.get("conflict_count") or 0),
            "stale_count": int(raw.get("stale_count") or 0),
            "count_by_category": dict(raw.get("categories") or {}),
            "local_only": bool(raw.get("local_only")),
            "cloud_sync": bool(raw.get("cloud_sync")),
            "private_values_exposed": False,
        }
    except Exception as error:
        return _status_error(error)


def _llm_planner_status() -> dict[str, Any]:
    provider_name_present = bool((os.getenv(LLM_PLANNER_PROVIDER_ENV) or os.getenv("LLM_PROVIDER") or "").strip())
    api_key_present = bool(os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    return {
        "enabled": _truthy_env(LLM_PLANNER_ENV),
        "env_var": LLM_PLANNER_ENV,
        "provider_env_var": LLM_PLANNER_PROVIDER_ENV,
        "provider_name_present": provider_name_present,
        "api_key_present": api_key_present,
        "provider_may_be_available": provider_name_present or api_key_present or _truthy_env(LLM_PLANNER_ENV),
        "provider_called": False,
    }


def _startup_status() -> dict[str, Any]:
    try:
        _ensure_personal_assistant_package()
        from core.personal_assistant import windows_startup_manager

        raw = windows_startup_manager.startup_status()
        return {
            "ok": bool(raw.get("ok")),
            "enabled": bool(raw.get("enabled")),
            "startup_method": raw.get("startup_method"),
            "target_valid": bool(raw.get("target_valid")),
            "error_count": len(raw.get("errors") or []),
            "message": raw.get("message"),
        }
    except Exception as error:
        return _status_error(error)


def _screen_status() -> dict[str, Any]:
    try:
        _ensure_personal_assistant_package()
        from core.personal_assistant import screen_context

        return {
            "ok": True,
            "window_awareness_importable": bool(getattr(screen_context, "window_awareness", None)),
            "screen_awareness_importable": bool(getattr(screen_context, "screen_awareness", None)),
            "screenshot_capture_performed": False,
            "ocr_capture_performed": False,
        }
    except Exception as error:
        return _status_error(error)


def _notification_status() -> dict[str, Any]:
    try:
        _ensure_personal_assistant_package()
        from core.personal_assistant import notifications

        return {
            "ok": True,
            "module_importable": True,
            "windows_toast_available": _module_available("winotify"),
            "fallback_channel": "log",
            "notification_sent": False,
            "formatter_available": callable(getattr(notifications, "build_reminder_notification_text", None)),
        }
    except Exception as error:
        return _status_error(error)


def _daily_use_readiness_status() -> dict[str, Any]:
    try:
        from daily_use_readiness import collect_daily_use_readiness

        return collect_daily_use_readiness()
    except Exception as error:
        return _status_error(error)


def _e2e_status() -> dict[str, Any]:
    script = ROOT / "scripts" / "dev" / "personal_assistant_e2e.py"
    docs = ROOT / "docs" / "PERSONAL_ASSISTANT_E2E_TEST_PACK.md"
    return {
        "ok": script.is_file(),
        "script_path": str(script),
        "script_exists": script.is_file(),
        "docs_exists": docs.is_file(),
    }


def build_personal_assistant_status(*, verbose_safe: bool = False) -> dict[str, Any]:
    import_error = ""
    try:
        _ensure_personal_assistant_package()
        from core.personal_assistant import context as _context  # noqa: F401

        importable = True
    except Exception as error:
        importable = False
        import_error = _safe_error(error)

    tools = _tool_status(verbose_safe=verbose_safe)
    scheduler = _scheduler_status()
    voice = _voice_status(verbose_safe=verbose_safe)
    memory = _memory_status()
    startup = _startup_status()
    screen = _screen_status()
    notifications = _notification_status()
    daily_use = _daily_use_readiness_status()
    e2e = _e2e_status()

    critical_failures = []
    if not importable:
        critical_failures.append("personal_assistant_import_failed")
    if not tools.get("ok") or int(tools.get("tool_count") or 0) == 0:
        critical_failures.append("tool_registry_unavailable")

    warnings = []
    for name, section in (
        ("scheduler", scheduler),
        ("voice_runtime", voice),
        ("memory_manager", memory),
        ("startup_integration", startup),
        ("screen_ocr", screen),
        ("notifications", notifications),
        ("daily_use_readiness", daily_use),
        ("e2e_pack", e2e),
    ):
        if not section.get("ok", True):
            warnings.append(f"{name}_warning")
    if daily_use.get("status") == "warning":
        warnings.append("daily_use_readiness_warning")
    if not notifications.get("windows_toast_available", False):
        warnings.append("windows_toast_optional_adapter_missing")
    if not screen.get("screen_awareness_importable", False):
        warnings.append("screen_ocr_optional_adapter_missing")
    if not voice.get("stt_provider", {}).get("available", False):
        warnings.append("voice_stt_optional_adapter_missing")

    status = {
        "ok": not critical_failures,
        "safe_to_expose": True,
        "read_only": True,
        "private_memory_values_exposed": False,
        "raw_transcripts_exposed": False,
        "screenshots_captured": False,
        "llm_provider_called": False,
        "personal_assistant": {
            "available": importable,
            "import_error": import_error,
            "package": "core.personal_assistant",
        },
        "tools": tools,
        "scheduler": scheduler,
        "voice_runtime": voice,
        "memory_manager": memory,
        "debug_mode": {
            "enabled": _truthy_env(DEBUG_ENV),
            "env_var": DEBUG_ENV,
        },
        "llm_planner": _llm_planner_status(),
        "startup_integration": startup,
        "screen_ocr": screen,
        "notifications": notifications,
        "daily_use_readiness": daily_use,
        "e2e_test_pack": e2e,
        "critical_failures": critical_failures,
        "warnings": sorted(set(warnings)),
    }
    if verbose_safe:
        status["environment_flags"] = {
            "debug": DEBUG_ENV,
            "llm_planner": LLM_PLANNER_ENV,
            "llm_planner_provider": LLM_PLANNER_PROVIDER_ENV,
            "reminder_scheduler": scheduler.get("env_var"),
            "voice_runtime": voice.get("env_var"),
        }
    return status


def _print_text(status: dict[str, Any]) -> None:
    tools = status.get("tools", {})
    scheduler = status.get("scheduler", {})
    voice = status.get("voice_runtime", {})
    daily_use = status.get("daily_use_readiness", {})
    memory = status.get("memory_manager", {})
    llm = status.get("llm_planner", {})
    print("GrandpaAssistant Personal Assistant Status")
    print(f"  Core available: {status.get('personal_assistant', {}).get('available')}")
    print(f"  Registered tools: {tools.get('tool_count', 0)}")
    print("  Tool names: " + ", ".join(tools.get("tool_names") or []))
    print(f"  Scheduler: enabled={scheduler.get('enabled')} running={scheduler.get('running')} interval={scheduler.get('interval_seconds')}")
    print(f"  Voice runtime: enabled={voice.get('enabled')} running={voice.get('running')} stt_available={voice.get('stt_provider', {}).get('available')}")
    print(
        "  Memory: count={count} active={active} archived={archived} conflicted={conflicted} stale={stale}".format(
            count=memory.get("memory_count", 0),
            active=memory.get("active_count", 0),
            archived=memory.get("archived_count", 0),
            conflicted=memory.get("conflict_count", 0),
            stale=memory.get("stale_count", 0),
        )
    )
    print(f"  Debug mode: {status.get('debug_mode', {}).get('enabled')}")
    print(f"  LLM planner: enabled={llm.get('enabled')} provider_available={llm.get('provider_may_be_available')} called={llm.get('provider_called')}")
    print(f"  Startup integration: enabled={status.get('startup_integration', {}).get('enabled')} target_valid={status.get('startup_integration', {}).get('target_valid')}")
    print(
        "  Screen/OCR: window_adapter={window} screen_adapter={screen} capture_performed={capture}".format(
            window=status.get("screen_ocr", {}).get("window_awareness_importable"),
            screen=status.get("screen_ocr", {}).get("screen_awareness_importable"),
            capture=status.get("screen_ocr", {}).get("screenshot_capture_performed"),
        )
    )
    print(f"  Notifications: toast={status.get('notifications', {}).get('windows_toast_available')} fallback={status.get('notifications', {}).get('fallback_channel')}")
    print(
        "  Daily-use readiness: status={status} ready={ready}/{total} warnings={warnings}".format(
            status=daily_use.get("status"),
            ready=daily_use.get("ready_count", 0),
            total=daily_use.get("section_count", 0),
            warnings=daily_use.get("warnings_count", 0),
        )
    )
    print(f"  E2E pack: {status.get('e2e_test_pack', {}).get('script_exists')}")
    print(f"  Warnings: {', '.join(status.get('warnings') or []) or 'none'}")
    print(f"  Overall OK: {status.get('ok')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print safe GrandpaAssistant personal-assistant diagnostics.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of the human-readable summary.")
    parser.add_argument("--check", action="store_true", help="Exit 0 only when critical personal-assistant imports and tools are healthy.")
    parser.add_argument("--verbose-safe", action="store_true", help="Include extra safe metadata without private content.")
    args = parser.parse_args(argv)

    try:
        status = build_personal_assistant_status(verbose_safe=args.verbose_safe)
        if args.json or args.check:
            print(json.dumps(status, indent=2, sort_keys=True))
        else:
            _print_text(status)
        return 0 if (not args.check or status.get("ok")) else 1
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        print(json.dumps({"ok": False, "error": _safe_error(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
