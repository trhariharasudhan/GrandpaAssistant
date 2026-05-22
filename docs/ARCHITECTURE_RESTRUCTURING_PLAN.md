# GrandpaAssistant Architecture Restructuring Plan

This document is the migration control file for restructuring GrandpaAssistant without breaking runtime compatibility.

## 1. Current Architecture Analysis

GrandpaAssistant is currently a backend-only Windows-first Python project. The active runtime path is `python backend\desktop_backend_entry.py`, with root `main.py` and `backend\main.py` preserved as launcher paths for console/assistant mode.

```text
GrandpaAssistant/
|-- backend/
|   |-- desktop_backend_entry.py
|   |-- desktop_backend_boot.py
|   |-- fastapi_chat.py
|   |-- main.py
|   |-- app/
|   |   |-- api/
|   |   |-- core/
|   |   |-- features/
|   |   |-- shared/
|   |   |-- services/
|   |   |-- security/
|   |   |-- integrations/
|   |   |-- agents/
|   |   |-- project_knowledge/
|   |   |-- browser_automation/
|   |   |-- visual_desktop/
|   |   |-- prompts/
|   |   |-- config/
|   |-- assets/
|   |-- data/
|-- docs/
|-- plugins/
|-- scripts/
|-- tests/
|-- runtime/
|-- reference/
|-- main.py
```

There is no active frontend workspace in this checkout. The README explicitly treats the project as backend-only.

## 2. Problems Found

| Area | Finding | Risk |
| --- | --- | --- |
| API layer | `backend/app/api/web_api.py` is primary but large; `chat_api.py` is a separate alternate FastAPI app with overlapping routes. | Route drift, duplicated auth/chat behavior. |
| Command routing | `core/command_router.py` is over 5,500 lines with 150+ functions. | High coupling, hard test isolation, slow feature changes. |
| Intent routing | `core/intent_router.py` is over 2,000 lines. | Mixed natural-language parsing and domain dispatch. |
| Feature modules | `features/modules/` is a compatibility shim package while real code lives in domain folders. | Easy to accidentally add new logic in legacy location. |
| Browser automation | Two stacks exist: `app/browser_automation/` and `app/services/browser_automation/`. | Confusing ownership; duplicated concepts. |
| LLM providers | `core/chatbot/providers`, `core/llm/providers`, and `shared/llm_client.py` overlap. | Provider behavior can diverge by entrypoint. |
| Memory/data | Memory is split across `shared/brain`, productivity store, terminal chat DB, and runtime JSON/SQLite files. | Migration needs schema ownership and backup rules. |
| Imports | Runtime relies on `sys.path` insertion for `backend/app`, `shared`, and `features`. | Moving files without shims can break legacy imports. |
| Config | Runtime config is mostly under `runtime/config`, but code config lives under `backend/app/config`. | Naming ambiguity between code config and user runtime config. |
| Tests | Tests are broad but use path insertion; local environments currently lack `pytest`. | Validation depends on `unittest` and custom scripts unless dev deps are installed. |
| Generated/reference | `runtime/` and `reference/` are intentionally ignored. | Must stay out of runtime imports and packaging. |

Largest files currently needing phased extraction:

| File | Approx lines | Target strategy |
| --- | ---: | --- |
| `backend/app/core/command_router.py` | 5,500+ | Extract command domains into `core/commands/handlers/`. |
| `backend/app/api/web_api.py` | 3,100+ | Convert endpoint groups to routers under `api/routes/`. |
| `backend/app/core/intent_router.py` | 2,100+ | Split parser, classifiers, and dispatch tables. |
| `backend/app/api/chat_api.py` | 1,700+ | Freeze as compatibility app, route new work through `web_api`. |
| `features/automation/messaging_automation_module.py` | 1,100+ | Split channels, schedulers, contacts, and templates. |
| `features/voice/speak.py` | 1,000+ | Split engine adapters, queue/state, and formatting. |
| `features/system/system_module.py` | 1,000+ | Split OS controls, power/session, app launch, and status. |

## 3. Proposed Production Architecture

Target structure:

```text
GrandpaAssistant/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |   |-- main.py
|   |   |   |-- routes/
|   |   |   |-- dependencies/
|   |   |   |-- middleware/
|   |   |   |-- schemas/
|   |   |-- core/
|   |   |   |-- runtime/
|   |   |   |-- commands/
|   |   |   |-- planning/
|   |   |   |-- prompts/
|   |   |-- services/
|   |   |   |-- browser_automation/
|   |   |   |-- local_actions/
|   |   |   |-- visual_desktop/
|   |   |-- features/
|   |   |   |-- automation/
|   |   |   |-- productivity/
|   |   |   |-- system/
|   |   |   |-- voice/
|   |   |   |-- vision/
|   |   |   |-- integrations/
|   |   |-- ai/
|   |   |   |-- llm/
|   |   |   |-- providers/
|   |   |   |-- rag/
|   |   |-- memory/
|   |   |   |-- repositories/
|   |   |   |-- semantic/
|   |   |   |-- stores/
|   |   |-- models/
|   |   |-- schemas/
|   |   |-- repositories/
|   |   |-- integrations/
|   |   |-- automation/
|   |   |-- plugins/
|   |   |-- utils/
|   |   |-- compat/
|   |-- configs/
|   |-- assets/
|   |-- scripts/
|-- configs/
|-- docs/
|-- scripts/
|-- tests/
|-- runtime/
```

Compatibility rule: old import paths stay in place as shims until all tests, scripts, docs, and packaged entrypoints use the new paths.

## 4. File Move Plan

Phase A moves are documentation/runtime-neutral only.

| Before | After | Why | Dependency impact |
| --- | --- | --- | --- |
| `structure.txt` | `docs/inventory/STRUCTURE_SNAPSHOT.txt` | Root should contain launch/config files only; inventory belongs under docs. | No runtime references found. |

Phase B should split API routes without changing route behavior.

| Before | After | Why | Dependency impact |
| --- | --- | --- | --- |
| `backend/app/api/web_api.py` health/debug/contact/auth/voice/mobile/chat sections | `backend/app/api/routes/*.py` included by `web_api.py` | Shrinks primary API and makes route ownership explicit. | Keep `web_api.app` and route paths unchanged. |
| `backend/app/api/chat_api.py` | `backend/app/api/compat/chat_api.py` plus shim at old path | Mark as alternate compatibility API. | `backend/fastapi_chat.py` keeps old import until shim proven. |

Phase C should split command and intent routing.

| Before | After | Why | Dependency impact |
| --- | --- | --- | --- |
| Large blocks in `core/command_router.py` | `core/commands/handlers/<domain>.py` | Reduces central dispatcher risk. | Existing `process_command` remains public facade. |
| Large classifiers in `core/intent_router.py` | `core/intents/` | Separates parsing from execution. | Keep old import path as facade. |

Phase D should consolidate duplicate feature stacks.

| Before | After | Why | Dependency impact |
| --- | --- | --- | --- |
| `backend/app/browser_automation/*` and `backend/app/services/browser_automation/*` | one canonical `services/browser_automation/` with old-package shims | One service owner. | Preserve `browser_automation.*` imports until tests migrate. |
| `features/modules/*` | `compat/features/modules/*` with old package retained as shim | Make legacy status obvious. | Do not remove old path before deprecation criteria pass. |

Phase E should normalize data and provider boundaries.

| Before | After | Why | Dependency impact |
| --- | --- | --- | --- |
| `shared/brain/*`, terminal memory, productivity store | `memory/repositories` and `memory/stores` facades | Dedicated memory ownership. | Needs DB backup and migration tests. |
| `core/chatbot/providers`, `core/llm/providers`, `shared/llm_client.py` | `ai/llm/providers` with compatibility facades | One provider registry. | High risk; defer until contract tests cover all entrypoints. |

## 5. Safe Migration Strategy

1. Keep entrypoints unchanged: `main.py`, `backend/main.py`, `backend/desktop_backend_entry.py`, and `backend/fastapi_chat.py`.
2. Add new packages first, then move internals behind compatibility shims.
3. Migrate tests and scripts before removing old imports.
4. For route modules, assert route counts and duplicate paths before and after each extraction.
5. For memory/provider moves, add repository/provider contract tests before moving code.
6. Preserve `runtime/`, `.env`, and user databases; never move runtime data as part of source restructuring.

## 6. Risks And Compatibility Notes

- `sys.path` insertion means top-level imports such as `from utils.paths import ...` are valid today. A packaging-style restructure must provide facades before changing imports.
- `features/modules` is intentionally a shim package. Removing it now would violate the documented deprecation plan.
- `chat_api.py` is duplicate-looking but still an alternate app imported by `backend/fastapi_chat.py`; do not delete it.
- `runtime/data` contains user state and must be treated as mutable local data, not source.
- `reference/system_prompts_leaks` is ignored research material and must not become a runtime dependency.

## 7. Validation Checklist

Run after every migration slice:

```powershell
.\.python311\python.exe scripts\dev\repo_structure_audit.py --json
.\.python311\python.exe scripts\dev\full_backend_validation.py
.\.python311\python.exe -m compileall -q backend tests scripts main.py
git status --short --branch
```

If `pytest` is added later, run:

```powershell
.\.python311\python.exe -m pytest
```

## 8. Execution Log

### Phase 2A: Health Route Extraction

Moved primary desktop health/status endpoints out of `backend/app/api/web_api.py` and into `backend/app/api/routes/health.py`.

| Endpoint | Method | New owner |
| --- | --- | --- |
| `/api/health` | GET | `backend/app/api/routes/health.py` |
| `/api/doctor` | GET | `backend/app/api/routes/health.py` |
| `/api/backend/stability` | GET | `backend/app/api/routes/health.py` |

Compatibility notes:

- `web_api.app` remains the only active desktop FastAPI app.
- Public URLs and response payloads are unchanged.
- The route module is registered through `app.include_router(create_health_router(globals()))`.
- The router reads dependencies dynamically from `web_api` globals so existing tests and runtime patches against `api.web_api` continue to work.
- No `chat_api.py` alternate runtime routes were changed.

Validation:

```powershell
.\.python311\python.exe -m unittest tests.test_web_api_routes tests.test_backend_stability_api tests.test_status_endpoint_ownership -v
.\.python311\python.exe -m compileall -q backend tests scripts main.py
.\.python311\python.exe scripts\dev\startup_smoke_check.py
.\.python311\python.exe scripts\dev\full_backend_validation.py
```

Result: all passed. Optional dependency readiness still reports hardware/model warnings unrelated to the route extraction.

### Phase 2B: Chat Route Extraction Prep

Audited the active desktop chat route group in `backend/app/api/web_api.py`.

Dependency findings:

| Dependency area | Current owner | Extraction note |
| --- | --- | --- |
| `chat_reply(...)` | `web_api.py` | Must stay for now; mobile REST and websocket code call it directly. |
| `chat_stream(...)` | `web_api.py` | Must stay for now; streaming generator captures many local helpers and state. |
| Session state | `web_api.py` globals: `_chat_sessions`, `_session_order` | Safe for basic list/create through dynamic globals; unsafe for delete/rename until more tests are isolated. |
| Model settings | `web_api.py` globals: `_chat_settings`, `_active_chat_model`, `_apply_runtime_chat_settings` | Safe for settings read/update through dynamic globals. |
| Upload/RAG | `web_api.py` helpers: `_extract_document_payload`, `_normalize_documents`, `_build_chat_input` | Keep in place for now. |
| Regenerate | `web_api.py` | Keep in place; depends on tool-aware reply and direct action helpers. |
| Mobile websocket | `web_api.py` | Keep in place; calls `chat_reply(...)` and `api_command(...)` directly. |

Moved the low-risk chat routes to `backend/app/api/routes/chat.py`.

| Endpoint | Method | New owner |
| --- | --- | --- |
| `/chat/settings` | GET | `backend/app/api/routes/chat.py` |
| `/chat/settings` | POST | `backend/app/api/routes/chat.py` |
| `/chat/sessions` | GET | `backend/app/api/routes/chat.py` |
| `/chat/sessions` | POST | `backend/app/api/routes/chat.py` |

Compatibility notes:

- `chat_reply`, `chat_stream`, and `mobile_websocket` remain in `web_api.py`.
- The chat router uses `create_router(web_api_globals)` and dynamic dependency lookup to preserve test patching and runtime globals.
- `web_api` module globals `get_chat_settings`, `update_chat_settings`, `get_sessions`, and `create_session` are assigned by the router factory for backward-compatible callable access.
- `POST /chat/sessions/rename`, `POST /chat/sessions/delete`, history, upload, export, reset, cancel, regenerate, main chat, and stream routes intentionally remain in `web_api.py`.

Validation:

```powershell
.\.python311\python.exe -m compileall -q backend tests scripts main.py
.\.python311\python.exe -m unittest tests.test_web_api_routes tests.test_chat_api_regressions tests.test_chat_api_prompt_behavior tests.test_status_endpoint_ownership -v
.\.python311\python.exe scripts\dev\startup_smoke_check.py
```

Manual route probes confirmed:

- `GET /chat/settings` returns 200.
- `POST /chat/settings` returns 200.
- `GET /chat/sessions` returns 200.
- `POST /chat/sessions` returns 200.
- `POST /chat` still resolves to `api.web_api.chat_reply`.
- `POST /chat/stream` still resolves to `api.web_api.chat_stream`.
- `mobile_websocket` still imports from `api.web_api`.
