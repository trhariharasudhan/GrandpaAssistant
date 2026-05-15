# Duplication Risks

This report identifies candidates for later cleanup. It does not authorize moving or deleting code.

## High-Level Risks

| Area | Status | Recommendation |
| --- | --- | --- |
| web_api.py vs chat_api.py | DUPLICATE | Both define FastAPI apps and overlapping chat/auth/runtime surfaces. Keep runtime stable; document route ownership before moving routes. |
| terminal chatbot providers vs shared llm_client | DUPLICATE | Terminal chatbot has OpenAI/Gemini/Ollama/fallback providers. Shared web chat client has OpenAI/Ollama plus fallback behavior through local knowledge and error paths. |
| memory/database modules | DUPLICATE | Assistant memory DB, productivity scope store, and terminal chat DB are separate. Do not merge without migration design. |
| command_router.py | PARTIAL | Large central command dispatcher. Refactor only after route/import inventory and domain-specific tests are in place. |
| features/modules | DUPLICATE | Compatibility aliases for legacy imports. Keep until all legacy import users are migrated. |

## Focus File Sizes And Route Counts

| Area | File | Lines | Routes |
| --- | --- | --- | --- |
| web_api | backend/app/api/web_api.py | 3607 | 91 |
| chat_api | backend/app/api/chat_api.py | 2000 | 76 |
| command_router | backend/app/core/command_router.py | 6441 | 0 |
| unified_command_router | backend/app/core/unified_command_router.py | 413 | 0 |

## Focus Module Comparison

| Area | File | Lines | Imports | Routes | Markers |
| --- | --- | --- | --- | --- | --- |
| web_api | backend/app/api/web_api.py | 3607 | 185 | 91 | 0 |
| chat_api | backend/app/api/chat_api.py | 2000 | 112 | 76 | 0 |
| command_router | backend/app/core/command_router.py | 6441 | 358 | 0 | 0 |
| unified_command_router | backend/app/core/unified_command_router.py | 413 | 18 | 0 | 0 |
| shared_llm_client | backend/app/shared/llm_client.py | 534 | 12 | 0 | 0 |
| shared_claude_client | backend/app/shared/claude_client.py | 106 | 2 | 0 | 0 |
| shared_offline_multi_model | backend/app/shared/offline_multi_model.py | 237 | 8 | 0 | 0 |
| assistant_database | backend/app/shared/brain/database.py | 258 | 11 | 0 | 0 |
| assistant_memory_engine | backend/app/shared/brain/memory_engine.py | 909 | 11 | 0 | 0 |
| semantic_memory | backend/app/shared/brain/semantic_memory.py | 488 | 10 | 0 | 0 |
| terminal_chat_memory | backend/app/core/chatbot/memory.py | 176 | 8 | 0 | 0 |
| terminal_provider:__init__ | backend/app/core/chatbot/providers/__init__.py | 6 | 4 | 0 | 0 |
| terminal_provider:base | backend/app/core/chatbot/providers/base.py | 21 | 3 | 0 | 0 |
| terminal_provider:fallback_provider | backend/app/core/chatbot/providers/fallback_provider.py | 14 | 3 | 0 | 0 |
| terminal_provider:gemini_provider | backend/app/core/chatbot/providers/gemini_provider.py | 18 | 3 | 0 | 0 |
| terminal_provider:ollama_provider | backend/app/core/chatbot/providers/ollama_provider.py | 17 | 3 | 0 | 0 |
| terminal_provider:openai_provider | backend/app/core/chatbot/providers/openai_provider.py | 18 | 3 | 0 | 0 |

## Exact Duplicate Method/Path Routes

| Method | Path | Locations |
| --- | --- | --- |
| POST | /api/automation/n8n/test | backend/app/api/chat_api.py:804 `n8n_test`<br>backend/app/api/web_api.py:2462 `api_n8n_test` |
| POST | /chat | backend/app/api/chat_api.py:1785 `chat`<br>backend/app/api/web_api.py:3189 `chat_reply` |
| GET | /chat/history | backend/app/api/chat_api.py:1773 `get_chat_history`<br>backend/app/api/web_api.py:3084 `chat_history` |
| POST | /chat/reset | backend/app/api/chat_api.py:1778 `reset_chat`<br>backend/app/api/web_api.py:3171 `chat_reset` |
| POST | /chat/stream | backend/app/api/chat_api.py:1911 `chat_stream`<br>backend/app/api/web_api.py:3355 `chat_stream` |

## Same Path Across Multiple Declarations

| Path | Locations |
| --- | --- |
| /api/auth/profile | GET backend/app/api/web_api.py:2576 `api_auth_profile`<br>POST backend/app/api/web_api.py:2582 `api_auth_update_profile` |
| /api/contacts | GET backend/app/api/web_api.py:2411 `api_contacts`<br>POST backend/app/api/web_api.py:2419 `api_add_contact` |
| /api/debug/fix-approvals | GET backend/app/api/web_api.py:2232 `api_fix_approvals`<br>POST backend/app/api/web_api.py:2240 `api_create_fix_approval` |
| /api/settings/startup | GET backend/app/api/web_api.py:2677 `api_startup_status`<br>POST backend/app/api/web_api.py:2692 `api_update_startup` |
| /auth/profile | GET backend/app/api/chat_api.py:883 `auth_profile`<br>POST backend/app/api/chat_api.py:889 `auth_update_profile` |
| /chat/sessions | GET backend/app/api/web_api.py:3048 `get_sessions`<br>POST backend/app/api/web_api.py:3054 `create_session` |
| /chat/settings | GET backend/app/api/web_api.py:3019 `get_chat_settings`<br>POST backend/app/api/web_api.py:3025 `update_chat_settings` |
| /goals | GET backend/app/api/chat_api.py:1328 `get_runtime_goals`<br>POST backend/app/api/chat_api.py:1337 `create_runtime_goal` |
| /workflows | GET backend/app/api/chat_api.py:1459 `get_workflows`<br>POST backend/app/api/chat_api.py:1467 `create_workflow_api` |

## Largest Files

| File | Lines |
| --- | --- |
| backend/app/core/command_router.py | 6441 |
| backend/app/api/web_api.py | 3607 |
| backend/app/core/intent_router.py | 2136 |
| backend/app/api/chat_api.py | 2000 |
| backend/app/features/automation/messaging_automation_module.py | 1427 |
| backend/app/features/voice/speak.py | 1277 |
| backend/app/features/system/system_module.py | 1208 |
| backend/app/features/productivity/task_module.py | 1182 |
| backend/app/features/productivity/nextgen_module.py | 1035 |
| backend/app/shared/device_manager.py | 1030 |
| backend/app/core/assistant.py | 991 |
| backend/app/features/voice/listen.py | 976 |
| backend/app/shared/brain/memory_engine.py | 909 |
| backend/app/features/integrations/google_contacts_module.py | 837 |
| backend/app/features/automation/notification_module.py | 791 |
| backend/app/features/system/window_context_module.py | 785 |
| backend/app/features/intelligence/browser_automation_module.py | 721 |
| backend/app/features/vision/screen_reader.py | 694 |
| backend/app/shared/iot_registry.py | 694 |
| backend/app/shared/brain/ai_engine.py | 673 |
