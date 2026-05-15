# GrandpaAssistant Feature Audit

Documentation-only audit of the active backend-only Windows assistant checkout.

Status values: COMPLETE, PARTIAL, BROKEN, MISSING, DUPLICATE.

## Summary Table

| Area | Status | Evidence | Notes |
| --- | --- | --- | --- |
| Backend runtime entry | COMPLETE | `backend/desktop_backend_entry.py`, `backend/app/api/web_api.py` | Active run path is `python backend\desktop_backend_entry.py`. It initializes the web runtime and starts FastAPI/uvicorn on localhost by default. |
| Terminal chatbot | COMPLETE | `backend/app/cli/chat.py`, `backend/app/core/chatbot/`, `docs/TERMINAL_CHATBOT.md`, `tests/test_terminal_chat_cli.py` | Terminal-only CLI, slash commands, fallback provider, memory, config summary, and smoke mode are covered. |
| Main chat API | PARTIAL | `backend/app/core/chat_service.py`, `backend/app/api/web_api.py`, `backend/app/api/chat_api.py` | Chat service is tested and has local knowledge fallback. There are two API modules with overlapping chat routes, which increases maintenance risk. |
| Memory/database | PARTIAL | `backend/app/shared/brain/database.py`, `backend/app/shared/brain/memory_engine.py`, `backend/app/core/chatbot/memory.py`, `backend/app/shared/productivity_store.py` | SQLite-backed assistant memory and productivity state exist. Terminal chatbot uses a separate SQLite schema under `runtime/data/grandpa_chat.db`. Legacy JSON migration paths remain. |
| OpenAI provider | PARTIAL | `backend/app/core/chatbot/providers/openai_provider.py`, `backend/app/shared/llm_client.py` | Implemented through direct chat-completions HTTP calls with missing-key handling and retries in shared LLM client. Needs current API/model review before production hardening. |
| Gemini provider | PARTIAL | `backend/app/core/chatbot/providers/gemini_provider.py` | Implemented for terminal chatbot provider selection. The broader shared LLM client does not expose Gemini. |
| Ollama provider | PARTIAL | `backend/app/core/chatbot/providers/ollama_provider.py`, `backend/app/shared/llm_client.py`, `backend/app/shared/brain/ai_engine.py` | Implemented in both terminal provider stack and shared LLM stack. Depends on a local Ollama service. |
| Fallback provider | COMPLETE | `backend/app/core/chatbot/providers/fallback_provider.py`, `backend/app/core/chatbot/intent_router.py` | Rule-based fallback and local intents prevent blank replies and exact echo behavior. |
| Voice input | PARTIAL | `backend/app/features/voice/listen.py`, `tests/test_optional_dependency_guards.py` | Supports speech_recognition, sounddevice, Whisper-style settings, wake aliases, sensitivity profiles, and dependency guards. Hardware and optional packages determine readiness. |
| Voice output | PARTIAL | `backend/app/features/voice/speak.py`, `backend/assets/sounds/` | Supports pyttsx3/SAPI, Piper, Coqui/custom voice settings, sounds, and emotion tone settings. Optional backends require local setup. |
| Vision/screen understanding | PARTIAL | `backend/app/features/vision/screen_reader.py`, `backend/app/shared/screen_awareness.py`, `backend/app/features/ui_analysis/`, `tests/test_screen_awareness.py`, `tests/test_ui_analysis.py` | OCR, screenshot capture, error-like text detection, UI element planning, and guarded UI execution exist. Tesseract, pyautogui, OpenCV, and display permissions affect runtime readiness. |
| Object detection | PARTIAL | `backend/app/features/vision/object_detection.py`, `backend/assets/models/hand_landmarker.task` | YOLO/OpenCV path exists with availability checks. Model and camera dependencies are optional. |
| Command router | PARTIAL | `backend/app/core/command_router.py`, `tests/test_command_router_confirmations.py` | Large central router handles many commands, confirmations, debug tools, contacts, screen commands, local knowledge, mobile companion API commands, and n8n. Size and mixed responsibilities are the main risk. |
| Desktop automation | PARTIAL | `backend/app/services/local_action_executor.py`, `backend/app/features/system/`, `backend/app/features/automation/`, `tests/test_local_action_executor.py` | Safe local action executor is allowlisted and audited. Browser, messaging, system controls, and Windows helpers exist, but many depend on host apps, permissions, or manual confirmation. |
| RAG/project knowledge | PARTIAL | `backend/app/shared/local_knowledge.py`, `backend/data/knowledge/*.json`, `backend/app/api/web_api.py` chat upload/export routes | Local structured knowledge and review queue exist. Chat upload/session routes exist, but this is not a fully unified retrieval pipeline across all assistant paths. |
| Reminders/tasks | COMPLETE | `backend/app/features/productivity/task_module.py`, `backend/app/shared/productivity_store.py`, `tests/test_productivity_store.py` | Tasks, reminders, due dates, recurrence, snooze, priority/category, SQLite persistence, and legacy migration are implemented and tested. |
| Notifications/automation reminders | PARTIAL | `backend/app/features/automation/notification_module.py` | Reminder/event popup monitor exists. It uses Windows COM popup behavior and local settings, so runtime depends on Windows desktop availability. |
| Logging | PARTIAL | `runtime/logs`, `backend/app/core/chatbot/engine.py`, `backend/app/services/local_action_executor.py`, debug audit modules | Terminal chat and local actions log to runtime paths. Logging is spread across modules rather than one unified logging policy. |
| Config | COMPLETE | `backend/app/shared/utils/config.py`, `backend/app/shared/utils/paths.py`, `backend/app/config/terminal_chat.json` | Settings defaults, runtime path resolution, env overrides, and terminal chat config exist. |
| Tests | COMPLETE | `tests/` | Unittest discovery finds 301 tests and covers core backend routes, chat, local actions, debug assistant, UI analysis, screen/window awareness, productivity store, and optional dependency guards. |
| Frontend/mobile client workspaces | MISSING | no tracked `frontend/` or `mobile/` directories | This is expected for the active backend-only project. Backend mobile companion API logic still exists as runtime logic. |

## Duplicate, Unused, Or Partial Modules

| Area | Status | Finding | Safe interpretation |
| --- | --- | --- | --- |
| `backend/app/features/modules/` | DUPLICATE | Thin compatibility aliases forward legacy `modules.*` imports to real domain folders. | Keep for now. Do not add business logic here. Later cleanup can remove only after import paths are migrated and tests prove it. |
| `backend/app/api/web_api.py` and `backend/app/api/chat_api.py` | DUPLICATE | Both expose chat/auth/device/settings style routes, with different URL prefixes and runtime roles. | Document supported public runtime first. Consolidation is possible later but high risk. |
| Terminal chatbot provider stack vs shared LLM stack | DUPLICATE | `backend/app/core/chatbot/providers/*` and `backend/app/shared/llm_client.py` implement separate provider logic. | Keep both until runtime ownership is clarified. Terminal CLI is clean and isolated. |
| `backend/app/shared/brain/*` vs pycache-only `backend/app/brain/*` | DUPLICATE | Source files live under `shared/brain`; `backend/app/brain` contains pycache-only artifacts in this checkout. | Do not delete in this pass. Future cleanup can remove pycache/artifact directories after confirming they are untracked and ignored. |
| `backend/app/shared/cognition/*` and pycache-only `backend/app/brain/cognition/*` | DUPLICATE | Active source appears in `shared/cognition`; old compiled artifacts exist elsewhere. | Treat as cleanup candidate, not runtime source. |
| `backend/app/agents/*` | PARTIAL | Agent runtime/catalog/message bus/state store exist. | Needs a separate audit to determine which routes actually rely on it. |
| `backend/app/services/*` | PARTIAL | Only `local_action_executor.py` source is present in services; subfolders contain compiled artifacts only in this checkout. | Do not remove yet. Note as artifact cleanup candidate. |
| Mobile companion backend logic | PARTIAL | `backend/app/shared/mobile_companion.py`, `/api/mobile/*`, `/mobile/*` routes in `web_api.py`. | Backend runtime feature remains even though no mobile app-client workspace exists. |
| Debug assistant system | COMPLETE | `backend/app/shared/debug_*`, `docs/DEBUG_ASSISTANT_GUIDE.md`, extensive tests. | Well-covered local backend troubleshooting surface. |

## Missing Features

- MISSING: Active frontend or mobile client workspace. This is intentional for the current backend-only project.
- MISSING: One unified LLM provider abstraction used by both terminal chat and web chat.
- MISSING: One unified memory abstraction across terminal chat, assistant memory, productivity state, and chat API session history.
- MISSING: A single authoritative route map that declares which API module is production runtime versus legacy/alternate.
- MISSING: Automated live hardware validation for microphone, speaker, OCR, camera, and Windows automation beyond smoke/guard tests.

