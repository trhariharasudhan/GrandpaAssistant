# LLM Provider Audit

Phase 4 backend-only provider consolidation audit. This phase introduces a unified abstraction and adapters, but keeps old modules and public call paths in place.

## Provider Inventory

| Provider Module | Used By | Features | Streaming | Memory Support | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `backend/app/core/llm/base.py` | New unified layer | `LLMRequest`, `LLMResponse`, `LLMProvider` protocol | Interface only | Prompt/history fields | COMPLETE | New canonical contract for text LLM calls. |
| `backend/app/core/llm/registry.py` | `provider_manager.py`, tests | Provider factory lookup, health cache | N/A | N/A | COMPLETE | Keeps provider construction lazy so env/config changes are read at request time. |
| `backend/app/core/llm/provider_manager.py` | `shared/llm_client.py`, tests | Env/config provider lookup, fallback chain, health/model info | Delegates provider streams | Passes prompt/history/system prompt | COMPLETE | Current fallback chain: OpenAI/Gemini -> Ollama; fallback provider for explicit local rules. |
| `backend/app/core/llm/providers/openai_provider.py` | Provider manager, terminal adapter | OpenAI chat completions, env config, model metadata | Yes | Message history | COMPLETE | Adapter target for old terminal OpenAI provider and desktop `llm_client`. |
| `backend/app/core/llm/providers/gemini_provider.py` | Provider manager, terminal adapter | Gemini generateContent, env config, model metadata | Partial | Prompt/system prompt | PARTIAL | Streaming interface yields full generated result because current Gemini wrapper was non-streaming. |
| `backend/app/core/llm/providers/ollama_provider.py` | Provider manager, terminal adapter | Ollama `/api/generate`, env config, model metadata | Yes | Prompt-formatted history | COMPLETE | Preserves `OLLAMA_REQUEST_TIMEOUT_SECONDS` behavior used by tests and desktop chat. |
| `backend/app/core/llm/providers/fallback_provider.py` | Provider manager, terminal adapter | Local rule fallback | Yes, single chunk | Prompt only | COMPLETE | Keeps terminal fallback text stable. |
| `backend/app/core/chatbot/providers/*.py` | Terminal chatbot engine and CLI | Legacy provider classes | No public stream API | Prompt built by terminal chatbot | PARTIAL | Now adapter wrappers over `core.llm`; old public `ProviderResult` remains unchanged. |
| `backend/app/shared/llm_client.py` | `api/web_api.py`, `api/chat_api.py`, `core/chat_service.py`, tests | Desktop chat API client, local knowledge short-circuit, OpenAI/Ollama selection, constants | Yes | History and system prompt | PARTIAL | Public functions now delegate generation/streaming/status through `core.llm`; old private helpers remain for compatibility during migration. |
| `backend/app/shared/brain/ai_engine.py` | `core/command_router.py`, web/browser intelligence modules | Offline/local conversation engine, command assistant AI calls, local fallback | Callback-style streaming | Internal conversation history | PARTIAL | Phase 5 routes Ollama generation/streaming through `LLMProviderManager` while preserving public function names and fallback text. |
| `backend/app/shared/offline_multi_model.py` | `api/chat_api.py`, `agents/catalog.py` | Ollama status and offline model mode metadata | No | N/A | PARTIAL | Phase 5 uses unified registry health checks for Ollama status while preserving status return shape. |
| `backend/app/shared/ai_router.py` | Backend shared decision logic | Chooses local/cloud route based on capability | No direct streaming | N/A | PARTIAL | Should later consume provider registry health instead of separate Ollama checks. |
| `backend/app/features/vision/vision_models.py` | Vision/screen understanding | OpenAI/Gemini/Ollama/Claude vision providers | No | Image prompt only | PARTIAL | Multimodal provider family; intentionally not merged into text LLM abstraction yet. |
| `backend/app/core/chatbot/prompt_builder.py` | Terminal chatbot engine | Terminal system prompt with memory/history injection | N/A | Terminal chat memory | DUPLICATE | Different style from desktop API prompt builders. |
| `backend/app/api/web_api.py` | Desktop backend API | Effective system prompt, semantic/mood/emotion/intelligence context | Uses `stream_chat_reply` | Semantic memory, mood memory, command context | DUPLICATE | Prompt construction remains route-owned in Phase 4. |
| `backend/app/api/chat_api.py` | Alternate chat API app | Hardware-aware prompt, semantic/direct memory context | Uses `stream_chat_reply` | Direct memory, semantic memory, mood memory | DUPLICATE | Kept unchanged because `web_api.py` remains active desktop owner. |

## Duplicated Logic Identified

- Provider request code existed in terminal chatbot providers and `shared/llm_client.py`.
- Fallback response text existed separately in terminal fallback provider and desktop API fallback behavior.
- OpenAI/Ollama model/env resolution existed in `llm_client.py`, terminal config, and startup/status checks.
- Prompt building is still split across terminal chatbot, `web_api.py`, `chat_api.py`, and `brain/ai_engine.py`.
- Streaming existed only in `llm_client.py` and route layers; terminal providers were non-streaming.
- Memory injection differs by caller: terminal SQLite chat memory, semantic memory, mood memory, direct memory, and `brain/ai_engine.py` conversation history.

## Phase 4 Consolidation

Added `backend/app/core/llm` as the canonical text-provider layer:

- `generate()`
- `stream_generate()`
- `health_check()`
- `model_info()`

Adapter decisions:

- Terminal chatbot provider classes now call unified provider classes internally.
- `shared/llm_client.py` now delegates generation, streaming, and model metadata to `LLMProviderManager`.
- Old provider modules remain in place.
- Old `llm_client` constants and public functions remain in place.
- Prompt builders and memory injection stay caller-owned for now.

## Migration-Safe Status

Status: PARTIAL but migration-safe.

Runtime entry points remain:

- `python backend\desktop_backend_entry.py`
- `python -m backend.app.cli.chat`

No old provider modules were removed.

## Phase 5 AI Engine Integration

Phase 5 migrated the command-router AI engine boundary without rewriting command-router call sites:

- `brain.ai_engine.ask_ollama()` now uses `LLMProviderManager` for Ollama generation and streaming.
- `brain.ai_engine` still owns conversation history, prompt composition, local knowledge short-circuiting, humanization, and offline/local fallback responses.
- `offline_multi_model.get_ollama_status()` now reports Ollama status through the unified registry health path.
- `llm_client.get_llm_status()` includes unified provider health details.
- Focused tests cover provider-manager generation, provider failure fallback, registry health status, and command-router AI paths.

Remaining duplicated work:

- Web/API prompt construction is still separate from terminal and `brain.ai_engine` prompt wrappers.
- `ai_router.py` still has route decision logic that can later consume registry health more directly.
- Vision providers remain a separate multimodal provider family.

Phase 6 update: `backend/app/core/prompts` now provides the shared prompt boundary used by terminal chatbot and `brain.ai_engine` wrappers. Web/API prompt assembly remains route-owned until route-specific behavior tests are added.

## Phase 8 Status Surface Consolidation

Phase 8 adds `backend/app/core/llm/status.py` as the canonical provider/model health reporting boundary.

| Status Caller | Previous Source | Current Source | Status | Notes |
| --- | --- | --- | --- | --- |
| `shared/llm_client.get_llm_status()` | Local env/model logic plus manager health | `core.llm.status` wrappers | COMPLETE | Keeps old keys and adds provider/model summaries. |
| `shared/offline_multi_model.get_ollama_status()` | Direct registry health check | `get_provider_status("ollama")` | COMPLETE | Keeps `ok`, `provider`, `model`, `base_url`, and `installed_models`. |
| `shared/startup_diagnostics._ollama_status()` | Direct `requests.get(/api/tags)` | `get_provider_status("ollama")` | COMPLETE | Diagnostics now read the same Ollama status surface. |
| Terminal `/provider`, `/model`, `/config` | Terminal provider instance only | `ChatbotEngine.provider_status()` over `core.llm.status` | COMPLETE | Output wording is preserved; `/config` includes status metadata. |
| `api/web_api.py` chat settings | `get_llm_status()` | Compatibility wrapper over `core.llm.status` | COMPLETE | Route response shape is preserved. |
| `api/chat_api.py` health/status | `get_ollama_status()` | Compatibility wrapper over `core.llm.status` | COMPLETE | Route response shape is preserved. |

Remaining provider/status duplication is mostly naming compatibility. Old functions should stay until API ownership cleanup decides which route surfaces are public and which are internal.

## Phase 9 Endpoint Ownership

Provider/status endpoint ownership is documented in `docs/STATUS_ENDPOINT_OWNERSHIP.md`.

- `web_api.py` remains the active desktop owner for `/api/health`, `/api/doctor`, `/api/backend/stability`, active desktop domain status routes, and `/chat/settings` provider/model settings.
- `chat_api.py` remains the alternate runtime owner for `/health`, `/doctor`, `/status`, `/models`, and alternate domain status routes.
- `core.llm.status` remains the shared provider/model status source.
- No provider/status route moved in Phase 9.
