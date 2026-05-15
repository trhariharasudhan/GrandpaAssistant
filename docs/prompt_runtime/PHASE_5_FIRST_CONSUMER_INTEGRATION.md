# Phase 5 First Consumer Integration

## Selected Integration Point

The first feature-flagged consumer is `backend/app/core/chat_service.py`.

This was chosen because it has a single private system prompt construction path for normal chat provider calls. It is narrower and safer than changing `web_api.py`, `chat_api.py`, or `command_router.py`.

## Legacy Fallback

`chat_service` now separates its existing prompt text into `_build_legacy_system_prompt()`.

`_build_system_prompt()` calls:

```python
resolve_chat_system_prompt(_build_legacy_system_prompt())
```

The resolver delegates to `get_runtime_system_prompt(...)` with the legacy prompt as fallback. When runtime prompts are disabled, the legacy prompt is returned unchanged.

## Enable Runtime Prompts

For manual testing:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
```

Disable safely:

```powershell
Remove-Item Env:\GRANDPA_USE_RUNTIME_PROMPTS
```

Accepted enabled values are `1`, `true`, `yes`, and `on`.

## Manual Test

Run the terminal chat smoke path with runtime prompts enabled:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
.\.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "hi da"
```

Then clear the environment variable to return to legacy prompt behavior.

## Command Router Boundary

`command_router.py` was not touched. Phase 5 only changes the normal chat-service system prompt resolver and leaves routing, system actions, automation, and command behavior unchanged.

## Known Limitations

- Only default mode is used in this phase.
- API-specific route prompt builders are not migrated.
- Terminal chatbot provider prompts are not directly migrated unless they flow through `chat_service`.
- Runtime prompts remain off by default.

## Next Steps

Phase 6 should add one more guarded integration or add mode selection tests before expanding runtime prompts into API/chat route adapters.
