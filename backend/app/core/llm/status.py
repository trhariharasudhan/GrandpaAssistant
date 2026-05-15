from __future__ import annotations

from typing import Any

from .provider_manager import LLMProviderManager, get_default_provider_manager


KNOWN_PROVIDERS = ("openai", "gemini", "ollama", "fallback")


def _manager(manager: LLMProviderManager | None = None) -> LLMProviderManager:
    return manager or get_default_provider_manager()


def _normalize_provider_name(provider: str | None, manager: LLMProviderManager) -> str:
    requested = str(provider or "").strip().lower()
    if requested in {"", "auto"}:
        return manager.resolve_provider_name(provider)
    return manager.resolve_provider_name(requested)


def _safe_model_info(manager: LLMProviderManager, provider: str) -> dict[str, Any]:
    try:
        info = manager.model_info(provider)
    except Exception as error:
        info = {"provider": provider, "error": str(error)}
    return info if isinstance(info, dict) else {"provider": provider}


def _safe_health(manager: LLMProviderManager, provider: str, *, force: bool = False) -> dict[str, Any]:
    try:
        health = manager.registry.health_check(provider, force=force)
    except Exception as error:
        health = {"ok": False, "provider": provider, "error": str(error)}
    return health if isinstance(health, dict) else {"ok": False, "provider": provider}


def get_provider_status(
    provider: str | None = None,
    *,
    manager: LLMProviderManager | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Return normalized status for one provider without changing provider behavior."""
    active_manager = _manager(manager)
    provider_name = _normalize_provider_name(provider, active_manager)
    model_info = _safe_model_info(active_manager, provider_name)
    health = _safe_health(active_manager, provider_name, force=force)
    ok = bool(health.get("ok"))
    model = str(model_info.get("model") or health.get("model") or "").strip()
    base_url = str(model_info.get("base_url") or health.get("base_url") or "").strip()
    installed_models = health.get("installed_models") or []
    if not isinstance(installed_models, list):
        installed_models = list(installed_models)

    return {
        "provider": provider_name,
        "name": provider_name,
        "model": model,
        "base_url": base_url,
        "ok": ok,
        "healthy": ok,
        "ready": ok,
        "available": ok,
        "status": "ok" if ok else "unavailable",
        "error": str(health.get("error") or ""),
        "streaming": bool(model_info.get("streaming")),
        "memory": model_info.get("memory", ""),
        "fallback": bool(model_info.get("fallback") or health.get("fallback") or provider_name == "fallback"),
        "installed_models": installed_models,
        "health": health,
        "model_info": model_info,
    }


def get_all_provider_statuses(
    *,
    manager: LLMProviderManager | None = None,
    force: bool = False,
) -> dict[str, dict[str, Any]]:
    """Return normalized statuses for all registered providers."""
    active_manager = _manager(manager)
    names = active_manager.registry.names() or list(KNOWN_PROVIDERS)
    return {
        name: get_provider_status(name, manager=active_manager, force=force)
        for name in names
    }


def get_active_provider_summary(
    provider: str | None = None,
    *,
    manager: LLMProviderManager | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Return a compact active-provider view for old status endpoints and commands."""
    active_manager = _manager(manager)
    provider_name = _normalize_provider_name(provider, active_manager)
    status = get_provider_status(provider_name, manager=active_manager, force=force)
    return {
        "provider": status["provider"],
        "model": status["model"],
        "base_url": status["base_url"],
        "ok": status["ok"],
        "ready": status["ready"],
        "healthy": status["healthy"],
        "available": status["available"],
        "status": status["status"],
        "error": status["error"],
        "fallback_chain": active_manager.fallback_chain(provider_name),
        "health": status["health"],
        "model_info": status["model_info"],
    }


def get_model_summary(
    provider: str | None = None,
    *,
    manager: LLMProviderManager | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Return active and per-provider model metadata from the unified registry."""
    active_manager = _manager(manager)
    active = get_active_provider_summary(provider, manager=active_manager, force=force)
    providers = get_all_provider_statuses(manager=active_manager, force=force)
    return {
        "provider": active["provider"],
        "model": active["model"],
        "active_provider": active["provider"],
        "active_model": active["model"],
        "models": {
            name: {
                "provider": item["provider"],
                "model": item["model"],
                "base_url": item["base_url"],
                "streaming": item["streaming"],
                "status": item["status"],
            }
            for name, item in providers.items()
        },
    }


def get_health_report(
    provider: str | None = None,
    *,
    manager: LLMProviderManager | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Return the shared health report used by diagnostics and compatibility wrappers."""
    active_manager = _manager(manager)
    active = get_active_provider_summary(provider, manager=active_manager, force=force)
    providers = get_all_provider_statuses(manager=active_manager, force=force)
    return {
        "ok": bool(active.get("ok")) or bool(providers.get("fallback", {}).get("ok")),
        "active": active,
        "providers": providers,
        "model_summary": get_model_summary(provider, manager=active_manager, force=force),
    }
