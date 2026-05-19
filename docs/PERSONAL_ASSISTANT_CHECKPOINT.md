# GrandpaAssistant Personal Assistant Checkpoint

Date: 2026-05-19

This checkpoint captures the context-aware local personal-assistant upgrade before the Git milestone commit.

## Summary

GrandpaAssistant now has a local personal-assistant layer that can interpret user intent, use short-term context, plan safe local actions, execute registered tools, and preserve useful structured long-term memory. The implementation keeps `process_command(...)` and the legacy command router path intact; the new assistant layer is integrated through `chat_service` and the terminal/API chat paths.

## Completed Capabilities

- Context-aware request handling through `chat_service`.
- Follow-up resolution for replies such as `yes`, `do it`, `close it`, and memory conflict decisions.
- Safe local action execution for volume control, app open/close, diagnostics, media keys, website/search helpers, and safe folder creation.
- Tool/adapter registry with discoverable tool metadata, risk levels, required parameters, permission requirements, and executor wrappers.
- Reminder creation, listing, completion, cancellation, due-checking, local notification fallback, and managed scheduler support.
- Screen-aware planning based on active window context, with explicit-request-only screenshot/OCR foundation.
- Voice runtime foundation with wake-word flow, controlled by environment flags and mock-tested without microphone dependency.
- Windows startup integration with explicit confirmation and current-user startup-folder behavior.
- Structured long-term memory with categories, local persistence, quality scoring, stale/conflict handling, review/cleanup helpers, and natural conflict follow-up resolution.
- Optional LLM-assisted planner fallback that can only propose registered tools and must pass validation before execution.
- Safe diagnostics/status CLI for the personal-assistant layer.
- Repeatable mock e2e runner for future regression checks.

## Architecture Modules

Primary integration:

- `backend/app/core/chat_service.py`
- `backend/app/api/chat_api.py`
- `backend/app/api/web_api.py`
- `backend/app/cli/chat.py`

Personal assistant core:

- `backend/app/core/personal_assistant/context.py`
- `backend/app/core/personal_assistant/intent_engine.py`
- `backend/app/core/personal_assistant/planner.py`
- `backend/app/core/personal_assistant/llm_planner.py`
- `backend/app/core/personal_assistant/tool_registry.py`
- `backend/app/core/personal_assistant/executor.py`
- `backend/app/core/personal_assistant/service.py`
- `backend/app/core/personal_assistant/screen_context.py`
- `backend/app/core/personal_assistant/reminder_engine.py`
- `backend/app/core/personal_assistant/reminder_scheduler.py`
- `backend/app/core/personal_assistant/notifications.py`
- `backend/app/core/personal_assistant/voice_runtime.py`
- `backend/app/core/personal_assistant/windows_startup_manager.py`
- `backend/app/core/personal_assistant/memory_manager.py`

Supporting adapters and tools:

- `backend/app/services/local_action_executor.py`
- `backend/app/shared/window_awareness.py`
- `scripts/dev/personal_assistant_e2e.py`
- `scripts/dev/personal_assistant_status.py`

Docs and snapshots:

- `docs/PERSONAL_ASSISTANT_ARCHITECTURE.md`
- `docs/PERSONAL_ASSISTANT_RELEASE_SNAPSHOT.md`
- `docs/PERSONAL_ASSISTANT_E2E_TEST_PACK.md`
- `docs/personal_assistant_tool_registry.json`

## Safety Model

- Tool registry risk levels:
  - `safe_read`
  - `safe_local_action`
  - `medium_confirmation`
  - `high_confirmation`
  - `blocked`
- Risky actions require confirmation before execution.
- Unsupported or unsafe actions route to `unsupported_action` with a clear adapter-missing explanation.
- The LLM planner, when enabled, may only propose a structured JSON plan using registered tools.
- Screenshot/OCR is explicit-request-only and never runs from the status CLI.
- Voice runtime and reminder scheduler are environment-gated and disabled by default.
- Memory is local-first, structured, inspectable, and deletable; sensitive content is blocked by default.
- The status CLI does not expose memory values, raw voice transcripts, screenshots, prompt bodies, secrets, or user conversations.

## Environment Flags

- `GRANDPA_ASSISTANT_DEBUG`
- `GRANDPA_ASSISTANT_ENABLE_LLM_PLANNER`
- `GRANDPA_ASSISTANT_PLANNER_PROVIDER`
- `GRANDPA_REMINDER_SCHEDULER_ENABLED`
- `GRANDPA_REMINDER_CHECK_INTERVAL_SECONDS`
- `GRANDPA_VOICE_RUNTIME_ENABLED`
- `GRANDPA_WAKE_WORD`
- `GRANDPA_VOICE_LISTEN_TIMEOUT_SECONDS`
- `GRANDPA_PERSONAL_ASSISTANT_MEMORY_PATH`

## Validation Results

Latest checkpoint validation:

- `scripts/dev/personal_assistant_status.py --check`: PASS
- `scripts/dev/personal_assistant_e2e.py`: PASS
- Focused personal-assistant unittest suite: PASS, 109 tests
- Full unittest discovery: PASS
- `py_compile` for changed Python files: PASS
- Terminal chatbot smoke: PASS
- Startup smoke: PASS

Focused test command:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_personal_assistant_long_term_memory tests.test_personal_assistant_voice_runtime tests.test_personal_assistant_windows_startup_manager tests.test_personal_assistant_reminder_scheduler tests.test_personal_assistant_reminder_engine tests.test_context_aware_personal_assistant tests.test_chat_service_context_aware_assistant tests.test_personal_assistant_local_actions tests.test_screen_aware_personal_assistant tests.test_personal_assistant_tool_registry tests.test_personal_assistant_llm_planner tests.test_personal_assistant_e2e_runner tests.test_personal_assistant_status_cli -v
```

Full discovery command:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Developer checks:

```powershell
.venv\Scripts\python.exe scripts/dev/personal_assistant_status.py --check
.venv\Scripts\python.exe scripts/dev/personal_assistant_e2e.py
.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "hi da"
.venv\Scripts\python.exe scripts/dev/startup_smoke_check.py
```

## Known Limitations

- Real microphone, OCR, toast notification, and LLM provider behavior are adapter-dependent and mostly mock-tested in the core suite.
- The standalone status CLI reports scheduler configuration for the current process; it does not introspect a different already-running backend process.
- App closing is intentionally limited to tracked and allowlisted apps.
- Memory conflict resolution handles one pending conflict at a time.
- Memory cleanup suggests actions instead of silently deleting multiple memories.
- The LLM-assisted planner is optional and must remain behind validation and registry restrictions.
- No broad purchasing, payment, messaging, or destructive file-operation automation is enabled.

## Next Recommended Phases

1. Add an admin-only design for a future personal-assistant status endpoint, reusing the safe CLI fields.
2. Add deeper real-device/manual validation for microphone, OCR, and toast notification adapters.
3. Add a read-only runtime dashboard plan for scheduler, voice runtime, and memory health.
4. Expand reminder recurrence only after the scheduler remains stable across app restarts.
5. Add richer memory review UX while keeping deletion/update confirmation explicit.

## Suggested Commit Message

```text
feat: add context-aware local personal assistant layer
```
