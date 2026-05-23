from collections.abc import MutableMapping
import json
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse


def create_router(web_api_globals: MutableMapping[str, Any]) -> APIRouter:
    router = APIRouter()
    ChatSettingsRequest = web_api_globals["ChatSettingsRequest"]
    SessionRequest = web_api_globals["SessionRequest"]
    SessionUpdateRequest = web_api_globals["SessionUpdateRequest"]
    RegenerateRequest = web_api_globals["RegenerateRequest"]
    RemoveDocumentRequest = web_api_globals["RemoveDocumentRequest"]
    CancelRequest = web_api_globals["CancelRequest"]
    ChatRequest = web_api_globals["ChatRequest"]

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

    @router.post("/chat/upload")
    async def chat_upload(
        request: Request,
        file: UploadFile = File(...),
        session_id: str | None = Form(default=None),
    ):
        web_api_globals["_enforce_app_auth"](request)
        session = web_api_globals["_resolve_session"](session_id=session_id)
        filename = web_api_globals["_compact_text"](file.filename) or "document"
        try:
            data = await file.read()
            document = web_api_globals["_extract_document_payload"](filename, data)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=500, detail=f"Could not read file: {error}") from error

        documents = web_api_globals["_normalize_documents"](session.get("documents"))
        documents = [item for item in documents if item.get("name") != document["name"]]
        documents.append(document)
        session["documents"] = documents
        session["updated_at"] = web_api_globals["_utc_now"]()
        web_api_globals["_save_chat_state"]()
        return {
            "ok": True,
            "document": {key: value for key, value in document.items() if key != "chunks"},
            "documents": [{key: value for key, value in item.items() if key != "chunks"} for item in documents],
            "session": session,
            "sessions": web_api_globals["_ordered_sessions"](),
        }

    @router.post("/chat/upload/remove")
    def chat_remove_upload(payload: RemoveDocumentRequest, request: Request):
        web_api_globals["_enforce_app_auth"](request)
        session = web_api_globals["_resolve_session"](session_id=payload.session_id)
        filename = web_api_globals["_compact_text"](payload.filename)
        if not filename:
            raise HTTPException(status_code=400, detail="Filename is required.")

        documents = web_api_globals["_normalize_documents"](session.get("documents"))
        original_count = len(documents)
        documents = [item for item in documents if item.get("name") != filename]

        if len(documents) == original_count:
            raise HTTPException(status_code=404, detail="Document not found in session.")

        session["documents"] = documents
        session["updated_at"] = web_api_globals["_utc_now"]()
        web_api_globals["_save_chat_state"]()
        return {
            "ok": True,
            "documents": [{key: value for key, value in item.items() if key != "chunks"} for item in documents],
            "session": session,
        }

    @router.get("/chat/export")
    def export_chat(request: Request, session_id: str):
        web_api_globals["_enforce_app_auth"](request)
        session = web_api_globals["_chat_sessions"].get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")

        lines = [f"# {session['title']}", ""]
        for item in session["messages"]:
            role = "You" if item["role"] == "user" else "Grandpa"
            timestamp = item.get("created_at", "")
            lines.append(f"[{timestamp}] {role}: {item.get('content', '')}")
        return {
            "ok": True,
            "session": {
                "id": session["id"],
                "title": session["title"],
            },
            "content": "\n".join(lines).strip(),
            "filename": f"{session['title'].replace(' ', '_').lower() or 'chat'}.md",
        }

    @router.post("/chat/reset")
    def chat_reset(request: Request, session_id: str | None = None):
        web_api_globals["_enforce_app_auth"](request)
        session = web_api_globals["_resolve_session"](session_id=session_id)
        session["messages"] = []
        session["updated_at"] = web_api_globals["_utc_now"]()
        web_api_globals["reset_clean_chat_session"](session["id"])
        web_api_globals["_save_chat_state"]()
        return {"ok": True}

    @router.post("/chat/cancel")
    def chat_cancel(payload: CancelRequest, request: Request):
        web_api_globals["_enforce_app_auth"](request)
        web_api_globals["_cancelled_streams"].add(payload.session_id)
        return {"ok": True}

    @router.post("/chat/stream")
    async def chat_stream(request: ChatRequest, http_request: Request = None):
        message = web_api_globals["_compact_text"](request.message)
        if not message:
            raise HTTPException(status_code=400, detail="Message is required.")
        web_api_globals["_enforce_app_auth"](http_request)
        user_id = web_api_globals["_authenticated_user_id"](http_request)
        prompt_guard = web_api_globals["validate_prompt_text"](message, source="web-api-stream")
        if not prompt_guard.get("allowed", True):
            async def blocked_stream():
                yield f"data: {json.dumps({'type': 'delta', 'content': prompt_guard.get('message', 'Unsafe prompt blocked.')})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'content': prompt_guard.get('message', 'Unsafe prompt blocked.'), 'interaction_id': None})}\n\n"

            return StreamingResponse(blocked_stream(), media_type="text/event-stream")

        session = web_api_globals["_resolve_session"](session_id=request.session_id)
        mood_snapshot = web_api_globals["record_mood_from_analysis"](
            message,
            web_api_globals["analyze_emotion"](message),
            source="web-api-stream",
        )
        runtime_observation = web_api_globals["ASSISTANT_RUNTIME"].observe_user_message(
            message,
            source="web-api-stream",
            emotion={"emotion": mood_snapshot.get("last_mood", "neutral")},
            mood=mood_snapshot,
        )
        context = runtime_observation.get("context", "casual")
        web_api_globals["observe_user_turn"](
            message,
            context=context,
            emotion=mood_snapshot.get("last_mood", "neutral"),
            mood=mood_snapshot.get("last_mood", "neutral"),
            source="web-api-stream",
        )
        web_api_globals["_update_session_title"](session, message)
        session_id = session["id"]
        if session_id in web_api_globals["_cancelled_streams"]:
            web_api_globals["_cancelled_streams"].discard(session_id)

        user_item = web_api_globals["_history_item"]("user", message)
        session["messages"].append(user_item)
        session["messages"] = web_api_globals["_trim_messages"](session["messages"])
        session["updated_at"] = web_api_globals["_utc_now"]()
        web_api_globals["_save_chat_state"]()
        web_api_globals["append_chat_message"](
            session_id,
            "user",
            message,
            user_id=user_id,
            source="web-stream",
            emotion=mood_snapshot.get("last_mood", "neutral"),
            metadata={"context": context},
        )
        web_api_globals["MOBILE_COMPANION"].record_chat_message("user", message, session_id=session_id, source="desktop-stream")
        history_snapshot = list(session["messages"][:-1])
        prompt_message = web_api_globals["_build_chat_input"](session, message, mood_snapshot=mood_snapshot, context=context)

        async def event_stream():
            full_reply = ""
            emitted_length = 0
            confirmation_id = None
            try:
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "mood",
                            "mood": mood_snapshot,
                            "session": {"id": session["id"], "title": session["title"]},
                        }
                    )
                    + "\n\n"
                )
                if web_api_globals["_looks_like_direct_action_input"](message):
                    direct_reply, tool_command, tool_messages, confirmation_id = web_api_globals["_execute_tool_command_for_chat"](
                        web_api_globals["_compact_text"](message),
                        source="chat-direct-stream",
                    )
                    assistant_item = web_api_globals["_history_item"](
                        "assistant",
                        direct_reply.strip() or "I could not generate a reply right now.",
                    )
                    if tool_command:
                        assistant_item["tool"] = {"command": tool_command, "messages": tool_messages}
                    if confirmation_id:
                        assistant_item["confirmation_id"] = confirmation_id
                    session["messages"].append(assistant_item)
                    session["messages"] = web_api_globals["_trim_messages"](session["messages"])
                    session["updated_at"] = web_api_globals["_utc_now"]()
                    web_api_globals["_save_chat_state"]()
                    web_api_globals["append_chat_message"](
                        session["id"],
                        "assistant",
                        assistant_item["content"],
                        user_id=user_id,
                        source="web-stream",
                        emotion=mood_snapshot.get("last_mood", "neutral"),
                        metadata={"route": "tool-direct"},
                    )
                    web_api_globals["MOBILE_COMPANION"].record_chat_message(
                        "assistant",
                        assistant_item["content"],
                        session_id=session["id"],
                        source="desktop-stream",
                    )
                    web_api_globals["ASSISTANT_RUNTIME"].observe_assistant_reply(assistant_item["content"], source="web-api-stream")
                    interaction = web_api_globals["record_assistant_turn"](
                        message,
                        assistant_item["content"],
                        context=context,
                        emotion=mood_snapshot.get("last_mood", "neutral"),
                        mood=mood_snapshot.get("last_mood", "neutral"),
                        source="web-api-stream",
                        route="tool-direct",
                        model="command-router",
                    )
                    web_api_globals["log_audit_event"](
                        "chat",
                        "assistant_stream_reply",
                        user_id=user_id,
                        payload={"session_id": session["id"], "route": "tool-direct", "interaction_id": interaction.get("id")},
                    )
                    yield (
                        "data: "
                        + json.dumps(
                            {
                                "type": "done",
                                "message": assistant_item,
                                "interaction_id": interaction.get("id"),
                                "session": {"id": session["id"], "title": session["title"]},
                            }
                        )
                        + "\n\n"
                    )
                    return

                for chunk in web_api_globals["stream_chat_reply"](
                    history_snapshot,
                    prompt_message,
                    model=web_api_globals["_active_chat_model"](),
                    system_prompt=web_api_globals["_effective_system_prompt"](message, mood_snapshot=mood_snapshot, context=context),
                ):
                    if session_id in web_api_globals["_cancelled_streams"]:
                        web_api_globals["_cancelled_streams"].discard(session_id)
                        yield f"data: {json.dumps({'type': 'cancelled'})}\n\n"
                        return
                    full_reply += chunk
                    if web_api_globals["_looks_like_echo_prefix"](full_reply, message):
                        continue
                    outgoing = full_reply[emitted_length:]
                    emitted_length = len(full_reply)
                    if outgoing:
                        yield f"data: {json.dumps({'type': 'chunk', 'content': outgoing, 'session_id': session_id})}\n\n"

                tool_command = None
                tool_messages = []
                stripped = full_reply.strip()
                if web_api_globals["_chat_settings"].get("tool_mode") and stripped.startswith("TOOL:"):
                    tool_command = web_api_globals["_compact_text"](stripped.replace("TOOL:", "", 1))
                    if web_api_globals["_is_risky_command"](tool_command):
                        confirmation_id = web_api_globals["_create_confirmation"](tool_command, source="chat-tool")
                        full_reply = f"I can do that, but I need confirmation first: {tool_command}"
                    else:
                        tool_messages = web_api_globals["_capture_command_reply"](tool_command)
                        bridge_message = (
                            f"User request: {message}\nTool command used: {tool_command}\nTool result: {' '.join(tool_messages)}\n"
                            "Now answer the user naturally using that result."
                        )
                        full_reply = web_api_globals["generate_chat_reply"](
                            history_snapshot,
                            bridge_message,
                            model=web_api_globals["_active_chat_model"](),
                            system_prompt=web_api_globals["_effective_system_prompt"](message, mood_snapshot=mood_snapshot, context=context),
                        )
                        full_reply = web_api_globals["_sanitize_assistant_reply"](full_reply, message)

                assistant_item = web_api_globals["_history_item"]("assistant", web_api_globals["_sanitize_assistant_reply"](full_reply, message))
                if tool_command:
                    assistant_item["tool"] = {"command": tool_command, "messages": tool_messages}
                if confirmation_id:
                    assistant_item["confirmation_id"] = confirmation_id
                session["messages"].append(assistant_item)
                session["messages"] = web_api_globals["_trim_messages"](session["messages"])
                session["updated_at"] = web_api_globals["_utc_now"]()
                web_api_globals["_save_chat_state"]()
                web_api_globals["append_chat_message"](
                    session["id"],
                    "assistant",
                    assistant_item["content"],
                    user_id=user_id,
                    source="web-stream",
                    emotion=mood_snapshot.get("last_mood", "neutral"),
                    metadata={"route": "chat-stream", "model": web_api_globals["_active_chat_model"]()},
                )
                web_api_globals["MOBILE_COMPANION"].record_chat_message(
                    "assistant",
                    assistant_item["content"],
                    session_id=session["id"],
                    source="desktop-stream",
                )
                web_api_globals["ASSISTANT_RUNTIME"].observe_assistant_reply(assistant_item["content"], source="web-api-stream")
                interaction = web_api_globals["record_assistant_turn"](
                    message,
                    assistant_item["content"],
                    context=context,
                    emotion=mood_snapshot.get("last_mood", "neutral"),
                    mood=mood_snapshot.get("last_mood", "neutral"),
                    source="web-api-stream",
                    route="chat-stream",
                    model=web_api_globals["_active_chat_model"](),
                )
                web_api_globals["log_audit_event"](
                    "chat",
                    "assistant_stream_reply",
                    user_id=user_id,
                    payload={"session_id": session["id"], "route": "chat-stream", "interaction_id": interaction.get("id")},
                )
                yield f"data: {json.dumps({'type': 'done', 'message': assistant_item, 'interaction_id': interaction.get('id'), 'session': {'id': session['id'], 'title': session['title']}})}\n\n"
            except Exception as error:
                web_api_globals["record_system_error"]("web-api-stream", str(error), metadata={"context": context})
                yield f"data: {json.dumps({'type': 'error', 'error': web_api_globals['_friendly_ai_error'](error)})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    web_api_globals["get_chat_settings"] = get_chat_settings
    web_api_globals["update_chat_settings"] = update_chat_settings
    web_api_globals["get_sessions"] = get_sessions
    web_api_globals["create_session"] = create_session
    web_api_globals["rename_session"] = rename_session
    web_api_globals["delete_session"] = delete_session
    web_api_globals["chat_history"] = chat_history
    web_api_globals["chat_upload"] = chat_upload
    web_api_globals["chat_remove_upload"] = chat_remove_upload
    web_api_globals["export_chat"] = export_chat
    web_api_globals["chat_reset"] = chat_reset
    web_api_globals["chat_cancel"] = chat_cancel
    web_api_globals["chat_stream"] = chat_stream
    return router
