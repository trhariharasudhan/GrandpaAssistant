# Phase 11 Memory Context Injection

## Purpose

Phase 11 adds safe optional `memory_context` preparation for runtime prompts. The integration remains limited to `chat_service`, behind `GRANDPA_USE_RUNTIME_PROMPTS`, and legacy behavior remains the default.

## Sanitization

`backend/app/core/prompt_memory_context.py` accepts strings, lists, dictionaries, and malformed values safely.

The sanitizer:

- compacts whitespace
- labels memory as contextual hints, not guaranteed facts
- limits output length
- excludes obvious sensitive keys and lines
- returns an empty string instead of raising

Sensitive labels excluded include:

- password
- token
- api_key
- secret
- credential
- otp
- pin

## Current Limitation

`chat_service` currently has recent session history but no separate long-term or retrieved memory source in this path. Phase 11 makes memory injection ready and testable, but the live provider call still passes `None` until an existing memory source is intentionally connected.

## No Exposure Rule

Memory content must not appear in:

- runtime metadata
- status helper output
- CLI status output
- logs
- docs
- API responses

Metadata may report only whether memory context was included.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_prompt_memory_context -v
```

```powershell
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --check
```

## Next Phase Suggestion

Phase 12 should add a planner/task-decomposition prompt mode or design the exact memory source that can safely feed `memory_context` without exposing private data.
