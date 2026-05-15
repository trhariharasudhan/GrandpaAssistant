# Command Router Audit

Phase 10 backend-only decomposition prep for `backend/app/core/command_router.py`. No command handlers were moved or split in this phase.

## Current Shape

- File size: about 6,450 lines.
- Main entrypoint: `process_command(command, INSTALLED_APPS, input_mode="text")`.
- Helper functions before `process_command`: formatting, UI action planning, confirmations, memory/context helpers, debug/fix helpers, contacts, follow-ups, config commands, AI response cleanup.
- Runtime style: linear first-match dispatch with many direct `speak(...)` side effects and several global pending-action variables.

## Imported Module Families

| Family | Examples | Role | Risk |
| --- | --- | --- | --- |
| Brain/AI | `brain.ai_engine`, `brain.database`, `brain.memory_engine`, `brain.semantic_memory` | AI fallback, command logs, personal memory, semantic lookup | Medium |
| Safety/security | `security.hub`, auth helpers, fix approval flow | Blocks/confirms risky actions, auth continuation, audit summaries | High |
| Windows/system | `system.*`, `keyboard`, `pyperclip`, `subprocess`, `webbrowser` | App/window/system controls, media, network, lock/shutdown | High |
| Productivity | tasks, calendar, notes, profile, routines, dashboard | Tasks, reminders, events, habits, goals, daily planning | Medium |
| Automation/integrations | n8n, messaging, IoT, mobile companion, local actions | External automations and device actions | High |
| Vision/context | screen awareness, UI analysis, OCR, object detection, hand mouse | Screen interpretation and UI automation | High |
| Diagnostics/debug | debug assistant, fix plan, backend stability, preflight | Debug reporting and repair approval flow | Medium |
| Voice/config | voice setup, language mode, Piper/custom voice | Voice tuning/status and assistant config | Medium |

## Command Groups

| Command Group | Functions | Modules Used | Risk Level | Suggested Future Module |
| --- | --- | --- | --- | --- |
| Safety/permissions | `_store_pending_confirmation`, `_clear_pending_confirmation`, `_pending_action_from_command`, `_handle_latest_pending_confirmation_response`, `_resume_secured_command` | `security.hub`, `fix_approval_flow` | High | `core.commands.safety` |
| UI analysis/screen actions | `_ui_analysis_payload`, `_maybe_create_pending_ui_action`, `_execute_pending_ui_action`, `_handle_ui_analysis_command` | `ui_analysis.*`, `context_action_executor` | High | `core.commands.handlers.automation` |
| AI fallback | `_clean_ai_response`, final AI branch in `process_command`, follow-up topic branch | `brain.ai_engine`, `core.followup_memory` | Medium | `core.commands.handlers.ai` |
| Memory/context | `_handle_memory_edit_command`, `_current_location_text`, semantic memory helpers, personal question branch | `brain.memory_engine`, `brain.semantic_memory` | Medium | `core.commands.handlers.memory` |
| Contacts/calls | `_handle_contact_action_command`, `_handle_contact_lookup_command`, `_maybe_confirm_contact_intent` | `contact_manager`, `call_control`, Phone Link readiness | High | `core.commands.handlers.contacts` |
| Debug/fix assistant | debug session helpers, fix approval helpers, dashboard/checklist commands | `debug_*`, `fix_*` | Medium | `core.commands.handlers.debug` |
| Productivity | planner, habits, goals, reminders, meetings, RAG, documents | `features.productivity.*` | Medium | `core.commands.handlers.productivity` |
| Automation/IoT | n8n handler, automation rules, mobile companion, IoT resolution | `automation.*`, `integrations.iot_module` | High | `core.commands.handlers.automation` |
| Voice/config | `_handle_config_command`, voice diagnostics/setup commands | voice/config helpers | Medium | `core.commands.handlers.config` |
| Vision/object detection | OCR, object watch, object scan, hand mouse | `vision.*`, `features.ui_analysis.*` | High | `core.commands.handlers.vision` |
| Windows/system actions | app launch, explorer, screenshot, close/minimize, shutdown/restart/sleep/lock, settings pages | `system.*`, `subprocess`, `keyboard` | High | `core.commands.handlers.system` |
| Local intents/basic chat | `try_handle_intent`, greeting/date/joke/wikipedia branches | `core.intent_router`, local knowledge/productivity modules | Low | `core.commands.handlers.knowledge` |

## Function Inventory

| Function | Lines | Purpose | Side Effects | Test Coverage | Migration Risk |
| --- | --- | --- | --- | --- | --- |
| `_compact_text` | 97-98 | Normalize command/display text | None | Indirect | Low |
| `detect_n8n_automation_intent` | 131-135 | Detect n8n automation phrasing | None | Indirect | Low |
| `_handle_n8n_automation_command` | 138-155 | Send command payload to n8n | Network/client call, `speak` | Route/API tests cover n8n; no direct router group test yet | Medium |
| UI action helpers | 158-404 | Analyze screen and create/execute pending UI action | Screen capture, UI action execution, `speak` | Indirect UI tests | High |
| Overlay/tray stubs | 406-557 | Backend-only compatibility stubs | None or status strings | Startup/import tests | Low |
| Confirmation helpers | 722-796 | Store, clear, resume pending confirmations | Mutates globals, may execute stored callbacks | `test_command_router_confirmations`, `test_command_router_groups` | High |
| Status/config summaries | 799-1519 | Offline, security, developer, IoT, voice, debug, memory summaries | Reads config/data; some external status calls | Broad unittest coverage | Medium |
| Emergency/contact helpers | 1526-1613, 1696-2440 | Emergency alerts, location sharing, contact disambiguation/action | Web/phone links, messaging/call flows, pending confirmations | Contact tests and router group safety coverage | High |
| `_handle_config_command` | 2443-3674 | Large config/status command dispatcher | Reads/writes settings and voice/config state | Indirect config/status tests | Medium |
| `handle_knowledge_command` | new module | Extracted low-risk basic knowledge replies | None; returns `CommandResult` | `test_command_router_knowledge_handler` | Low |
| `handle_memory_command` | new module | Extracted low-risk personal name and semantic memory commands | Personal name save callback; semantic reads; returns `CommandResult` | `test_command_router_memory_handler` | Medium |
| `handle_diagnostics_command` | new module | Extracted read-only diagnostics/status replies | Reads diagnostic summary callbacks; returns `CommandResult` | `test_command_router_diagnostics_handler` | Low |
| `handle_debug_command` | new module | Extracted read-only debug/fix summary replies | Reads debug/fix summary callbacks; returns `CommandResult` | `test_command_router_debug_handler` | Low |
| `handle_status_command` | new module | Extracted read-only voice/offline/backend status replies | Reads status callbacks; returns `CommandResult` | `test_command_router_status_handler` | Low |
| `handle_productivity_command` | new module | Extracted read-only productivity/automation/mobile summary replies | Reads productivity/status callbacks; returns `CommandResult` | `test_command_router_productivity_handler` | Low |
| `handle_knowledge_services_command` | new module | Extracted read-only language, meeting, RAG, proactive suggestion, knowledge review, and learning summaries | Reads knowledge-service callbacks; returns `CommandResult` | `test_command_router_knowledge_services_handler` | Low |
| `handle_device_status_command` | new module | Extracted read-only phone, face enrollment, startup auto-launch, and smart-home setup summaries | Reads device/readiness callbacks; returns `CommandResult` | `test_command_router_device_status_handler` | Low |
| `handle_awareness_command` | new module | Extracted read-only active-window awareness summaries | Reads active-window callback; returns `CommandResult` | `test_command_router_awareness_handler` | Low |
| `handle_contacts_command` | new module | Extracted read-only local and Google contact lookup/status summaries | Reads contact summary callbacks; returns `CommandResult` | `test_command_router_contacts_handler` | Low |
| `CommandContext` / `CommandHandlerRegistry` / `build_readonly_registry` | new modules | Shared callback bundle, ordered handler execution, and named read-only registry builder | None by itself | `test_command_handler_registry`, `test_command_registry_builder` | Low |
| `process_command` | 3678-6420s | Main command dispatch pipeline | Many: speaks, logs, settings writes, OS/device actions, AI calls | Existing router tests plus Phase 10/11 group tests | High |

## Dangerous/System Actions

| Action | Current Guard | Risk |
| --- | --- | --- |
| Shutdown/restart/sign out/sleep/close app | Pending confirmation and/or security gate | High |
| Lock system/security lockdown | Direct action after matching command | High |
| UI click/type execution | Pending UI action with confidence/screen-change checks | High |
| IoT control | IoT resolver may require confirmation | High |
| Contact delete/call/message/mail | Confirmation mode/contact disambiguation | High |
| Fix approval execution | Explicit approval ID or latest plan approval | High |
| Object detection/hand mouse | Availability checks and stop events | Medium |

## AI, Memory, Context Paths

- AI fallback lives at the end of `process_command` and calls `ask_ollama(...)`.
- Follow-up AI path uses `app_scan_module.LAST_TOPIC` plus pronoun detection.
- Personal memory is handled by direct commands such as `my name is ...`, `_handle_memory_edit_command`, and `is_personal_question(...)` plus `search_memory(...)`.
- Semantic memory commands are `semantic memory status` and `search/find/look up my memory ...`.
- Screen/context commands include screen explanation, fix plan, context suggestions, visible text summaries, and UI actions.

## Phase 10 Test Coverage Added

`tests/test_command_router_groups.py` covers:

- greeting/basic chat branch
- local intent dispatch branch
- AI fallback branch
- safe app/system command sample through mocked launcher
- shutdown confirmation path
- security refusal path
- unknown command provider failure path
- personal memory write path

## Phase 11 Extraction Update

`backend/app/core/commands/handlers/knowledge.py` now owns only the low-risk basic knowledge replies:

- greetings/basic replies
- period greeting via injected `get_period`
- joke via injected `tell_joke`
- factual Wikipedia-style prefixes via injected `wikipedia_search`

`command_router.py` still owns `process_command(...)`, broad `try_handle_intent(...)`, post-intent contact context handling, memory, safety, system actions, UI automation, IoT, contacts, and AI fallback.

Line count changed from 6,465 to 6,432 lines.

## Phase 12 Memory Extraction Update

`backend/app/core/commands/handlers/memory.py` now owns only low-risk memory branches:

- save/read personal identity name
- semantic memory status
- read-only semantic memory lookup

`command_router.py` still owns `_handle_memory_edit_command(...)`, `clear memory`, destructive memory actions, personal-question fallback, and AI fallback. Semantic memory delegation remains at the original semantic-memory location in `process_command(...)` to preserve dispatch order.

Line count changed from 6,432 to 6,425 lines.

## Phase 13 Diagnostics Extraction Update

`backend/app/core/commands/handlers/diagnostics.py` now owns only read-only diagnostics/status branches:

- security status summary
- voice diagnostics summary
- assistant doctor summary
- backend stability summary

`command_router.py` still owns security alerts/logs, security admin/auth/lockdown actions, voice setup/auth actions, screen/debug/fix assistant commands, provider/AI fallback, and system actions. Diagnostics delegation is split across the old security/voice location and the old diagnostics location to preserve dispatch order.

Line count changed from 6,425 to 6,418 lines.

## Phase 14 Debug/Fix Summary Extraction Update

`backend/app/core/commands/handlers/debug.py` now owns only read-only debug/fix summary branches:

- current debug session summary
- debug dashboard summary
- pending fix approvals summary
- fix audit summary

`command_router.py` still owns debug session lifecycle, export, search/timeline/reuse/checklist commands, debug report/fix-plan generation, `apply fix`, `dismiss fix`, and approval execution. The line count changed from 6,418 to 6,438 lines because adapter callbacks were added to preserve exact dispatch order.

## Phase 15 Debug History/Reporting Extraction Update

`backend/app/core/commands/handlers/debug.py` was extended to own additional read-only debug history/reporting branches:

- debug timeline/history summary
- debug session search summary
- reuse suggestions
- debug learning summary
- debug checklist/preflight summary

`command_router.py` still owns debug session start/close/export, `debug this`, fix plan generation, fix application, dismiss/approval execution, and all system/safety/UI/IoT/contact/AI fallback paths. The line count changed from 6,438 to 6,439 lines because callback wrappers preserve exact old behavior.

## Phase 16 Registry/Context Foundation Update

`backend/app/core/commands/context.py` and `backend/app/core/commands/registry.py` provide a shared callback bundle and ordered handler execution for extracted handlers.

The existing extracted handlers now consume `CommandContext` while preserving their callback-style test interface. `command_router.py` still invokes the extracted handlers at the legacy dispatch points, so behavior order is unchanged. The line count changed from 6,439 to 6,432 lines.

## Phase 17 Status Extraction Update

`backend/app/core/commands/handlers/status.py` now owns read-only voice/offline/backend status branches, including offline mode/help/AI status, focus status, voice trainer status, Piper/custom voice setup summaries, and voice profile status. Phase 31 moved developer mode/workspace summaries to `developer_status`.

`command_router.py` still owns all settings writes, model/provider changes, voice setup actions, auth/security mutations, system actions, and AI fallback. The line count changed from 6,432 to 6,416 lines.

## Phase 18 Productivity Extraction Update

`backend/app/core/commands/handlers/productivity.py` now owns read-only productivity, automation history, and mobile status summary branches:

- planner focus summary
- reminder timeline summary
- habit dashboard summary
- goal board summary
- smart reminder priority summary
- automation history summary
- mobile companion status summary

`command_router.py` still owns reminder/task creation and mutation, habit/goal mutation, AI day planning, automation execution/configuration, mobile setup/send actions, IoT/system/safety paths, and AI fallback. The line count changed from 6,416 to 6,395 lines.

## Phase 19 Knowledge Services Extraction Update

`backend/app/core/commands/handlers/knowledge_services.py` initially owned read-only language, meeting, RAG/local knowledge, proactive suggestion, knowledge review queue, and learning status summary branches. Phase 25 moved RAG/local knowledge and knowledge review ownership into `project_knowledge`.

`command_router.py` still owns language mode changes/previews, meeting capture/recording, document tag/move operations, RAG indexing and knowledge writes, proactive suggestion refresh/update, notification execution, and AI fallback. The line count changed from 6,395 to 6,396 lines because callback wiring was added to preserve dispatch order.

## Phase 20 Device Status Extraction Update

`backend/app/core/commands/handlers/device_status.py` initially owned read-only phone link readiness, face/security enrollment status, startup auto-launch status, and smart-home setup/help summary branches. Phase 27 moved smart-home setup/help ownership into `iot_status`.

`command_router.py` still owns face enrollment/verification actions, authentication and lock/unlock flows, startup enable/disable mutations, phone pairing/device setup, smart-home/IoT control actions, camera/microphone/OCR/object detection actions, system controls, and AI fallback. The line count changed from 6,396 to 6,404 lines because callback wiring was added to preserve dispatch order.

## Phase 21 Awareness Extraction Update

`backend/app/core/commands/handlers/awareness.py` now owns only the read-only active-window summary commands. The Tamil active-window command still requests Tamil output through the same callback.

`command_router.py` still owns screen explanation, visible text summarization, OCR/screenshot capture, context suggestions, object detection status and execution, UI actions, system actions, and AI fallback. The line count changed from 6,404 to 6,403 lines.

## Phase 22 Contacts Extraction Update

`backend/app/core/commands/handlers/contacts.py` now owns read-only local contact list/find commands and read-only Google contact list/change/favorite/alias summaries.

`command_router.py` still owns call/message/mail actions, local contact add/delete, Google sync/refresh/merge/import, favorite and alias mutations, confirmation flows, contact field lookups that force Google refresh, system actions, and AI fallback. The line count changed from 6,403 to 6,419 lines because callback wiring was added to preserve dispatch order.

## Phase 23 Registry Builder Update

`backend/app/core/commands/registry.py` now provides `build_readonly_registry(...)` and a stable default read-only group order. `command_router.py` uses named groups at the existing legacy dispatch locations instead of repeatedly constructing one-off registries.

No command groups moved in this phase. Safety/system/UI/IoT/contact action/AI fallback logic remains in `command_router.py`. The line count changed from 6,419 to 6,398 lines.

## Phase 24 Calendar/Planning Extraction Update

`backend/app/core/commands/handlers/planning.py` now owns only read-only calendar/planning summary branches:

- Google Calendar connection/sync status text
- Google Calendar today/upcoming event summaries
- Google Calendar event title listing
- local calendar/date query summaries through the existing `handle_calendar_queries(...)` callback

`command_router.py` still owns Google Calendar sync/refresh, event creation/deletion/rename/reschedule/update, generic agenda intent routing, weather lookup, reminder/task mutations, notification actions, AI day planning, and AI fallback. The default registry appends `planning` after `contacts`, while named `planning_google` and `planning_calendar` groups keep the old dispatch positions. The line count changed from 6,398 to 6,403 lines.

## Phase 25 Project Knowledge Extraction Update

`backend/app/core/commands/handlers/project_knowledge.py` now owns read-only local file/project knowledge summaries:

- RAG library summaries
- local knowledge review queue summaries
- storage report summaries
- storage cleanup suggestion summaries

`knowledge_services` now keeps language, meeting, proactive suggestion, and learning summaries; project/file/library knowledge moved to the dedicated `project_knowledge` handler. `command_router.py` still owns document tag/move operations, knowledge answer add/clear/delete, indexing/reindexing, file create/edit/delete/move, document search/Q&A paths that can call RAG/model behavior, embedding/vector DB writes, and AI fallback. The default registry appends `project_knowledge` after `planning`, while named groups preserve old dispatch positions. The line count changed from 6,403 to 6,402 lines.

## Phase 26 System Health Extraction Update

`backend/app/core/commands/handlers/system_health.py` now owns read-only system-health summaries:

- system/PC health status
- CPU, RAM, disk, and exact battery status
- hardware/device status
- recent hardware/device event history

`command_router.py` still owns broad battery fallback behavior, storage status and cleanup suggestions through `project_knowledge`, hardware scan/rescan/refresh actions, settings changes, startup changes, shutdown/restart/sleep/lock/sign-out, app/window actions, capture/control actions, and AI fallback. The default registry appends `system_health` after `project_knowledge`, while named groups keep core health and hardware summaries at their legacy dispatch points. The line count changed from 6,402 to 6,409 lines.

## Phase 27 IoT/Smart-Home Status Extraction Update

`backend/app/core/commands/handlers/iot_status.py` now owns read-only IoT/smart-home summaries:

- smart-home status and configured device summaries
- IoT inventory/overview summaries
- smart-home action history summaries
- smart-home setup/readiness help

`device_status` now keeps phone link, face/security, and startup readiness summaries. `command_router.py` still owns IoT control dispatch, confirmation-backed IoT actions, live validation/connectivity checks, pairing/connect flows, config mutations, system actions, and AI fallback. The default registry appends `iot_status` after `system_health`. The line count changed from 6,409 to 6,394 lines.

## Phase 28 Security/Auth Status Extraction Update

`backend/app/core/commands/handlers/security_status.py` now owns read-only security/auth/admin summaries:

- security status
- security alerts and logs
- voice authentication status
- security admin status
- Windows/admin permission status

`diagnostics` now keeps voice diagnostics, assistant doctor, and backend stability summaries. `command_router.py` still owns authentication actions, assistant lock/unlock and lockdown, trust/approve device mutations, security admin mode changes, security PIN changes, emergency actions, permission/security setting mutations, log clearing/deletion, system actions, and AI fallback. The default registry appends `security_status` after `iot_status`. The line count changed from 6,394 to 6,392 lines.

## Phase 29 Emergency Status Extraction Update

`backend/app/core/commands/handlers/emergency_status.py` now owns read-only emergency summaries:

- emergency mode status/help
- emergency quick-response help
- emergency protocol information

`command_router.py` still owns emergency protocol triggers, alert/SOS sending, safe-alert sending, location sharing, emergency contact calls/messages, lockdown/lock/unlock, emergency setting changes, log clearing/deletion, system actions, and AI fallback. The default registry appends `emergency_status` after `security_status`. The line count changed from 6,392 to 6,393 lines.

## Phase 30 Profile/Preference Status Extraction Update

`backend/app/core/commands/handlers/profile_status.py` now owns read-only profile and preference summaries:

- profile summary
- personal details snapshot
- preferred response language
- preferred response tone

`command_router.py` still owns preferred language/tone updates, profile edits, memory saves, memory forget/delete/clear flows, persona/personality changes, config/database writes, and AI fallback. The default registry appends `profile_status` after `emergency_status`. The line count changed from 6,393 to 6,409 lines.

## Phase 31 Developer/Git Status Extraction Update

`backend/app/core/commands/handlers/developer_status.py` now owns read-only developer and git summaries:

- developer mode status/help
- workspace and coding summaries
- git status
- current git branch
- git remotes
- recent commits
- repository summary

`status` no longer owns developer mode/workspace summaries. `command_router.py` still owns terminal launch, save/run flows, git add/commit/push/pull/reset/checkout/merge/rebase, file writes/edits, script execution, app launch, developer setting changes, and AI fallback. The default registry appends `developer_status` after `profile_status`. The line count changed from 6,409 to 6,400 lines.

## Phase 32 Notification/Popup Status Extraction Update

`backend/app/core/commands/handlers/notification_status.py` now owns read-only notification summaries:

- notification status and summary
- notification help
- popup/alert status summaries
- reminder/event notification status
- notification history/list read-only response

`command_router.py` still owns notification sending, popup display, reminder/task mutations, notification enable/disable commands, notification setting changes, and AI fallback. The default registry appends `notification_status` after `developer_status`. The line count changed from 6,400 to 6,490 lines because explicit notification summary helpers now replace broad config-only visibility for these read-only commands.

## Phase 33 Sound/Audio/Chime Status Extraction Update

`backend/app/core/commands/handlers/audio_status.py` now owns read-only audio summaries:

- sound status
- audio status
- chime status
- notification sound summary
- voice audio readiness

`command_router.py` still owns sound/chime playback, sound setting changes, enable/disable sound or chime commands, voice start/stop/listen/capture commands, microphone capture, TTS playback, and AI fallback. The default registry appends `audio_status` after `notification_status`. The line count changed from 6,490 to 6,565 lines because explicit read-only sound/audio summary helpers were added.

## Phase 34 Overlay/Pinned-Command Status Extraction Update

`backend/app/core/commands/handlers/overlay_status.py` now owns read-only overlay summaries:

- overlay status
- quick overlay status
- pinned command list/summary
- hotkey status
- overlay help

`command_router.py` still owns pin/unpin/move pinned command actions, overlay enable/disable/toggle, hotkey setting changes, overlay open/close/hide/show actions, UI click/type actions, and AI fallback. The default registry appends `overlay_status` after `audio_status`. The line count changed from 6,565 to 6,616 lines because explicit overlay/hotkey summary helpers were added.

## Phase 35 Startup/Interface Status Extraction Update

`backend/app/core/commands/handlers/interface_status.py` now owns read-only startup/interface summaries:

- startup status
- auto-launch status
- tray mode status
- interface/terminal mode status
- desktop/backend mode summary
- launcher/readiness status

`device_status` no longer owns auto-launch status. `command_router.py` still owns startup enable/disable, tray mode setting changes, interface/terminal mode setting changes, UI/desktop-shell open commands, app/window launch commands, settings writes, and AI fallback. The default registry appends `interface_status` after `overlay_status`. The line count changed from 6,616 to 6,663 lines because explicit startup/interface summary helpers were added.

## Phase 36 Config/Settings Status Extraction Update

`backend/app/core/commands/handlers/config_status.py` now owns read-only config/settings summaries:

- config status
- settings status
- assistant settings summary
- environment/config readiness
- feature toggle summary

`command_router.py` still owns settings mutations, feature enable/disable commands, admin/escalation flows, API key/config writes, security setting changes, and AI fallback. The default registry appends `config_status` after `interface_status`. The line count changed from 6,663 to 6,737 lines because explicit config/settings summary helpers were added.

## Migration Notes

- Do not split `process_command` until every extracted group has a result contract.
- Preserve `speak(...)` behavior until a `CommandResult` object exists.
- Move pure helpers first; delay stateful pending-confirmation and Windows action extraction.
- Keep global pending-confirmation state in one module until a command context object replaces it.
