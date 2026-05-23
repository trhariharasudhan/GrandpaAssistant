# GrandpaAssistant Personal Assistant Release Snapshot

Snapshot date: 2026-05-19

## Summary

GrandpaAssistant now has a stable context-aware local personal assistant layer integrated through `chat_service`. The system supports deterministic intent understanding, short-term follow-up context, safe local action execution, screen-aware planning, reminder scheduling, optional Windows startup, optional wake-word voice runtime, a registered tool/skill system, safe LLM-assisted planning fallback, and structured long-term memory with conflict resolution.

Runtime code was not changed for this report.

## Stable Capabilities

### Conversation and Context

- Detects local-action intents without hardcoding only one sentence.
- Resolves short follow-ups like `yes`, `do it`, `close it`, and `check everything`.
- Stores short-term context per session.
- Asks missing-detail questions before acting.
- Falls back to normal chat when no personal-assistant action is appropriate.

### Local Actions

- Volume increase/decrease/mute/unmute through safe local adapter.
- Allowlisted app open.
- Close only assistant-tracked/allowlisted app processes.
- Safe folder creation under configured local roots.
- Browser URL open and safe YouTube search.
- Media key control when active media context exists.

### Screen Awareness

- Active-window metadata informs planning.
- Explicit screen-read requests can trigger screenshot/OCR summary.
- No hidden background screenshot capture.
- Screen debug metadata remains opt-in.

### Reminders and Scheduler

- Creates structured reminders.
- Handles incomplete reminder details.
- Lists, completes, and cancels reminders.
- Checks due reminders.
- Optional managed scheduler loop can notify while backend/CLI is running.
- Scheduler is disabled by default unless `GRANDPA_REMINDER_SCHEDULER_ENABLED=1`.

### Voice Runtime

- Optional managed wake-word loop.
- Configurable wake word.
- Routes recognized command through the same assistant pipeline.
- Uses existing voice/STT/TTS adapters if available.
- Disabled by default unless `GRANDPA_VOICE_RUNTIME_ENABLED=1`.
- Chat enable flow requires confirmation.

### Windows Startup

- Checks current-user startup status.
- Enables startup only after confirmation.
- Disables startup safely.
- Does not require admin/system-wide startup mutation.

### Tool Registry

- Every current local action is represented as a registered tool.
- Tools declare description, intents, capabilities, required parameters, risk level, permission requirement, confirmation requirement, availability, executor, and safe failure message.
- Capability discovery uses the registry instead of hallucinating unsupported tools.
- Unsupported actions are handled by `unsupported_action`.

### LLM-Assisted Planner Fallback

- Deterministic planner remains preferred.
- LLM planner is optional and only used when enabled/configured.
- LLM can only propose registered tools.
- Plan JSON is validated before execution.
- Invalid JSON, invented tools, prompt injection, and unsafe plans are rejected.

### Long-Term Memory

- Structured local memory, not raw chat dumps.
- Categories include preferences, favorite apps, work context, communication style, known devices, and assistant behavior preferences.
- Sensitive content is blocked.
- Low-quality/temporary memories are rejected.
- Conflicts are detected.
- Natural conflict follow-up is supported:
  - `yes`, `yes update it`, `use new one` -> update
  - `no`, `keep old one`, `don't change` -> keep existing
  - `cancel` -> clear pending conflict
- Stale, archived, conflicted, and low-confidence memories are ignored by planner.
- Review and cleanup tools summarize memory quality without deleting silently.

## Current Module Inventory

Core personal assistant:

- `backend/app/core/personal_assistant/__init__.py`
- `backend/app/core/personal_assistant/context.py`
- `backend/app/core/personal_assistant/intent_engine.py`
- `backend/app/core/personal_assistant/planner.py`
- `backend/app/core/personal_assistant/tool_registry.py`
- `backend/app/core/personal_assistant/executor.py`
- `backend/app/core/personal_assistant/service.py`
- `backend/app/core/personal_assistant/llm_planner.py`
- `backend/app/core/personal_assistant/screen_context.py`
- `backend/app/core/personal_assistant/reminder_engine.py`
- `backend/app/core/personal_assistant/reminder_scheduler.py`
- `backend/app/core/personal_assistant/notifications.py`
- `backend/app/core/personal_assistant/voice_runtime.py`
- `backend/app/core/personal_assistant/windows_startup_manager.py`
- `backend/app/core/personal_assistant/memory_manager.py`

Integration:

- `backend/app/core/chat_service.py`
- `backend/app/api/chat_api.py`
- `backend/app/api/web_api.py`
- `backend/app/cli/chat.py`
- `backend/app/services/local_action_executor.py`
- `backend/app/shared/window_awareness.py`

Developer test pack:

- `scripts/dev/personal_assistant_e2e.py`
- `docs/PERSONAL_ASSISTANT_E2E_TEST_PACK.md`

Tool snapshot:

- `docs/personal_assistant_tool_registry.json`

## Feature Flags and Environment Variables

Off by default:

- `GRANDPA_REMINDER_SCHEDULER_ENABLED`
- `GRANDPA_VOICE_RUNTIME_ENABLED`
- `GRANDPA_ASSISTANT_ENABLE_LLM_PLANNER`
- `GRANDPA_USE_RUNTIME_PROMPTS`
- `GRANDPA_USE_PROJECT_CONTEXT`

Other controls:

- `GRANDPA_PERSONAL_ASSISTANT_DEBUG`
- `GRANDPA_PERSONAL_ASSISTANT_MEMORY_PATH`
- `GRANDPA_REMINDER_CHECK_INTERVAL_SECONDS`
- `GRANDPA_WAKE_WORD`
- `GRANDPA_VOICE_LISTEN_TIMEOUT_SECONDS`
- `GRANDPA_VOICE_IDLE_SLEEP_SECONDS`
- `GRANDPA_ASSISTANT_PLANNER_PROVIDER`

## Safety Checkpoint

Confirmed architecture boundaries:

- No command router rewrite required.
- No frontend/mobile dependency.
- No public API route added for personal-assistant internals.
- High-risk/destructive actions are blocked or confirmation-gated.
- Voice and reminder background loops are opt-in and lifecycle-managed.
- Screenshot/OCR is explicit-request driven.
- Memory is local-first and structured.
- Tool registry is the single execution gate for personal assistant tools.

## Validation Commands

Focused suite:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_personal_assistant_long_term_memory tests.test_personal_assistant_voice_runtime tests.test_personal_assistant_windows_startup_manager tests.test_personal_assistant_reminder_scheduler tests.test_personal_assistant_reminder_engine tests.test_context_aware_personal_assistant tests.test_chat_service_context_aware_assistant tests.test_personal_assistant_local_actions tests.test_screen_aware_personal_assistant tests.test_personal_assistant_tool_registry tests.test_personal_assistant_llm_planner tests.test_personal_assistant_e2e_runner -v
```

E2E:

```powershell
.venv\Scripts\python.exe scripts\dev\personal_assistant_e2e.py --scheduler-once
```

Full discovery:

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

## Latest Validation Result

Current checkpoint validation passed:

- E2E mock runner: PASS
- Focused personal assistant suite: PASS
- Full unittest discovery: PASS
- Terminal chatbot smoke: PASS
- Startup smoke: PASS

## Known Limitations

- Real microphone and OCR flows are mainly validated through safe mock paths.
- One memory conflict is resolved at a time.
- Memory cleanup is suggestion-first, not automatic deletion.
- Calendar/email/message/payment actions are not active personal-assistant tools.
- LLM planner is not a replacement for deterministic safety checks.
- Safe personal-assistant status is available through the CLI and localhost/admin API, but there is no full dashboard UI yet.

## Recommended Next Phase

Recommended next phase: a read-only runtime dashboard design for personal-assistant status.

The dashboard should reuse safe metadata only:

- registered tools
- enabled feature flags
- scheduler status
- voice runtime status
- memory status/counts
- recent debug summaries without raw private content

It should not expose prompt bodies, screenshots, microphone audio, secrets, or full memory dumps.
