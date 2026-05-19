# GrandpaAssistant Personal Assistant Architecture

Status: stable checkpoint, 2026-05-19

This document describes the current local personal assistant layer after the recent context, screen, voice, reminder, tool-registry, LLM-planner, and long-term memory upgrades. It is a backend-only architecture note. It does not describe `command_router.py` extraction work except where the old router remains a compatibility/public command entrypoint.

## Current Architecture Overview

GrandpaAssistant now has a dedicated `core.personal_assistant` layer that sits inside the existing backend chat path. It is designed to understand user intent, keep short-term context, use safe local tools, and personalize behavior with structured local memory.

Primary integration point:

- `backend/app/core/chat_service.py`
  - Calls `core.personal_assistant.service.handle_personal_assistant_message(...)` before provider fallback.
  - Normal chat still falls through to the configured provider/fallback when the personal assistant does not handle a message.
  - Debug metadata is opt-in.

Core modules:

- `backend/app/core/personal_assistant/context.py`
  - Short-term session context.
  - Pending plans, missing details, reminder details, target app/object, pending memory conflict, last executed action.
- `backend/app/core/personal_assistant/intent_engine.py`
  - Deterministic intent detection.
  - Handles action intents, follow-ups, reminders, memory commands, startup/voice controls, screen/media commands.
- `backend/app/core/personal_assistant/planner.py`
  - Converts intent + context + screen data + memory hints into `AssistantActionPlan`.
  - Resolves follow-ups like “yes”, “do it”, “close it”, “check everything”, and pending memory conflicts.
- `backend/app/core/personal_assistant/tool_registry.py`
  - Declarative registry for local tools/adapters.
  - Provides tool metadata, validation, capability discovery, and execution wrapper.
- `backend/app/core/personal_assistant/executor.py`
  - Executes validated plans through the registry.
  - Maintains short-term context after execution.
- `backend/app/core/personal_assistant/service.py`
  - Orchestrates the whole assistant pipeline.
  - Builds safe debug metadata.
- `backend/app/core/personal_assistant/llm_planner.py`
  - Optional safe LLM-assisted planner fallback.
  - Only proposes registered tools; never executes directly.
- `backend/app/core/personal_assistant/screen_context.py`
  - Active-window and explicit screenshot/OCR context foundation.
- `backend/app/core/personal_assistant/reminder_engine.py`
  - Structured reminders, due checks, completion, cancellation.
- `backend/app/core/personal_assistant/reminder_scheduler.py`
  - Optional managed reminder scheduler loop.
- `backend/app/core/personal_assistant/notifications.py`
  - Notification abstraction with safe fallback.
- `backend/app/core/personal_assistant/voice_runtime.py`
  - Optional managed wake-word voice runtime.
- `backend/app/core/personal_assistant/windows_startup_manager.py`
  - Optional current-user Windows startup integration.
- `backend/app/core/personal_assistant/memory_manager.py`
  - Structured long-term memory, review, cleanup, conflict handling, persistence.

Supporting adapters:

- `backend/app/services/local_action_executor.py`
  - Windows-safe local actions: volume, app open/close, media keys, browser open, safe folder creation.
- `backend/app/shared/window_awareness.py`
  - Active-window awareness foundation.

Developer validation:

- `scripts/dev/personal_assistant_e2e.py`
  - Mock-safe end-to-end conversation pack through the same `chat_service` path.

Lifecycle hooks:

- `backend/app/api/chat_api.py`
  - Starts/stops reminder scheduler and voice runtime according to environment flags.
- `backend/app/api/web_api.py`
  - Same lifecycle guard for web runtime.
- `backend/app/cli/chat.py`
  - Terminal chat starts/stops optional scheduler and voice runtime according to flags.

## Personal Assistant Pipeline

Current high-level flow:

```text
user message
  -> chat_service.build_chat_reply(...)
  -> personal_assistant.service.handle_personal_assistant_message(...)
  -> intent_engine.detect_intent(...)
  -> service._merge_follow_up(...)
  -> screen_context.get_screen_context(...)
  -> planner.build_action_plan(...)
  -> optional llm_planner fallback when deterministic confidence is low
  -> missing-detail question OR confirmation question OR execution
  -> tool_registry.validate + execute_registered_tool(...)
  -> executor.execute_plan(...)
  -> response payload
  -> short-term context update
  -> optional debug metadata
```

Important behavior:

- If the personal assistant cannot confidently handle the message, it returns `handled=False` and chat provider fallback continues.
- “Yes” and “do it” are context-sensitive and resolve pending work.
- Pending memory conflicts take priority over generic action confirmations.
- Risky actions ask first.
- Unsupported actions return a specific missing-adapter explanation.

## Screen-Aware Flow

Screen awareness is local and explicit/safe:

```text
user message
  -> intent detects screen/media/current-window need
  -> screen_context gathers active-window metadata
  -> optional screenshot/OCR only for explicit screen-read requests
  -> planner combines user intent + active window + context
  -> tool registry executes safe local action or asks follow-up
```

Examples:

- “pause it” uses active media context if available.
- “close this” requires confirmation and tracked/allowlisted context.
- “read this error” triggers explicit screenshot/OCR path.
- “search this on Google” uses clipboard/selected text if safely available.

Safety boundaries:

- No hidden background screenshots.
- No cloud upload by default.
- No UI clicking/typing automation in this layer.
- Destructive UI actions remain blocked or require explicit confirmation.

## Voice Runtime Flow

Voice runtime is optional and off by default.

```text
GRANDPA_VOICE_RUNTIME_ENABLED=1
  -> lifecycle starts VoiceRuntimeManager
  -> passive wake listener waits for "Grandpa" / "Hey Grandpa"
  -> command transcript is captured
  -> command routes through chat_service/personal assistant
  -> normal assistant response is sent to TTS adapter
```

Controls:

- `enable_voice_runtime`
- `disable_voice_runtime`
- `voice_runtime_status`

Safety boundaries:

- No voice runtime starts unless enabled by env flag or explicit tool flow.
- Enabling from chat requires confirmation.
- STT/TTS adapters fail safely if unavailable.
- Normal replies do not expose debug internals.

## Reminder Scheduler Flow

Reminder creation:

```text
message
  -> intent: create_reminder / meeting_reminder
  -> missing details collected if needed
  -> reminder_engine.create_reminder(...)
  -> productivity store persists structured reminder
```

Due reminder flow:

```text
GRANDPA_REMINDER_SCHEDULER_ENABLED=1
  -> ReminderScheduler starts during app/CLI lifecycle
  -> periodic check_due_reminders()
  -> due reminders marked due
  -> notifications sent through abstraction
  -> duplicate notifications avoided
```

Controls:

- `create_reminder`
- `list_reminders`
- `complete_reminder`
- `cancel_reminder`
- `check_due_reminders`

Safety boundaries:

- Scheduler is disabled by default in tests.
- Unit tests use single-tick/no-sleep paths.
- Notification failures do not crash scheduler.
- Ambiguous reminder completion/cancellation asks which reminder.

## Long-Term Memory Flow

Memory is structured, local-first, and quality-gated. It is not a raw conversation dump.

Memory fields include:

- `memory_id`
- `category`
- `key`
- `value`
- `source`
- `confidence`
- `created_at`
- `updated_at`
- `last_used_at`
- `pinned`
- `manual`
- `retention_policy`
- `status`
- `quality_score`
- `conflict_status`
- `pending_value`
- `history`

Default persistence:

- `runtime/data/personal_assistant_memory.json`
- Override for tests/development: `GRANDPA_PERSONAL_ASSISTANT_MEMORY_PATH`

Memory categories:

- `user_preferences`
- `recurring_tasks`
- `favorite_apps`
- `common_locations`
- `communication_preferences`
- `work_context`
- `assistant_behavior_preferences`
- `reminders_summary`
- `known_devices`

Memory commands/tools:

- `remember_this`
- `forget_memory`
- `list_memories`
- `memory_status`
- `memory_opt_out`
- `review_memories`
- `cleanup_memories`
- `update_memory`
- `memory_conflicts`
- `resolve_memory_conflict`

Conflict flow:

```text
new memory conflicts with existing category + key
  -> uncertain source creates unresolved conflict
  -> assistant asks whether to update
  -> pending_memory_conflict stored in short-term context
  -> next reply resolves:
       yes / use new one -> update
       no / keep old one -> keep old
       cancel -> clear conflict
  -> history trail updated
```

Memory planner usage:

- Memory supports intent but does not override explicit user intent.
- Manual/pinned memories rank first.
- Low-confidence, stale, archived, and conflicted memories are ignored.
- Examples:
  - “open my editor” may use saved preferred editor.
  - “play music” may use saved favorite music.

## Tool Registry Table

The machine-readable registry snapshot lives at:

- `docs/personal_assistant_tool_registry.json`

Current tool groups:

| Area | Tools |
| --- | --- |
| Audio | `volume_control`, `media_key_control` |
| Apps/Windows | `open_app`, `close_tracked_app`, `startup_status`, `enable_startup`, `disable_startup` |
| Diagnostics | `system_diagnostics` |
| Reminders | `create_reminder`, `list_reminders`, `complete_reminder`, `cancel_reminder`, `check_due_reminders` |
| Voice | `voice_runtime_status`, `enable_voice_runtime`, `disable_voice_runtime` |
| Memory | `remember_this`, `list_memories`, `forget_memory`, `memory_status`, `memory_opt_out`, `review_memories`, `cleanup_memories`, `update_memory`, `memory_conflicts`, `resolve_memory_conflict` |
| Screen | `active_window_context`, `screen_read`, `search_selected_google` |
| Web | `open_website` |
| Files | `create_folder` |
| Help/Safety | `capability_discovery`, `unsupported_action` |

## Safety Model and Risk Levels

Registry risk levels:

- `safe_read`
  - Read-only checks/status/summaries.
  - Examples: diagnostics, memory review, startup status.
- `safe_local_action`
  - Reversible or low-risk local actions.
  - Examples: volume control, create reminder, disable startup.
- `medium_confirmation`
  - Requires explicit user confirmation.
  - Examples: open app, close tracked app, enable startup, enable voice runtime.
- `high_confirmation`
  - Reserved for future high-risk but potentially allowed actions.
- `blocked`
  - Unsupported or unsafe capabilities.
  - Examples: payments, destructive deletion, external communication without adapter.

Additional safety rules:

- The LLM planner can only propose registered tools.
- Tool parameters are validated before execution.
- Screen capture is explicit only.
- Startup is current-user only and requires confirmation to enable.
- Voice runtime is off by default and confirmation-gated from chat.
- Memory blocks obvious secrets and rejects temporary/low-quality memories.
- Cleanup suggests; it does not silently delete multiple memories.

## Debug Metadata Behavior

Debug metadata is internal/opt-in and should not leak in normal responses.

It includes:

- detected intent
- confidence
- planner source
- selected tool
- tool availability
- missing fields
- permission decision
- executor result summary
- active window summary
- screenshot/OCR summary when applicable
- reminder scheduler status
- voice runtime status
- memory candidates/used/ignored reasons
- LLM planner validation details when attempted

It does not intentionally expose:

- raw prompts
- full memory dumps in normal response
- hidden screenshots
- secrets
- private audio

## Environment Variables

Prompt/project context:

- `GRANDPA_USE_RUNTIME_PROMPTS`
- `GRANDPA_USE_PROJECT_CONTEXT`

Personal assistant debug:

- `GRANDPA_PERSONAL_ASSISTANT_DEBUG`

LLM planner:

- `GRANDPA_ASSISTANT_ENABLE_LLM_PLANNER`
- `GRANDPA_ASSISTANT_PLANNER_PROVIDER`

Long-term memory:

- `GRANDPA_PERSONAL_ASSISTANT_MEMORY_PATH`

Reminder scheduler:

- `GRANDPA_REMINDER_SCHEDULER_ENABLED`
- `GRANDPA_REMINDER_CHECK_INTERVAL_SECONDS`

Voice runtime:

- `GRANDPA_VOICE_RUNTIME_ENABLED`
- `GRANDPA_WAKE_WORD`
- `GRANDPA_VOICE_LISTEN_TIMEOUT_SECONDS`
- `GRANDPA_VOICE_IDLE_SLEEP_SECONDS`

Runtime paths:

- `GRANDPA_ASSISTANT_RUNTIME_DIR`
- `GRANDPA_ASSISTANT_DATA_DIR`
- `GRANDPA_ASSISTANT_LOGS_DIR`
- `GRANDPA_ASSISTANT_CACHE_DIR`
- `GRANDPA_ASSISTANT_CONFIG_DIR`

## Test and E2E Commands

Focused personal assistant suite:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_personal_assistant_long_term_memory tests.test_personal_assistant_voice_runtime tests.test_personal_assistant_windows_startup_manager tests.test_personal_assistant_reminder_scheduler tests.test_personal_assistant_reminder_engine tests.test_context_aware_personal_assistant tests.test_chat_service_context_aware_assistant tests.test_personal_assistant_local_actions tests.test_screen_aware_personal_assistant tests.test_personal_assistant_tool_registry tests.test_personal_assistant_llm_planner tests.test_personal_assistant_e2e_runner -v
```

E2E mock runner:

```powershell
.venv\Scripts\python.exe scripts\dev\personal_assistant_e2e.py --scheduler-once
```

Full test discovery:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Terminal smoke:

```powershell
.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "hi da"
```

Startup smoke:

```powershell
.venv\Scripts\python.exe scripts\dev\startup_smoke_check.py
```

## Known Limitations

- Memory extraction is deterministic and conservative.
- Only one pending memory conflict is resolved at a time.
- Cleanup suggests stale/low-quality memories but does not bulk-delete automatically.
- Voice wake-word runtime requires available local microphone/STT adapters.
- Real microphone/screen/app actions are mostly mock-tested in e2e for safety.
- LLM planner is optional and disabled unless configured.
- No broad UI automation/click/type execution is enabled here.
- No cloud sync for memory/reminders by default.
- `command_router.py` remains public legacy entrypoint and is intentionally not part of this layer’s refactor.

## Future Roadmap

Recommended next phases:

- Add richer memory categories and user-approved sensitive-memory flow.
- Add memory conflict selection when multiple conflicts exist.
- Add admin/debug read-only status endpoint for personal assistant internals if needed.
- Improve local wake-word/STT provider availability checks.
- Add safe calendar integration through the tool registry.
- Add richer screen semantics while keeping explicit screenshot permissions.
- Add persistent audit summaries for tool executions.
- Add planner self-review for multi-step tasks without executing unapproved actions.
