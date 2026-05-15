# Prompt Runtime Route Ownership Plan

## Current Prompt Runtime Modules And Owners

- `backend/app/core/prompt_loader.py`: prompt file loading.
- `backend/app/core/prompt_builder.py`: prompt composition.
- `backend/app/core/prompt_modes.py`: supported mode validation.
- `backend/app/core/prompt_mode_resolver.py`: conservative mode detection.
- `backend/app/core/runtime_prompt_adapter.py`: legacy/runtime prompt selection.
- `backend/app/core/prompt_runtime_observability.py`: safe metadata.
- `backend/app/core/prompt_runtime_status.py`: safe internal status.
- `backend/app/core/prompt_memory_context.py`: memory context sanitization.
- `backend/app/core/planner_prompt_payload.py`: internal planner payload construction.
- `backend/app/core/planner_payload_verifier.py`: internal planner payload verification.
- `scripts/dev/prompt_runtime_status.py`: local CLI diagnostics.

## Current Consumer

`chat_service` is the only runtime prompt consumer.

Runtime prompts remain behind `GRANDPA_USE_RUNTIME_PROMPTS` and are off by default.

## Future Admin Diagnostics Endpoint Owner

Preferred future owner:

- `backend/app/api/admin.py`, if admin routes are centralized.

Alternative future owner:

- `backend/app/api/prompt_runtime_admin.py`, if no central admin route module exists.

The endpoint should call `get_prompt_runtime_status()` and return only the safe status shape.

## Modules That Must Not Own Diagnostics

The diagnostics endpoint must not be owned by:

- `backend/app/core/command_router.py`
- frontend/mobile code
- broad public chat APIs
- route modules intended for unauthenticated user chat
- automation or tool execution modules

## Safe Integration Boundaries

Allowed future boundary:

```text
admin/local-only route -> get_prompt_runtime_status() -> safe JSON response
```

Forbidden future boundary:

```text
public chat route -> prompt bodies/status/debug internals
command router -> prompt diagnostics
diagnostics endpoint -> command/tool execution
```

## Migration Strategy

1. Keep CLI-only diagnostics as the default.
2. Confirm the admin route location.
3. Add authentication or localhost-only guard.
4. Add tests for forbidden fields and access control.
5. Register the route only after security tests pass.
6. Keep rollback simple by removing the admin router include.
