# GrandpaAssistant Cleanup Plan

Documentation-only cleanup plan. No files have been moved or deleted by this plan.

## Safety Rules

1. Keep `python backend\desktop_backend_entry.py` runnable.
2. Do not add frontend, mobile, or UI client workspaces.
3. Do not delete backend, docs, scripts, plugins, tests, or runtime-related backend logic without a separate validation step.
4. Do not change imports, route paths, or command behavior during documentation cleanup.
5. Validate after every cleanup phase with:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe scripts\dev\startup_smoke_check.py
```

## Recommended Phases

### Phase 1: Freeze Runtime Contracts

Status: MISSING

Create a route ownership document that declares:

- Primary runtime: `backend/app/api/web_api.py`
- Secondary/alternate runtime: `backend/app/api/chat_api.py`
- Supported entrypoints
- Routes that must remain stable
- Routes that are legacy or internal

Risk: low, documentation-only.

### Phase 2: Inventory Import Paths

Status: MISSING

Generate an import map for:

- `modules.*` compatibility imports
- `brain.*` imports
- `shared.*` imports
- `features.*` imports
- direct `sys.path` assumptions in entrypoints

Risk: low if read-only. This should happen before any file moves.

### Phase 3: Mark Compatibility Shims

Status: PARTIAL

`backend/app/features/modules/README.md` already states the rule: compatibility aliases only. Add this same rule to architecture docs and future contributor notes.

Risk: low.

### Phase 4: Pycache And Generated Artifact Cleanup

Status: PARTIAL

Candidate areas:

- `backend/app/brain/**/__pycache__`
- `backend/app/services/**/__pycache__`
- `backend/app/core/knowledge_engine/**/__pycache__`
- `backend/app/core/math_engine/**/__pycache__`
- `backend/app/core/security/**/__pycache__`
- root and backend `__pycache__`

Do not perform this until confirming:

- Files are untracked.
- `.gitignore` covers `__pycache__/` and `*.pyc`.
- Validation passes before and after cleanup.

Risk: low if untracked compiled artifacts only, but still separate from this audit.

### Phase 5: Provider Consolidation Design

Status: PARTIAL

Current duplication:

- Terminal provider stack: `backend/app/core/chatbot/providers/*`
- Shared web/API provider stack: `backend/app/shared/llm_client.py`
- Command-router AI engine: `backend/app/shared/brain/ai_engine.py`

Completed cleanup:

- Added unified text provider layer under `backend/app/core/llm`.
- Adapted terminal providers and `shared/llm_client.py`.
- Routed `brain.ai_engine.ask_ollama()` through `LLMProviderManager`.
- Routed Ollama status checks through unified provider health.

Remaining work:

- Keep old provider modules until a later removal phase.
- Consolidate prompt-builder boundaries only after behavior tests cover web/API, terminal, and command-router prompts.
- Consider migrating `ai_router.py` to consume provider registry health directly.

Risk: medium once code changes begin.

### Phase 6: Memory Boundary Design

Status: DUPLICATE

Current stores:

- assistant memory SQLite
- terminal chat SQLite
- productivity SQLite scope store
- local knowledge JSON
- legacy JSON migration paths

Recommended next step:

- Document which store owns conversational memory, personal memory, productivity state, knowledge facts, and audit/debug records.
- Avoid merging stores until all tests and migration expectations are clear.

Risk: medium to high if changed without migration tests.

### Phase 7: Prompt Builder Route Migration

Status: COMPLETE

Completed:

- Added shared prompt package: `backend/app/core/prompts`.
- Migrated terminal chatbot prompt wrapper.
- Migrated `brain.ai_engine` prompt wrapper.
- Added prompt behavior tests for language style, memory, history, safety, and code instructions.
- Added route adapters in `backend/app/core/prompts/route_adapters.py`.
- Migrated `web_api.py` and `chat_api.py` prompt helper bodies to route adapters.
- Added behavior tests for active desktop and alternate chat route prompt assembly.

Remaining:

- Keep current reply style and memory/context injection stable.
- Do not remove wrapper helper names until API route consolidation is complete.

Risk: medium because prompts are directly user-visible.

### Phase 8: Provider Status Reporting Consolidation

Status: PARTIAL

Provider/status reporting consolidation is complete as a prerequisite to command-router work:

- Added `backend/app/core/llm/status.py`.
- Migrated `llm_client.get_llm_status()`, `offline_multi_model.get_ollama_status()`, startup diagnostics, and terminal provider/model/config commands through the shared status surface.
- Preserved old route-facing and CLI-facing function names.
- Added tests for fallback, missing cloud keys, unavailable Ollama, old wrappers, route status payloads, and terminal status commands.

Recommended next status cleanup:

- Keep old wrappers until route ownership is settled.
- Add explicit provider/status endpoints only after deciding whether `web_api.py` or `chat_api.py` owns them publicly.

### Phase 9: Provider Status Endpoint Ownership

Status: COMPLETE

Completed:

- Added `docs/STATUS_ENDPOINT_OWNERSHIP.md`.
- Kept `web_api.py` as active desktop status owner.
- Kept `chat_api.py` as alternate runtime status owner.
- Kept provider/model reporting behind `core.llm.status` wrappers.
- Moved no routes.

Risk: low while documentation-only; medium if route ownership changes without client contract tests.

### Phase 10: Command Router Decomposition Plan

Status: PARTIAL

`backend/app/core/command_router.py` is large and central. Do not split it yet.

Safe preparation:

- Group command patterns by feature domain in documentation.
- Add tests for any untested command groups before refactoring.
- Identify commands that are pure dispatch versus commands that hold state.
- COMPLETE: Added `docs/COMMAND_ROUTER_AUDIT.md`.
- COMPLETE: Added `docs/COMMAND_ROUTER_SPLIT_PLAN.md`.
- COMPLETE: Added `tests/test_command_router_groups.py`.

First safe future split:

- Extract only low-risk knowledge/local-intent handling behind a wrapper.
- Keep `process_command(...)` as the entrypoint.
- Leave safety confirmations, Windows actions, UI automation, IoT, contacts, and AI fallback in place until more focused tests exist.

Phase 11 completion:

- Added `backend/app/core/commands/result.py`.
- Added `backend/app/core/commands/handlers/knowledge.py`.
- Routed the old basic greeting/joke/period/Wikipedia-style branch through `handle_knowledge_command(...)`.
- Added `tests/test_command_router_knowledge_handler.py`.
- Kept broad `try_handle_intent(...)`, safety, system actions, UI automation, IoT, contacts, and AI fallback in `command_router.py`.

Phase 12 completion:

- Added `backend/app/core/commands/handlers/memory.py`.
- Routed low-risk personal name save/read commands through `handle_memory_command(...)`.
- Routed semantic memory status/search through `handle_memory_command(...)` while preserving its original dispatch location.
- Added `tests/test_command_router_memory_handler.py`.
- Kept memory edit/delete, `clear memory`, personal-question fallback, and AI fallback in `command_router.py`.

Phase 13 completion:

- Added `backend/app/core/commands/handlers/diagnostics.py`.
- Routed read-only security status, voice diagnostics, assistant doctor, and backend stability summaries through `handle_diagnostics_command(...)`.
- Added `tests/test_command_router_diagnostics_handler.py`.
- Kept security actions, voice setup/auth actions, debug/fix workflows, system actions, and AI fallback in `command_router.py`.

Phase 14 completion:

- Added `backend/app/core/commands/handlers/debug.py`.
- Routed read-only current debug session, debug dashboard, fix approvals summary, and fix audit summary through `handle_debug_command(...)`.
- Added `tests/test_command_router_debug_handler.py`.
- Kept debug session mutation, debug export/search/timeline/reuse/checklist, fix plan creation, fix application, dismiss/approval execution, system actions, and AI fallback in `command_router.py`.

Phase 15 completion:

- Extended `backend/app/core/commands/handlers/debug.py`.
- Routed read-only debug timeline/history, debug search, reuse suggestions, debug learning, and debug checklist summaries through `handle_debug_command(...)`.
- Added `tests/test_command_router_debug_history_handler.py`.
- Kept debug session start/close/export, debug report generation, fix plan/application, approval mutation, system actions, and AI fallback in `command_router.py`.

Phase 16 completion:

- Added `backend/app/core/commands/context.py`.
- Added `backend/app/core/commands/registry.py`.
- Migrated extracted handlers to accept `CommandContext`.
- Kept callback-style handler tests compatible.
- Kept `process_command(...)` as the public entrypoint and moved no new command groups.
- Added `tests/test_command_handler_registry.py`.

Phase 17 completion:

- Added `backend/app/core/commands/handlers/status.py`.
- Routed read-only offline/backend/voice status and setup summaries through `handle_status_command(...)`.
- Added `tests/test_command_router_status_handler.py`.
- Kept settings writes, voice setup actions, auth/security mutations, system actions, and AI fallback in `command_router.py`.

Phase 18 completion:

- Added `backend/app/core/commands/handlers/productivity.py`.
- Routed read-only planner focus, reminder timeline, habit/goal dashboard, smart reminder priority, automation history, and mobile companion status summaries through `handle_productivity_command(...)`.
- Added `tests/test_command_router_productivity_handler.py`.
- Kept reminder/task mutation, habit/goal mutation, AI day planning, automation execution/configuration, mobile setup/send actions, IoT/system/safety paths, and AI fallback in `command_router.py`.

Phase 19 completion:

- Added `backend/app/core/commands/handlers/knowledge_services.py`.
- Routed read-only language mode, meeting summary, RAG library, proactive suggestion, knowledge review queue, and learning status summaries through `handle_knowledge_services_command(...)`.
- Added `tests/test_command_router_knowledge_services_handler.py`.
- Kept language changes/previews, meeting capture/recording, document tag/move operations, RAG indexing, knowledge writes, proactive refresh/update, notification execution, and AI fallback in `command_router.py`.

Phase 20 completion:

- Added `backend/app/core/commands/handlers/device_status.py`.
- Routed read-only phone link readiness, face/security enrollment status, startup auto-launch status, and smart-home setup/help summaries through `handle_device_status_command(...)`.
- Added `tests/test_command_router_device_status_handler.py`.
- Kept face enrollment/verification, auth lock/unlock, startup enable/disable, phone pairing/setup, smart-home/IoT controls, camera/microphone/OCR/object detection actions, system actions, and AI fallback in `command_router.py`.

Phase 21 completion:

- Added `backend/app/core/commands/handlers/awareness.py`.
- Routed read-only active-window summary commands through `handle_awareness_command(...)`.
- Added `tests/test_command_router_awareness_handler.py`.
- Kept screenshot/OCR capture, screen explanation, visible text summarization, context suggestions, object detection, UI actions, system actions, and AI fallback in `command_router.py`.

Phase 22 completion:

- Added `backend/app/core/commands/handlers/contacts.py`.
- Routed read-only local contact list/find and Google contact list/change/favorite/alias summaries through `handle_contacts_command(...)`.
- Added `tests/test_command_router_contacts_handler.py`.
- Kept calls, messages, emails, contact edits/deletes, Google sync/refresh/merge/import, confirmation flows, field lookups that force refresh, system actions, and AI fallback in `command_router.py`.

Phase 23 completion:

- Updated `backend/app/core/commands/registry.py` with `build_readonly_registry(...)`.
- Replaced repeated one-off read-only registry construction in `command_router.py` with named groups.
- Added `tests/test_command_registry_builder.py`.
- Moved no new command branches and preserved legacy dispatch locations.

Phase 24 completion:

- Added `backend/app/core/commands/handlers/planning.py`.
- Routed read-only Google Calendar status/today/upcoming/titles and local calendar/date query summaries through `handle_planning_command(...)`.
- Added `tests/test_command_router_planning_handler.py`.
- Added the `planning` registry group after `contacts`, plus named `planning_google` and `planning_calendar` groups to preserve old dispatch locations.
- Kept Google Calendar sync/event mutations, generic agenda intent routing, weather lookup, reminders/tasks mutations, notifications, AI day planning, and AI fallback in `command_router.py`.

Phase 25 completion:

- Added `backend/app/core/commands/handlers/project_knowledge.py`.
- Routed read-only RAG library, knowledge review queue, storage report, and storage cleanup suggestion summaries through `handle_project_knowledge_command(...)`.
- Added `tests/test_command_router_project_knowledge_handler.py`.
- Added the `project_knowledge` registry group after `planning`, plus named `project_knowledge_library` and `project_knowledge_storage` groups to preserve old dispatch locations.
- Kept knowledge writes, review clearing, document tag/move operations, project/file indexing, document Q&A/search, file mutations, embedding/vector DB writes, and AI fallback outside the extracted handler.

Phase 26 completion:

- Added `backend/app/core/commands/handlers/system_health.py`.
- Routed read-only system/PC health, CPU, RAM, disk, exact battery, hardware status, and hardware event summaries through `handle_system_health_command(...)`.
- Added `tests/test_command_router_system_health_handler.py`.
- Added the `system_health` registry group after `project_knowledge`, plus named `system_health_core`, `system_health_hardware`, and `system_health_battery` groups for safe dispatch subsets.
- Kept broad battery fallback, storage status/cleanup, scans/rescans, settings changes, startup changes, system power actions, app/window actions, hardware capture/control, and AI fallback outside the extracted handler.

Phase 27 completion:

- Added `backend/app/core/commands/handlers/iot_status.py`.
- Routed read-only smart-home status, IoT inventory, smart-home history, and setup/readiness help summaries through `handle_iot_status_command(...)`.
- Added `tests/test_command_router_iot_status_handler.py`.
- Added the `iot_status` registry group after `system_health`.
- Moved smart-home setup/help ownership out of `device_status`; phone link, face/security, and startup readiness remain there.
- Kept IoT control dispatch, confirmation-backed device actions, live validation/connectivity checks, pairing/connect flows, config mutations, system actions, and AI fallback outside the extracted handler.

Phase 28 completion:

- Added `backend/app/core/commands/handlers/security_status.py`.
- Routed read-only security status, security alerts/logs, voice authentication status, security admin status, and admin-permission status summaries through `handle_security_status_command(...)`.
- Added `tests/test_command_router_security_status_handler.py`.
- Added the `security_status` registry group after `iot_status`.
- Moved security-status ownership out of `diagnostics`; diagnostics keeps voice diagnostics, assistant doctor, and backend stability.
- Kept authentication, lock/unlock, lockdown, device trust, security admin changes, PIN changes, emergency actions, permission/security setting mutations, log clearing/deletion, system actions, and AI fallback outside the extracted handler.

Phase 29 completion:

- Added `backend/app/core/commands/handlers/emergency_status.py`.
- Routed read-only emergency mode/help, quick-response help, and emergency protocol information summaries through `handle_emergency_status_command(...)`.
- Added `tests/test_command_router_emergency_status_handler.py`.
- Added the `emergency_status` registry group after `security_status`.
- Kept protocol triggers, alert/SOS sending, safe-alert sending, location sharing, emergency contact calls/messages, lockdown/lock/unlock, emergency setting changes, log clearing/deletion, system actions, and AI fallback outside the extracted handler.

Phase 30 completion:

- Added `backend/app/core/commands/handlers/profile_status.py`.
- Routed read-only profile summary, personal details snapshot, preferred language, and preferred tone summaries through `handle_profile_status_command(...)`.
- Added `tests/test_command_router_profile_status_handler.py`.
- Added the `profile_status` registry group after `emergency_status`.
- Kept preference updates, profile edits, memory saves, memory forget/delete/clear flows, persona/personality setting changes, config/database writes, and AI fallback outside the extracted handler.

Phase 31 completion:

- Added `backend/app/core/commands/handlers/developer_status.py`.
- Routed read-only developer mode, workspace/coding, git status, branch, remote, recent commit, and repository summaries through `handle_developer_status_command(...)`.
- Added `tests/test_command_router_developer_status_handler.py`.
- Added the `developer_status` registry group after `profile_status`.
- Moved developer mode/workspace summary ownership out of the generic `status` handler.
- Kept terminal launch, save/run flows, git mutations, file writes/edits, script execution, app launch, developer setting changes, and AI fallback outside the extracted handler.

Phase 32 completion:

- Added `backend/app/core/commands/handlers/notification_status.py`.
- Routed read-only notification status/help, popup/alert status, reminder/event notification status, and notification history/list summaries through `handle_notification_status_command(...)`.
- Added `tests/test_command_router_notification_status_handler.py`.
- Added the `notification_status` registry group after `developer_status`.
- Added notification summary callbacks to `CommandContext`.
- Kept notification sending, popup display, reminder/task mutations, notification enable/disable commands, notification setting changes, and AI fallback outside the extracted handler.

Phase 33 completion:

- Added `backend/app/core/commands/handlers/audio_status.py`.
- Routed read-only sound status, audio status, chime status, notification sound status, and voice audio readiness through `handle_audio_status_command(...)`.
- Added `tests/test_command_router_audio_status_handler.py`.
- Added the `audio_status` registry group after `notification_status`.
- Added audio summary callbacks to `CommandContext`.
- Kept sound/chime playback, sound setting changes, enable/disable sound or chime commands, voice start/stop/listen/capture commands, microphone capture, TTS playback, and AI fallback outside the extracted handler.

Phase 34 completion:

- Added `backend/app/core/commands/handlers/overlay_status.py`.
- Routed read-only overlay status, quick overlay status, pinned command list/summary, hotkey status, and overlay help through `handle_overlay_status_command(...)`.
- Added `tests/test_command_router_overlay_status_handler.py`.
- Added the `overlay_status` registry group after `audio_status`.
- Added overlay summary callbacks to `CommandContext`.
- Kept pin/unpin/move pinned command actions, overlay enable/disable/toggle, hotkey setting changes, overlay open/close/hide/show actions, UI click/type actions, and AI fallback outside the extracted handler.

Phase 35 completion:

- Added `backend/app/core/commands/handlers/interface_status.py`.
- Routed read-only startup status, auto-launch status, tray mode status, interface/terminal mode status, desktop/backend mode summary, and launcher/readiness status through `handle_interface_status_command(...)`.
- Added `tests/test_command_router_interface_status_handler.py`.
- Added the `interface_status` registry group after `overlay_status`.
- Added startup/interface summary callbacks to `CommandContext`.
- Moved auto-launch status ownership out of `device_status`.
- Kept startup enable/disable, tray mode setting changes, interface/terminal mode setting changes, UI/desktop-shell open commands, app/window launches, settings writes, and AI fallback outside the extracted handler.

Phase 36 completion:

- Added `backend/app/core/commands/handlers/config_status.py`.
- Routed read-only config status, settings status, assistant settings summary, environment/config readiness, and feature toggle summaries through `handle_config_status_command(...)`.
- Added `tests/test_command_router_config_status_handler.py`.
- Added the `config_status` registry group after `interface_status`.
- Added config/settings summary callbacks to `CommandContext`.
- Kept settings mutations, feature enable/disable commands, admin/escalation flows, API key/config writes, security setting changes, and AI fallback outside the extracted handler.

Risk: high once code changes begin, because many features route through this file.

### Phase 17: Optional Dependency Readiness Matrix

Status: PARTIAL

Create a table for optional dependencies:

- microphone/STT: speech_recognition, sounddevice, Whisper
- TTS: pyttsx3/SAPI, Piper, Coqui
- screen/OCR: pyautogui, pytesseract, Tesseract executable, OpenCV, NumPy
- object detection: ultralytics, YOLO model, camera
- Windows automation: keyboard, pyperclip, pywin32, COM/WScript shell

Risk: low, documentation-only.

### Phase 18: Backend API Consolidation Proposal

Status: DUPLICATE

Do not merge `web_api.py` and `chat_api.py` yet.

Safe prep:

- List route overlaps.
- Mark public, internal, and legacy routes.
- Keep mobile companion backend routes documented as backend runtime logic, not as an active mobile app workspace.

Risk: medium to high once code changes begin.

## Safe Cleanup Recommendations

- COMPLETE: Keep frontend/mobile app-client directories absent from active project.
- COMPLETE: Keep `backend/data/knowledge/*.json` tracked as seed knowledge.
- COMPLETE: Keep `.gitignore` secret patterns for app auth secret, secret files, token files, and credential files.
- PARTIAL: Add a route ownership document before moving API code.
- PARTIAL: Add an import map before touching compatibility modules.
- DUPLICATE: Treat `features/modules` as intentional compatibility shims, not dead code.
- DUPLICATE: Treat provider duplication as design debt, not immediate cleanup.
- DUPLICATE: Treat pycache-only directory contents as generated artifacts, but remove only in a separate explicit cleanup pass.
- MISSING: Hardware readiness docs for voice, vision, and desktop automation.

## Current Cleanup Cycle Status

Status: COMPLETE through Phase 37.

The backend cleanup cycle is now paused. The final report is `docs/FINAL_BACKEND_CLEANUP_REPORT.md`.

Do not continue extracting command groups until the remaining action-heavy command paths have exact behavioral tests and a new phase plan.
