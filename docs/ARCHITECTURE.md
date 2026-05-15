# GrandpaAssistant Backend Architecture

GrandpaAssistant is currently a backend-only Windows assistant. The primary runtime path is:

```text
python backend\desktop_backend_entry.py
```

That entrypoint adds backend/app/shared/features paths to `sys.path`, initializes `app.api.web_api`, and starts uvicorn on `127.0.0.1:8765` unless environment variables override host or port.

## Top-Level Layout

```text
GrandpaAssistant/
|-- backend/    Active Python backend runtime, API, assistant logic, assets, local knowledge
|-- docs/       Architecture, audit, setup, release, validation, and operational notes
|-- plugins/    Local plugin examples
|-- runtime/    Local generated runtime state, logs, cache, models, artifacts
|-- scripts/    Development smoke checks and Windows helper scripts
|-- tests/      Backend unittest suite
|-- main.py     Thin root launcher/helper
```

## Backend Layout

```text
backend/
|-- desktop_backend_entry.py   Active Windows/backend API entrypoint
|-- desktop_backend_boot.py    Boot helper
|-- fastapi_chat.py            Chat API entry helper
|-- main.py                    Backend assistant launcher
|-- app/
|   |-- api/                   FastAPI surfaces
|   |-- cli/                   Terminal chatbot CLI
|   |-- config/                Terminal chat config and backend config helpers
|   |-- core/                  Assistant loop, command router, chatbot engine
|   |-- features/              Voice, vision, system, productivity, automation, integrations
|   |-- security/              Runtime security/auth/permission modules
|   |-- services/              Service-style helpers, currently local action executor source
|   |-- shared/                Shared memory, LLM, config, paths, debug, IoT, screen/window helpers
|   |-- agents/                Agent runtime/catalog/message bus/state store
|-- assets/                    Sounds, model assets, safe example credential templates
|-- data/knowledge/            Checked-in local knowledge seed files
```

## Runtime Entry Points

| Entry | Status | Purpose |
| --- | --- | --- |
| `python backend\desktop_backend_entry.py` | COMPLETE | Primary backend API runtime. Must remain runnable. |
| `python backend\fastapi_chat.py` | PARTIAL | Chat API entrypoint. Useful but overlaps with `web_api.py`. |
| `python -m backend.app.cli.chat` | COMPLETE | Terminal-only chatbot. No frontend, mobile, browser page, or UI dependency. |
| `scripts\windows\start_assistant_console.cmd` | COMPLETE | Windows helper for starting the assistant. |
| `scripts\dev\startup_smoke_check.py` | COMPLETE | Launches backend and verifies readiness/shutdown. |

## API Architecture

`backend/app/api/web_api.py` is the primary desktop backend API surface. It includes health, backend stability, command execution, debug assistant, screen/window context, contacts, phone link readiness, local actions, UI analysis, auth, memory, voice status/control, startup settings, mobile companion backend routes, and chat routes.

`backend/app/api/chat_api.py` is a second FastAPI surface with health/doctor, auth, devices, settings, voice setup, IoT, status/security, runtime, agents, goals, plugins, intelligence/learning, memory, workflows, mood, ask, chat history, chat, and streaming routes.

Status: DUPLICATE. Both files are legitimate backend code, but there is no single route ownership document yet. Do not remove or merge either file until supported runtime contracts are explicitly chosen.

## Chat Architecture

There are two chat stacks:

1. Terminal chatbot stack: `backend/app/core/chatbot/`
   - CLI: `backend/app/cli/chat.py`
   - Engine: `backend/app/core/chatbot/engine.py`
   - Providers: OpenAI, Gemini, Ollama, fallback
   - Memory: `backend/app/core/chatbot/memory.py`
   - Config: `backend/app/config/terminal_chat.json` plus environment variables

2. Web/API chat stack:
   - Service: `backend/app/core/chat_service.py`
   - Provider helper: `backend/app/shared/llm_client.py`
   - Local knowledge: `backend/app/shared/local_knowledge.py`
   - Routes: `backend/app/api/web_api.py` and `backend/app/api/chat_api.py`

Status: PARTIAL/DUPLICATE. Both stacks work for their paths, but provider and memory behavior are split.

Phase 4 introduced `backend/app/core/llm` as the unified text LLM provider layer. Phase 5 connected `backend/app/shared/brain/ai_engine.py`, `backend/app/shared/llm_client.py`, and Ollama provider health/status checks to that layer through adapters. Public command-router and chatbot entry points still call the same functions, so this is an integration step rather than a route or UX rewrite.

Phase 6 introduced `backend/app/core/prompts` as the shared prompt-building boundary. Terminal chatbot prompts and `brain.ai_engine` prompts now use the shared builder through wrappers. Phase 7 added route prompt adapters so desktop `web_api.py` and alternate `chat_api.py` keep their helper names and route behavior while delegating prompt assembly to `core.prompts.route_adapters`.

Phase 8 introduced `backend/app/core/llm/status.py` as the shared provider/model status surface. `llm_client`, `offline_multi_model`, startup diagnostics, terminal chatbot status commands, and web/chat API status payloads now read provider health and model metadata from the same registry-backed helpers while preserving old wrapper names and response keys.

## Memory And Data Architecture

| Store | Status | Path | Purpose |
| --- | --- | --- | --- |
| Assistant memory DB | COMPLETE | runtime data via `backend/app/shared/brain/database.py` | Encrypted memory entries and command history in SQLite. |
| Productivity state | COMPLETE | `assistant_state_kv` in assistant DB | Tasks, notes, events, user preferences, chat state scopes. |
| Terminal chat DB | COMPLETE | `runtime/data/grandpa_chat.db` | Terminal sessions, messages, user memories, app events. |
| Local knowledge JSON | COMPLETE | `backend/data/knowledge/*.json` | Seed knowledge for math, science, and Thirukkural. |
| Review queue | PARTIAL | ignored runtime/data knowledge queue path | Captures safe unknown factual questions for later review. |
| Legacy JSON memory | PARTIAL | legacy paths under runtime data | Migration support remains for backward compatibility. |

## Command Flow

For the desktop assistant, command flow centers on `backend/app/core/command_router.py`.

```text
voice/text input
  -> assistant loop or API command route
  -> command_router.process_command(...)
  -> feature modules, shared helpers, local actions, chat fallback, or debug tools
  -> speak/log/API response
```

Status: PARTIAL. The router is capable and tested, but it is very large and mixes command parsing, confirmation state, feature dispatch, debug tools, and integration calls.

Phase 10 added `docs/COMMAND_ROUTER_AUDIT.md`, `docs/COMMAND_ROUTER_SPLIT_PLAN.md`, and `tests/test_command_router_groups.py` as preparation for decomposition. No router logic was moved. The safest first future split is a low-risk knowledge/local-intent handler while keeping `process_command(...)` as the public entrypoint.

Phase 11 performed that first narrow extraction: `backend/app/core/commands/handlers/knowledge.py` now handles basic greetings, simple reply phrases, period greetings, jokes, and Wikipedia-style factual prefixes through injected dependencies. `process_command(...)` remains the public entrypoint and still owns safety, system actions, UI automation, IoT, contacts, broad intent routing, and AI fallback.

Phase 12 added `backend/app/core/commands/handlers/memory.py` for the low-risk personal-name and semantic-memory read-only paths. Destructive memory actions, memory edit commands, personal-question fallback, and AI fallback remain in `command_router.py`.

Phase 13 added `backend/app/core/commands/handlers/diagnostics.py` for read-only security status, voice diagnostics, assistant doctor, and backend stability summaries. Security actions, voice setup/auth actions, debug/fix workflows, system controls, and AI fallback remain in `command_router.py`.

Phase 14 added `backend/app/core/commands/handlers/debug.py` for read-only current debug session, debug dashboard, fix approvals, and fix audit summaries. Debug session mutation, fix plan creation, fix approval execution/dismissal, system controls, and AI fallback remain in `command_router.py`.

Phase 15 extended the debug handler for read-only debug timeline/history, debug session search summaries, reuse suggestions, debug learning summaries, and debug checklist summaries. Debug session lifecycle/export, debug report generation, fix plan/application/approval mutation, and AI fallback remain in `command_router.py`.

Phase 16 added `backend/app/core/commands/context.py` and `backend/app/core/commands/registry.py`. Extracted handlers now share a `CommandContext`, and `command_router.py` invokes them through ordered registries at the existing dispatch points. No additional command groups moved.

Phase 17 added `backend/app/core/commands/handlers/status.py` for read-only voice/offline/backend status summaries. Settings writes, voice setup actions, auth/security mutations, system actions, and AI fallback remain in `command_router.py`.

Phase 18 added `backend/app/core/commands/handlers/productivity.py` for read-only planner focus, reminder timeline, habit/goal dashboard, smart reminder priority, automation history, and mobile companion status summaries. Reminder/task mutations, habit/goal mutations, automation execution/configuration, mobile actions, IoT/system/safety logic, and AI fallback remain in `command_router.py`.

Phase 19 added `backend/app/core/commands/handlers/knowledge_services.py` for read-only language mode, meeting summary, RAG library, proactive suggestion, knowledge review queue, and learning status summaries. Language changes, meeting capture/recording, RAG indexing, knowledge writes, proactive refresh/notification execution, and AI fallback remain in `command_router.py`.

Phase 20 added `backend/app/core/commands/handlers/device_status.py` for read-only phone link readiness, face/security enrollment status, startup auto-launch status, and smart-home setup/help summaries. Enrollment, verification, auth, startup mutations, IoT controls, camera/microphone/OCR/object detection actions, system controls, and AI fallback remain in `command_router.py`.

Phase 21 added `backend/app/core/commands/handlers/awareness.py` for read-only active-window summaries. Screenshot/OCR capture, screen explanation, visible text summarization, context suggestions, object detection, UI actions, system controls, and AI fallback remain in `command_router.py`.

Phase 22 added `backend/app/core/commands/handlers/contacts.py` for read-only local contact list/find commands and Google contact list/change/favorite/alias summaries. Calls, messages, emails, contact edits/deletes, Google sync/refresh/merge/import, confirmation flows, field lookups that force refresh, system controls, and AI fallback remain in `command_router.py`.

Phase 23 updated `backend/app/core/commands/registry.py` with a named read-only registry builder. `command_router.py` still owns dispatch placement, but uses named registry groups instead of repeated one-off registry construction. No command behavior moved in this phase.

Phase 24 added `backend/app/core/commands/handlers/planning.py` for read-only Google Calendar status/listing summaries and local calendar/date query summaries. Google Calendar sync and event mutations, generic agenda intent routing, weather lookup, reminders/tasks mutations, notifications, AI day planning, and AI fallback remain in `command_router.py`.

Phase 25 added `backend/app/core/commands/handlers/project_knowledge.py` for read-only RAG library, knowledge review queue, storage report, and storage cleanup suggestion summaries. Knowledge writes, review clearing, document tag/move operations, project/file indexing, document Q&A/search, file mutation, embedding/vector DB writes, and AI fallback remain in `command_router.py` or their existing intent/API owners.

Phase 26 added `backend/app/core/commands/handlers/system_health.py` for read-only system, CPU, RAM, disk, exact battery, hardware status, and hardware event summaries. Broad battery fallback, storage cleanup/status, scans/rescans, settings changes, startup changes, system power actions, app/window actions, hardware capture/control, and AI fallback remain with their existing owners.

Phase 27 added `backend/app/core/commands/handlers/iot_status.py` for read-only smart-home status, IoT inventory, smart-home history, and setup/readiness help summaries. IoT control dispatch, confirmation-backed device actions, live validation/connectivity checks, pairing/connect flows, config mutations, system actions, and AI fallback remain with their existing owners.

Phase 28 added `backend/app/core/commands/handlers/security_status.py` for read-only security status, security alerts/logs, voice authentication status, security admin status, and admin-permission status summaries. Authentication, lock/unlock, lockdown, device trust, security admin changes, PIN changes, emergency actions, permission/security setting mutations, log clearing/deletion, system actions, and AI fallback remain with their existing owners.

Phase 29 added `backend/app/core/commands/handlers/emergency_status.py` for read-only emergency mode/help, quick-response help, and emergency protocol information summaries. Protocol triggers, alert/SOS sending, safe-alert sending, location sharing, emergency contact calls/messages, lockdown/lock/unlock, emergency setting changes, log clearing/deletion, system actions, and AI fallback remain with their existing owners.

Phase 30 added `backend/app/core/commands/handlers/profile_status.py` for read-only profile summary, personal snapshot, preferred language, and preferred tone summaries. Preference updates, profile edits, memory saves/deletes/clears, persona changes, config/database writes, and AI fallback remain with their existing owners.

Phase 31 added `backend/app/core/commands/handlers/developer_status.py` for read-only developer mode, workspace/coding, git status, branch, remotes, recent commits, and repository summaries. Terminal launch, save/run flows, git mutations, file writes/edits, script execution, app launch, developer setting changes, and AI fallback remain with their existing owners.

Phase 32 added `backend/app/core/commands/handlers/notification_status.py` for read-only notification status/help, popup/alert status, reminder/event notification status, and notification history/list summaries. Notification sending, popup display, reminder/task mutations, enable/disable flows, setting changes, and AI fallback remain with their existing owners.

Phase 33 added `backend/app/core/commands/handlers/audio_status.py` for read-only sound status, audio status, chime status, notification sound summaries, and voice audio readiness. Playback, sound/chime setting changes, voice start/stop, microphone capture, TTS playback, and AI fallback remain with their existing owners.

Phase 34 added `backend/app/core/commands/handlers/overlay_status.py` for read-only overlay status, quick overlay status, pinned command list/summary, hotkey status, and overlay help. Pin/unpin/move actions, overlay enable/disable/toggle, hotkey changes, overlay open/close/hide/show, UI actions, and AI fallback remain with their existing owners.

Phase 35 added `backend/app/core/commands/handlers/interface_status.py` for read-only startup status, auto-launch status, tray mode status, interface/terminal mode status, desktop/backend mode summaries, and launcher/readiness status. Startup changes, tray/interface mode writes, UI launch/open commands, app/window launches, settings writes, and AI fallback remain with their existing owners.

Phase 36 added `backend/app/core/commands/handlers/config_status.py` for read-only config status, settings status, assistant settings summary, environment/config readiness, and feature toggle summaries. Settings mutations, feature enable/disable commands, admin/escalation flows, API key/config writes, security setting changes, and AI fallback remain with their existing owners.

## Feature Domains

| Domain | Status | Main files |
| --- | --- | --- |
| Voice | PARTIAL | `features/voice/listen.py`, `features/voice/speak.py` |
| Vision/OCR | PARTIAL | `features/vision/screen_reader.py`, `shared/screen_awareness.py` |
| UI analysis | PARTIAL | `features/ui_analysis/*` |
| Productivity | COMPLETE | `features/productivity/*`, `shared/productivity_store.py` |
| System controls | PARTIAL | `features/system/*`, `shared/controls/*` |
| Automation | PARTIAL | `features/automation/*`, `services/local_action_executor.py` |
| Integrations | PARTIAL | `features/integrations/*`, `integrations/n8n_client.py` |
| Security/auth | PARTIAL | `app/security/*`, `shared/app_auth.py`, auth routes |
| Debug assistant | COMPLETE | `shared/debug_*`, `docs/DEBUG_ASSISTANT_GUIDE.md` |
| Agents/cognition | PARTIAL | `app/agents/*`, `shared/cognition/*` |

## Compatibility And Legacy Layers

`backend/app/features/modules/` is an intentional compatibility alias layer for old imports like `from modules.task_module import ...`. Each file forwards to a real domain module. Status: DUPLICATE, but intentional.

Several directories contain compiled pycache artifacts without matching source in this checkout, especially under `backend/app/brain`, `backend/app/services/integrations`, `backend/app/services/iot`, `backend/app/services/llm`, and `backend/app/core/knowledge_engine`. Status: DUPLICATE/PARTIAL artifact shape. Do not delete in this documentation pass.

## Runtime Data Policy

Runtime data should live under `runtime/` or ignored backend data paths. Secret-bearing files such as `backend/data/app_auth_secret.txt`, `backend/data/*.secret`, token files, and credential files are ignored.

Checked-in files under `backend/data/knowledge/` are seed knowledge, not local secrets.

## Test Architecture

Tests are standard unittest files under `tests/`. Current coverage focuses on backend behavior, route protection, command safety, optional dependency guards, terminal chat, productivity persistence, local knowledge, screen/window awareness, UI analysis, debug assistant, contacts/calling, n8n, and backend startup checks.
