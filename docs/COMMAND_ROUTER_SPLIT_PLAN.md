# Command Router Split Plan

Phase 10 preparation plan. This is not an instruction to move code yet.

## Target Structure

```text
backend/app/core/commands/
  router.py
  registry.py
  result.py
  safety.py
  handlers/
    ai.py
    system.py
    productivity.py
    memory.py
    automation.py
    knowledge.py
    fallback.py
```

## Proposed Responsibilities

| Future Module | Responsibility | First Candidates | Risk |
| --- | --- | --- | --- |
| `result.py` | `CommandResult` shape, spoken text, metadata, confirmation payload | New code only | Low |
| `registry.py` | Handler registration and first-match ordering | New code only | Medium |
| `safety.py` | Confirmation IDs, pending action storage, security gate wrappers | `_store_pending_confirmation`, `_pending_action_from_command`, `_resume_secured_command` | High |
| `handlers/knowledge.py` | Greetings, local intent router, date/time/wiki/simple local answers | greeting/date/joke/local intent branches | Low |
| `handlers/memory.py` | Personal memory and semantic memory commands | `_handle_memory_edit_command`, name commands, semantic memory commands | Medium |
| `handlers/ai.py` | Follow-up AI and final AI fallback | `_clean_ai_response`, final `ask_ollama` branch | Medium |
| `handlers/productivity.py` | Planner, tasks, habits, goals, meetings, documents, RAG | productivity command blocks | Medium |
| `handlers/automation.py` | n8n, automation rules, IoT, UI action execution | n8n/UI/IoT/automation branches | High |
| `handlers/system.py` | Windows app/window/system controls | explorer, screenshot, close/minimize/maximize, shutdown/restart, settings pages | High |
| `handlers/fallback.py` | Unknown command fallback and last-response safety | final fallback behavior | Medium |

## Safe Split Order

1. Add `CommandResult` and handler protocol without changing `process_command`.
2. Extract pure local/knowledge helpers first: greetings, `try_handle_intent`, joke/date/wiki branches.
3. Extract memory read/write commands after preserving memory tests.
4. Extract AI fallback after adding stream/non-stream behavior tests.
5. Extract productivity commands by domain, one small group at a time.
6. Extract system/automation commands last because they have the highest side-effect risk.
7. Move safety/confirmation state only after all handlers can return confirmation intents instead of storing globals directly.

## Required Guardrails

- Keep `process_command(...)` as the public entrypoint until the end.
- Keep `speak(...)` outputs stable.
- Keep pending confirmation IDs and phrases stable.
- No real OS actions in tests; use mocks for launch, shutdown, restart, IoT, UI actions, calls, and messaging.
- Validate desktop backend and terminal chatbot after each extracted group.

## Exact First Safe Split Recommendation

Start with `handlers/knowledge.py` behind a wrapper while leaving `process_command` in place. The first extraction should include only low-risk branches:

- `try_handle_intent(command)`
- greetings: `hi`, `hello`, `hey`, `hi grandpa`
- `how are you`
- time-of-day greeting via `get_period()`
- `joke`
- Wikipedia-style factual prefix branch

Reason: this group has mostly read-only behavior and no pending confirmations, filesystem writes, OS control, automation, network device control, or security state mutation.

## Phase 11 First Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/result.py`
- `backend/app/core/commands/handlers/knowledge.py`
- `tests/test_command_router_knowledge_handler.py`

Extracted from `command_router.py`:

- greeting commands: `hi`, `hello`, `hey`, `hi grandpa`, and Odin variants
- `how are you` basic reply
- time-of-day phrase reply through injected `get_period`
- joke reply through injected `tell_joke`
- Wikipedia-style factual prefixes through injected `wikipedia_search`

Not extracted:

- broad `try_handle_intent(...)` dispatch, because it can route non-knowledge domains
- safety confirmations
- Windows/system actions
- UI automation
- IoT
- contacts/calls/messages
- AI fallback

Line count changed from 6,465 to 6,432 lines.

## Phase 12 Memory Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/memory.py`
- `tests/test_command_router_memory_handler.py`

Extracted from `command_router.py`:

- `my name is ...`
- `what is my name`, `who am i`, `tell my name`
- `semantic memory status`, `memory semantic status`, `semantic search status`
- read-only semantic memory search: `search/find/look up my memory for ...`

Not extracted:

- `_handle_memory_edit_command(...)`
- `clear memory`
- destructive memory deletion
- personal-question fallback via `is_personal_question(...)`
- AI fallback

Line count changed from 6,432 to 6,425 lines.

Next safe extraction candidate: keep memory extraction paused and add tests for debug/fix assistant command summaries, or extract additional pure read-only status summaries only after exact reply tests are added.

## Phase 13 Diagnostics Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/diagnostics.py`
- `tests/test_command_router_diagnostics_handler.py`

Extracted from `command_router.py`:

- `security status`, `assistant security status`, `system security status`
- `voice diagnostics`, `voice tuning status`, `voice debug`
- `assistant doctor`, `startup doctor`, `system doctor`, `check assistant health`, `assistant health check`
- `backend health summary`, `backend stability summary`, `backend release lock`, `release lock status`, `backend stability dashboard`

Not extracted:

- security alerts/logs
- security admin/auth/lockdown actions
- voice enrollment/auth/setup/config actions
- screen/debug/fix assistant commands
- provider/AI fallback
- system actions

Line count changed from 6,425 to 6,418 lines.

Next safe extraction candidate: extract read-only debug/fix summary commands only after exact reply-shape tests cover debug session summary, debug dashboard, fix approvals summary, and fix audit.

## Phase 14 Debug/Fix Summary Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/debug.py`
- `tests/test_command_router_debug_handler.py`

Extracted from `command_router.py`:

- `current debug session`, `debug session summary`
- `debug dashboard`, `debug health`, `debug status`, `troubleshooting dashboard`
- `show fix approvals`
- `show fix audit log`, `fix audit`, `last fix actions`

Not extracted:

- `start debug session`
- `close debug session`
- `export debug session`
- debug session search/timeline/reuse/learning/checklist
- `debug this`
- fix-plan generation
- `apply fix`
- `dismiss fix ...`
- approval allow/execute paths

Line count changed from 6,418 to 6,438 lines because this phase added callback wrappers and delegation while preserving dispatch order. The behavioral extraction is still complete; later consolidation can reduce adapter overhead after more handlers share a common registry.

Next safe extraction candidate: add tests for read-only debug timeline/search/reuse/checklist summaries, then extract only those read-only debug history/reporting branches. Keep fix plan creation and approval mutation in `command_router.py`.

## Phase 15 Debug History/Reporting Extraction

Status: COMPLETE

Changed:

- Extended `backend/app/core/commands/handlers/debug.py`.
- Added `tests/test_command_router_debug_history_handler.py`.

Extracted from `command_router.py`:

- `debug timeline`, `show debug timeline`, `what happened in debug session`, `debug history`
- `search debug sessions for ...`, `find debug session ...`, `old debug issue ...`, `previous error ...`
- `seen this before`, `similar debug history`, `previous fix for this`, `idhu munnadi vandhucha`
- `debug learning summary`, `what did we learn from debug history`, `common debug errors`, `repeated issues`, `debug insights`
- `run debug checklist`, `preflight debug check`, `preventive debug check`, `debug checklist`, `issue varama check pannu`

Not extracted:

- `start debug session`
- `close debug session`
- `export debug session`
- `debug this`
- fix-plan generation
- `apply fix`
- `dismiss fix ...`
- approval allow/execute paths

Line count changed from 6,438 to 6,439 lines because the router now owns stable callback wrappers for the debug history summaries. Later registry work can collapse repeated callback wiring.

Next safe extraction candidate: stop command-router splitting for one phase and introduce a small command handler registry/context object to reduce repeated callback wiring before extracting more groups.

## Phase 16 Registry/Context Foundation

Status: COMPLETE

Created:

- `backend/app/core/commands/context.py`
- `backend/app/core/commands/registry.py`
- `tests/test_command_handler_registry.py`

Changed:

- `knowledge.py`, `memory.py`, `diagnostics.py`, and `debug.py` now accept a shared `CommandContext`.
- Existing callback-style tests remain compatible.
- `command_router.py` builds one context and invokes small `CommandHandlerRegistry` instances at the same legacy dispatch locations.

Behavior boundary:

- No new command groups were moved.
- `process_command(...)` remains the public entrypoint.
- Registry order was tested independently: first handled result stops the chain, not-handled falls through, and dangerous commands are not swallowed.

Line count changed from 6,439 to 6,432 lines.

Next safe extraction candidate: use the new context/registry to extract read-only voice setup/status summaries or read-only backend/offline mode summaries. Avoid any settings writes or auth/security mutations until exact reply tests exist.

## Phase 17 Voice/Offline/Backend Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/status.py`
- `tests/test_command_router_status_handler.py`

Extracted from `command_router.py`:

- `offline mode status`, `is offline mode on`, `what works offline`
- `offline help`, `offline quick help`, `offline commands`
- `offline ai status`, `local ai status`, `is local ai ready`
- `developer mode status`, `what is developer mode`, `developer help`
- `focus mode status`, `is focus mode on`
- `voice trainer status`, `voice trainer`
- `piper setup status`, `piper voice setup`, `piper status`
- `my voice setup`, `my voice setup status`, `own voice setup`, `custom voice setup`, `voice clone setup`
- `my voice license status`, `custom voice license status`, `voice license status`, `coqui license status`
- `list my voice samples`, `list custom voice samples`, `show custom voice samples`, `available custom voice samples`
- `voice status`, `voice recognition status`, `current voice profile`
- `developer summary`, `workspace summary`, `coding summary`

Not extracted:

- enable/disable offline/developer/focus modes
- voice trainer changes
- Piper/custom voice setup actions
- security/auth actions
- system actions

Line count changed from 6,432 to 6,416 lines.

Next safe extraction candidate: add tests for read-only productivity summaries such as planner focus, reminder timeline, habit/goal dashboards, automation history, and mobile/status summaries before extracting them into a productivity/status handler.

## Phase 18 Productivity/Automation Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/productivity.py`
- `tests/test_command_router_productivity_handler.py`

Extracted from `command_router.py`:

- `planner focus`, `planner focus summary`, `today focus suggestions`, `focus suggestions`, `what should i focus on today`
- `reminder timeline`, `today reminder timeline`, `upcoming reminder timeline`
- `habit dashboard`, `habit summary`, `show habit dashboard`, `habit status`
- `goal board`, `goal board summary`, `goal summary`, `show goals`
- `smart reminder priority`, `smart reminders`, `prioritize reminders`, `reminder priority`
- `automation history`, `automation run history`, `show automation history`
- `mobile companion status`, `mobile status`, `show mobile companion status`

Not extracted:

- create/update/delete reminders and tasks
- habit/goal creation or completion
- AI day planning
- automation creation, execution, enable, or disable
- mobile companion setup or send/update actions
- IoT/system/safety/AI fallback

Line count changed from 6,416 to 6,395 lines.

Next safe extraction candidate: add exact-reply tests for read-only language/meeting/RAG/proactive suggestion summaries, then extract only the summary/status paths. Keep capture, tag, move, refresh, and mutation commands in `command_router.py`.

## Phase 19 Knowledge Services Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/knowledge_services.py`
- `tests/test_command_router_knowledge_services_handler.py`

Extracted from `command_router.py`:

- `language mode status`, `current language mode`, `language mode`
- `meeting summary`, `meeting mode summary`, `show meeting summary`
- `rag library`, `rag library summary`, `show rag library`
- `show proactive suggestions`, `proactive suggestions`, `assistant suggestions`
- `show knowledge review queue`, `knowledge misses`
- `learning status`, `self learning status`, `self improvement status`, `what have you learned`

Not extracted:

- language mode changes and previews
- meeting note capture or recording actions
- document tag/move operations
- RAG indexing or knowledge writes
- proactive suggestion refresh/update or notification execution
- AI fallback

Line count changed from 6,395 to 6,396 lines because the router now owns stable callback wiring for the new read-only service summaries.

Next safe extraction candidate: add exact-reply tests for read-only device/readiness summaries such as phone link readiness, face/security enrollment status, startup auto-launch status, and smart-home setup help. Keep enrollment, setup, auth, IoT actions, and system mutations in `command_router.py`.

## Phase 20 Device/Readiness Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/device_status.py`
- `tests/test_command_router_device_status_handler.py`

Extracted from `command_router.py`:

- `phone link status`
- `face security status`, `face verification status`, `face status`, `is my face enrolled`
- `assistant startup status`, `startup launch status`, `auto launch status`
- `smart home setup help`, `iot setup help`, `smart home setup`, `iot config help`

Not extracted:

- face enrollment or verification actions
- authentication, lock, or unlock actions
- startup enable/disable actions
- phone pairing or device setup mutations
- smart-home/IoT control actions
- camera, microphone, OCR, object detection, app launch, system, or AI fallback paths

Line count changed from 6,396 to 6,404 lines because the router now owns stable callback wiring for device/readiness summaries.

Next safe extraction candidate: add exact-reply tests for read-only context/awareness summaries such as active window summary, visible text summaries, screen explanation status, and object detection status only where they do not capture hardware or mutate state. Keep scans, captures, object detection start/stop, UI actions, and system controls in `command_router.py`.

## Phase 21 Context/Awareness Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/awareness.py`
- `tests/test_command_router_awareness_handler.py`

Extracted from `command_router.py`:

- `what app am i in`
- `what app am i using`
- `what window is active`
- `current window`
- `active window`
- `naan enna app use panren`
- `where am i working`

Not extracted:

- `what is on my screen`, `explain my screen`, `read my screen`, and related screen explanation commands because they call screen/OCR capture paths
- `summarize this screen` because it calls screenshot/OCR-backed visible text summarization
- `object detection status`, `detected objects`, and object-query commands because the current branch can run camera detection when no cached detector is active
- context suggestion commands because they build live screen suggestions
- UI click/type/execute actions
- system actions and AI fallback

Line count changed from 6,404 to 6,403 lines.

Next safe extraction candidate: add exact-reply tests for read-only contact lookup/status summaries, while keeping calls, messages, emails, sync, contact edits, and confirmation flows in `command_router.py`.

## Phase 22 Contact Lookup/Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/contacts.py`
- `tests/test_command_router_contacts_handler.py`

Extracted from `command_router.py`:

- `show contact`, `show contacts`, `list contacts`, `my contacts`
- `find contact ...`, `search contact ...`
- `list google contacts`, `show google contacts`, `show synced contacts`
- `show google contact changes`, `google contact changes`, `recent contact changes`
- `list favorite contacts`, `show favorite contacts`
- `list contact aliases`, `show contact aliases`

Not extracted:

- call/message/mail/email actions
- local contact add/delete flows
- Google Contacts sync/refresh/merge/import
- contact favorites and alias mutations
- contact field lookups like `what is Priya phone`, because the current path force-refreshes Google Contacts
- confirmation approve/deny flows
- system actions and AI fallback

Line count changed from 6,403 to 6,419 lines because the router now owns stable callback wiring for contact lookup/status summaries.

Next safe extraction candidate: pause feature extraction and reduce repeated registry boilerplate in `command_router.py` by creating one ordered read-only registry builder, while preserving every existing dispatch location and reply text.

## Phase 23 Registry Builder Consolidation

Status: COMPLETE

Created/changed:

- Updated `backend/app/core/commands/registry.py` with `DEFAULT_READONLY_GROUPS` and `build_readonly_registry(...)`.
- Added `tests/test_command_registry_builder.py`.
- Replaced one-off read-only `CommandHandlerRegistry([...])` construction in `command_router.py` with named builder calls.

Supported groups:

- `knowledge`
- `memory`, `memory_personal`, `semantic_memory`
- `diagnostics`, `diagnostics_status`, `diagnostics_health`
- `debug`, `debug_session`, `debug_history`
- `status`
- `productivity`
- `knowledge_services`
- `device_status`
- `awareness`
- `contacts`
- `planning`
- `project_knowledge`
- `system_health`
- `iot_status`
- `security_status`
- `emergency_status`
- `profile_status`

Behavior boundary:

- No new command groups were extracted.
- Legacy dispatch locations are unchanged.
- Reply text/shape is unchanged.
- Safety/system/UI/IoT/contact action/AI fallback logic remains in `command_router.py`.

Line count changed from 6,419 to 6,398 lines.

Next safe extraction candidate: add exact-reply tests for read-only calendar/weather/basic planning summaries, but keep event creation/deletion, Google sync, notification actions, and AI fallback in `command_router.py`.

## Phase 24 Calendar/Planning Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/planning.py`
- `tests/test_command_router_planning_handler.py`

Extracted from `command_router.py`:

- `google calendar status`
- `calendar sync status`
- `today in google calendar`, `google calendar today`, `today google calendar events`
- `upcoming google calendar events`, `google calendar upcoming events`
- `list google calendar event titles`, `google calendar titles`, `show google calendar titles`
- local read-only calendar/date queries previously handled by `handle_calendar_queries(...)`

Not extracted:

- Google Calendar sync/refresh
- Google Calendar event create/delete/rename/reschedule/update flows
- generic `today agenda`, which remains intent-router-owned
- weather commands, because existing behavior can use external weather lookup
- reminders/tasks mutations
- notification actions
- AI day planning and AI fallback

Registry update:

- Added default group `planning` after `contacts`.
- Added named groups `planning_google` and `planning_calendar` so `command_router.py` can preserve the legacy dispatch locations.

Line count changed from 6,398 to 6,403 lines because callback wrappers and registry delegation preserve exact behavior.

Next safe extraction candidate: audit read-only local file/project knowledge helper branches, but keep indexing, file mutation, RAG writes, and AI fallback in `command_router.py`.

## Phase 25 Project Knowledge Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/project_knowledge.py`
- `tests/test_command_router_project_knowledge_handler.py`

Extracted/owned by the new handler:

- `rag library`, `rag library summary`, `show rag library`
- `show knowledge review queue`, `knowledge misses`
- `storage status`, `disk space`, `storage report`
- `storage cleanup suggestion`, `cleanup suggestion`, `how should i clean storage`

Ownership change:

- `knowledge_services` now keeps language, meeting, proactive suggestions, and learning summaries.
- `project_knowledge` owns RAG/library, local knowledge review, and local storage summary commands.

Not extracted:

- document tag/move operations
- knowledge answer add/clear/delete operations
- project/file indexing or reindexing
- document search/Q&A commands that can call RAG or model-backed paths
- file create/edit/delete/move operations
- embedding/vector DB writes
- AI/RAG answer generation and AI fallback

Registry update:

- Added default group `project_knowledge` after `planning`.
- Added named groups `project_knowledge_library` and `project_knowledge_storage` so `command_router.py` can preserve the legacy dispatch locations.

Line count changed from 6,403 to 6,402 lines.

Next safe extraction candidate: extract read-only system storage/device-health summaries into a system status handler only where they do not mutate settings or trigger hardware actions.

## Phase 26 System Health Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/system_health.py`
- `tests/test_command_router_system_health_handler.py`

Extracted/owned by the new handler:

- `system status`, `health status`, `system health`, `pc health`
- `cpu usage`, `cpu status`
- `ram usage`, `memory usage`, `ram status`, `memory status`
- `disk usage`, `disk status`
- exact `battery status`, `battery health`
- `hardware status`, `device status`, `connected hardware`, `what hardware is connected`, `what devices are connected`
- `recent hardware events`, `hardware events`, `recent device events`, `device events`

Not extracted:

- broad battery fallback phrases, which keep the existing `get_battery_info()` reply behavior
- `storage status` and cleanup suggestion commands, now owned by `project_knowledge`
- hardware scan/rescan/refresh actions
- settings changes and startup changes
- shutdown/restart/sleep/lock/sign-out
- app launch/close/window actions
- screen/camera/microphone capture or control actions
- AI fallback

Registry update:

- Added default group `system_health` after `project_knowledge`.
- Added named groups `system_health_core`, `system_health_hardware`, and `system_health_battery` for dispatch-safe subsets.

Line count changed from 6,402 to 6,409 lines because the router now wires health callbacks and named registry dispatch.

Next safe extraction candidate: extract read-only IoT/smart-home status and history summaries, while leaving validation with connectivity checks, control commands, and config mutations in `command_router.py`.

## Phase 27 IoT/Smart-Home Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/iot_status.py`
- `tests/test_command_router_iot_status_handler.py`

Extracted/owned by the new handler:

- `smart home status`, `iot status`, `smart home devices`, `list smart home devices`
- `iot inventory`, `iot overview`, `smart home inventory`
- `what iot devices are connected`, `what smart devices are connected`, `list iot devices`
- `iot action history`, `smart home history`, `smart home action history`, `recent smart home actions`
- `smart home setup help`, `iot setup help`, `smart home setup`, `iot config help`

Ownership change:

- `device_status` now keeps phone link, face/security, and startup readiness summaries.
- `iot_status` owns smart-home setup/readiness help plus IoT status, inventory, and history summaries.

Not extracted:

- IoT control commands such as turn on/off or switch on/off
- `dispatch_iot_command(...)`, `resolve_iot_command(...)`, and `run_iot_command(...)`
- live validation/connectivity checks
- pairing/connect commands
- config mutations
- system actions and AI fallback

Registry update:

- Added default group `iot_status` after `system_health`.

Line count changed from 6,409 to 6,394 lines.

Next safe extraction candidate: extract read-only security/auth status summaries, while leaving auth, trust, lock/unlock, emergency, and permission mutations in `command_router.py`.

## Phase 28 Security/Auth Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/security_status.py`
- `tests/test_command_router_security_status_handler.py`

Extracted/owned by the new handler:

- `security status`, `assistant security status`, `system security status`
- `security alerts`, `show security alerts`, `security warnings`
- `security logs`, `show security logs`, `recent security logs`
- `my voice auth status`, `voice authentication status`, `voice auth status`
- `security admin status`, `is security admin mode on`
- `admin status`, `administrator status`, `full control status`, `settings access status`

Ownership change:

- `diagnostics` now keeps voice diagnostics, assistant doctor, and backend stability summaries.
- `security_status` owns security/auth/admin read-only summaries.

Not extracted:

- voice/face/PIN authentication actions
- assistant lock/unlock and lockdown actions
- trust/approve device mutations
- security admin mode enable/disable
- security PIN changes
- emergency mode/protocol/actions
- permission/security setting mutations
- log clearing/deletion
- system actions and AI fallback

Registry update:

- Added default group `security_status` after `iot_status`.

Line count changed from 6,394 to 6,392 lines.

Next safe extraction candidate: extract read-only emergency status/help summaries into a dedicated emergency_status handler, while leaving alert sending, location sharing, calls, lockdown, and emergency protocol triggers in `command_router.py`.

## Phase 29 Emergency Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/emergency_status.py`
- `tests/test_command_router_emergency_status_handler.py`

Extracted/owned by the new handler:

- `emergency mode status`, `what is emergency mode`, `emergency help`
- `emergency quick response`, `emergency quick responses`, `quick response system`
- `emergency protocol status`, `what is emergency protocol`

Not extracted:

- emergency protocol triggers
- alert/SOS sending
- safe-alert sending
- location sharing
- emergency contact calls/messages
- lockdown/lock/unlock
- emergency setting changes
- log clearing/deletion
- system actions and AI fallback

Registry update:

- Added default group `emergency_status` after `security_status`.

Line count changed from 6,392 to 6,393 lines.

Next safe extraction candidate: extract read-only preference/profile status summaries, while leaving preference updates, profile edits, memory writes, and AI fallback in `command_router.py`.

## Phase 30 Profile/Preference Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/profile_status.py`
- `tests/test_command_router_profile_status_handler.py`

Extracted/owned by the new handler:

- `tell me about myself`, `summarize my profile`, `my profile summary`, `who am i really`
- `personal snapshot`, `summarize my personal details`, `personal details snapshot`
- `what is my preferred language`, `my preferred language`, `preferred language`
- `what is my preferred tone`, `my preferred tone`, `preferred tone`

Not extracted:

- preferred language/tone updates
- profile edits
- name/profile/memory saves
- memory forget/delete/clear flows
- persona/personality setting changes
- config/database writes
- AI fallback

Registry update:

- Added default group `profile_status` after `emergency_status`.

Line count changed from 6,393 to 6,409 lines because profile callbacks now preserve existing intent-router and preference readback behavior.

Next safe extraction candidate: extract read-only developer/git/status summaries, while leaving file save/run, terminal launch, git mutation, and AI fallback in `command_router.py`.

## Phase 31 Developer/Git Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/developer_status.py`
- `tests/test_command_router_developer_status_handler.py`

Extracted/owned by the new handler:

- `developer mode status`, `what is developer mode`, `developer help`
- `developer summary`, `workspace summary`, `coding summary`
- `git status`, `check git status`, `developer git status`
- `current git branch`, `what branch am i on`, `git branch`
- `git remotes`, `show git remotes`, `github remotes`
- `recent commits`, `git recent commits`, `show recent commits`
- `github summary`, `git summary`, `repository summary`

Not extracted:

- `open terminal`, `open developer terminal`, `start terminal`
- `save and run current file`, `developer save and run`, `save run current file`
- `git add`, `git commit`, `git push`, `git pull`, `git reset`, `git checkout`, `git merge`, `git rebase`
- file save/edit/write operations
- script/terminal execution
- app launch
- developer setting changes
- AI fallback

Registry update:

- Added default group `developer_status` after `profile_status`.
- Moved developer mode/workspace summaries out of the generic `status` handler so ownership is explicit.

Line count changed from 6,409 to 6,400 lines.

Next safe extraction candidate: extract read-only notification/help/status summaries, while leaving notification sending, reminder mutations, popup actions, and AI fallback in `command_router.py`.

## Phase 32 Notification/Popup Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/notification_status.py`
- `tests/test_command_router_notification_status_handler.py`

Extracted/owned by the new handler:

- `notification status`, `notifications status`, `show notification status`, `notification summary`, `notifications summary`
- `notification help`, `notifications help`, `popup help`, `alert help`
- `popup status`, `popup alert status`, `alert popup status`, `popup summary`, `alert status summary`
- `reminder notification summary`, `reminder notification status`, `reminder popup status`, `event notification status`
- `notification history`, `notification list`, `show notification history`, `show notifications`, `recent notifications`

Not extracted:

- send notification/alert commands
- popup display actions
- reminder/task create/update/delete
- notification enable/disable commands
- notification setting changes
- AI fallback

Registry update:

- Added default group `notification_status` after `developer_status`.
- Added notification summary callbacks to `CommandContext`.

Line count changed from 6,400 to 6,490 lines because this phase introduced explicit read-only summary helpers for notification settings that were previously embedded in broad config output.

Next safe extraction candidate: extract read-only sound/audio/chime status summaries, while leaving sound setting changes, playback actions, voice start/stop, and AI fallback in `command_router.py`.

## Phase 33 Sound/Audio/Chime Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/audio_status.py`
- `tests/test_command_router_audio_status_handler.py`

Extracted/owned by the new handler:

- `sound status`, `sounds status`, `assistant sound status`
- `audio status`, `assistant audio status`, `audio summary`
- `chime status`, `voice chime status`, `wake chime status`, `desktop chime status`
- `notification sound summary`, `notification sound status`, `notification sounds`
- `voice audio readiness`, `voice audio status`, `microphone readiness`, `mic readiness`, `tts readiness`

Not extracted:

- sound/chime playback
- sound setting changes
- enable/disable sound or chime commands
- voice start/stop/listen/capture commands
- microphone capture
- TTS playback
- AI fallback

Registry update:

- Added default group `audio_status` after `notification_status`.
- Added audio summary callbacks to `CommandContext`.

Line count changed from 6,490 to 6,565 lines because this phase introduced explicit read-only sound/audio summary helpers.

Next safe extraction candidate: extract read-only overlay/pinned-command status summaries, while leaving pin/unpin/move actions, overlay enable/disable/hotkey changes, UI actions, and AI fallback in `command_router.py`.

## Phase 34 Overlay/Pinned-Command Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/overlay_status.py`
- `tests/test_command_router_overlay_status_handler.py`

Extracted/owned by the new handler:

- `overlay status`, `overlay summary`, `quick command overlay status`
- `quick overlay status`, `quick overlay summary`
- `list pinned commands`, `show pinned commands`, `pinned commands`, `pinned command summary`
- `hotkey status`, `hotkeys status`, `overlay hotkey status`, `quick overlay hotkey status`, `ocr hotkey status`
- `overlay help`, `quick overlay help`, `quick command overlay help`

Not extracted:

- pin/unpin pinned command actions
- move/reorder pinned command actions
- overlay enable/disable/toggle actions
- hotkey setting changes
- overlay open/close/hide/show actions
- UI click/type actions
- AI fallback

Registry update:

- Added default group `overlay_status` after `audio_status`.
- Added overlay summary callbacks to `CommandContext`.

Line count changed from 6,565 to 6,616 lines because this phase introduced explicit read-only overlay/hotkey summary helpers.

Next safe extraction candidate: extract read-only startup/interface mode status summaries, while leaving startup enable/disable, tray mode changes, interface mode changes, UI launch/open commands, and AI fallback in `command_router.py`.

## Phase 35 Startup/Interface Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/interface_status.py`
- `tests/test_command_router_interface_status_handler.py`

Extracted/owned by the new handler:

- `startup status`, `assistant startup status`, `startup launch status`
- `auto launch status`, `auto-launch status`, `startup auto launch status`
- `tray mode status`, `tray startup status`, `background mode status`
- `interface mode status`, `startup interface status`, `terminal mode status`
- `desktop mode status`, `backend mode status`, `desktop backend mode`, `desktop backend mode summary`
- `launcher readiness status`, `launcher status`, `desktop launcher status`, `backend launcher status`

Not extracted:

- startup enable/disable actions
- tray mode setting changes
- interface/terminal mode setting changes
- UI/desktop shell open commands
- app/window launch commands
- settings writes
- AI fallback

Registry update:

- Added default group `interface_status` after `overlay_status`.
- Added startup/interface summary callbacks to `CommandContext`.
- Moved `auto launch status` ownership out of `device_status`.

Line count changed from 6,616 to 6,663 lines because this phase introduced explicit read-only startup/interface summary helpers.

Next safe extraction candidate: extract read-only config/settings status summaries, while leaving every setting mutation and admin/escalation flow in `command_router.py`.

## Phase 36 Config/Settings Status Extraction

Status: COMPLETE

Created:

- `backend/app/core/commands/handlers/config_status.py`
- `tests/test_command_router_config_status_handler.py`

Extracted/owned by the new handler:

- `config status`, `configuration status`, `backend config status`
- `settings status`, `assistant settings status`
- `show settings`, `show config`, `settings`, `assistant settings summary`, `settings summary`
- `environment config readiness`, `environment readiness`, `config readiness`, `backend config readiness`
- `feature toggle summary`, `feature toggles`, `feature toggle status`, `feature status summary`

Not extracted:

- setting changes
- feature enable/disable commands
- admin/escalation flows
- API key/config writes
- security setting changes
- AI fallback

Registry update:

- Added default group `config_status` after `interface_status`.
- Added config/settings summary callbacks to `CommandContext`.

Line count changed from 6,663 to 6,737 lines because this phase introduced explicit read-only config/settings summary helpers.

Next safe extraction candidate: consolidate read-only summary helpers into smaller shared modules to reduce `command_router.py` boilerplate before extracting more command groups.
