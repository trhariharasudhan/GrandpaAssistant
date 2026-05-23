from collections.abc import MutableMapping
from typing import Any

from fastapi import APIRouter, HTTPException, Request


def create_router(web_api_globals: MutableMapping[str, Any]) -> APIRouter:
    router = APIRouter()
    ChatSettingsRequest = web_api_globals["ChatSettingsRequest"]
    SessionRequest = web_api_globals["SessionRequest"]
    SessionUpdateRequest = web_api_globals["SessionUpdateRequest"]
    RegenerateRequest = web_api_globals["RegenerateRequest"]

    @router.get("/chat/settings")
    def get_chat_settings(request: Request):
        web_api_globals["_enforce_app_auth"](request)
        chat_settings = web_api_globals["_chat_settings"]
        return {
            "ok": True,
            "settings": {
                **chat_settings,
                "active_model": web_api_globals["_active_chat_model"](),
                "llm_status": web_api_globals["get_llm_status"](),
            },
        }

    @router.post("/chat/settings")
    def update_chat_settings(request: ChatSettingsRequest, http_request: Request):
        web_api_globals["_enforce_app_auth"](http_request)
        compact_text = web_api_globals["_compact_text"]
        chat_settings = web_api_globals["_chat_settings"]
        if request.llm_provider is not None:
            provider = compact_text(request.llm_provider).lower()
            chat_settings["llm_provider"] = (
                provider if provider in {"auto", "openai", "ollama"} else web_api_globals["DEFAULT_LLM_PROVIDER"]
            )
        if request.model is not None:
            chat_settings["model"] = compact_text(request.model) or web_api_globals["DEFAULT_OPENAI_MODEL"]
        if request.ollama_model is not None:
            chat_settings["ollama_model"] = compact_text(request.ollama_model) or web_api_globals["DEFAULT_OLLAMA_MODEL"]
        if request.system_prompt is not None:
            chat_settings["system_prompt"] = request.system_prompt.strip() or web_api_globals["SYSTEM_PROMPT"]
        if request.tone is not None:
            chat_settings["tone"] = compact_text(request.tone) or "friendly"
        if request.response_style is not None:
            chat_settings["response_style"] = compact_text(request.response_style) or "balanced"
        if request.tool_mode is not None:
            chat_settings["tool_mode"] = bool(request.tool_mode)
        web_api_globals["_apply_runtime_chat_settings"]()
        web_api_globals["_save_chat_state"]()
        return {
            "ok": True,
            "settings": {
                **chat_settings,
                "active_model": web_api_globals["_active_chat_model"](),
                "llm_status": web_api_globals["get_llm_status"](),
            },
        }

    @router.get("/chat/sessions")
    def get_sessions(request: Request):
        web_api_globals["_enforce_app_auth"](request)
        return {"ok": True, "sessions": web_api_globals["_ordered_sessions"]()}

    @router.post("/chat/sessions")
    def create_session(request: SessionRequest, http_request: Request):
        web_api_globals["_enforce_app_auth"](http_request)
        session = web_api_globals["_ensure_session"](
            title=web_api_globals["_compact_text"](request.title) or "New chat",
            create_new=True,
        )
        web_api_globals["_save_chat_state"]()
        return {"ok": True, "session": session, "sessions": web_api_globals["_ordered_sessions"]()}

    @router.post("/chat/sessions/rename")
    def rename_session(request: SessionUpdateRequest, http_request: Request):
        web_api_globals["_enforce_app_auth"](http_request)
        session = web_api_globals["_chat_sessions"].get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        session["title"] = web_api_globals["_compact_text"](request.title) or session["title"]
        session["updated_at"] = web_api_globals["_utc_now"]()
        web_api_globals["_save_chat_state"]()
        return {"ok": True, "session": session, "sessions": web_api_globals["_ordered_sessions"]()}

    @router.post("/chat/sessions/delete")
    def delete_session(request: RegenerateRequest, http_request: Request):
        web_api_globals["_enforce_app_auth"](http_request)
        deleted = web_api_globals["_delete_session"](request.session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found.")
        current = web_api_globals["_ordered_sessions"]()[0]
        return {
            "ok": True,
            "sessions": web_api_globals["_ordered_sessions"](),
            "current_session_id": current["id"],
        }

    @router.get("/chat/history")
    def chat_history(request: Request, session_id: str | None = None):
        web_api_globals["_enforce_app_auth"](request)
        session = web_api_globals["_resolve_session"](session_id=session_id)
        return {
            "ok": True,
            "session": session,
            "messages": session["messages"],
            "sessions": web_api_globals["_ordered_sessions"](),
        }

    web_api_globals["get_chat_settings"] = get_chat_settings
    web_api_globals["update_chat_settings"] = update_chat_settings
    web_api_globals["get_sessions"] = get_sessions
    web_api_globals["create_session"] = create_session
    web_api_globals["rename_session"] = rename_session
    web_api_globals["delete_session"] = delete_session
    web_api_globals["chat_history"] = chat_history
    return router
