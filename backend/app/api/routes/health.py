from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from fastapi import APIRouter, Request


def _daily_use_readiness() -> dict[str, Any]:
    from daily_use_readiness import collect_daily_use_readiness

    return collect_daily_use_readiness()


def create_router(deps: MutableMapping[str, Any]) -> APIRouter:
    router = APIRouter()

    @router.get("/api/health")
    def api_health():
        assistant_runtime = deps["ASSISTANT_RUNTIME"]
        if not assistant_runtime.status_payload().get("running"):
            assistant_runtime.start()
        return {
            "ok": True,
            "service": "grandpa-assistant-api",
            "runtime": assistant_runtime.status_payload(),
            "semantic_memory": deps["semantic_memory_status"](prewarm=False),
            "doctor": deps["collect_startup_diagnostics"](),
        }

    @router.get("/api/doctor")
    def api_doctor():
        return {
            "ok": True,
            "doctor": deps["collect_startup_diagnostics"](use_cache=False),
            "daily_use_readiness": _daily_use_readiness(),
        }

    @router.get("/api/backend/stability")
    def api_backend_stability(request: Request):
        context = deps["_authenticated_app_context"](request, required=False)
        if not deps["_is_local_request"](request) and not deps["_is_admin_context"](context):
            return deps["_restricted_stability_payload"]()
        return deps["build_backend_stability_payload"](
            pending_confirmations=deps["_pending_confirmations"],
            api_health={
                "key": "api_health",
                "name": "API health",
                "status": "ok",
                "detail": "API health is responding through the active backend process.",
            },
        )

    return router
