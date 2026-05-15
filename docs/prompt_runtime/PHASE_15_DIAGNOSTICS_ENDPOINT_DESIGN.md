# Phase 15 Diagnostics Endpoint Design

## A. Purpose

A future admin-only prompt-runtime diagnostics endpoint may be useful for checking runtime prompt readiness from the backend without opening a shell.

It could help an administrator verify:

- whether runtime prompts are enabled
- which prompt modes are supported
- which prompt files are present or missing
- whether the status payload is safe to expose
- whether the reference prompt folder is unused

It is not implemented yet because any HTTP endpoint increases exposure risk. The existing local CLI remains the safer diagnostics surface until admin authentication, route ownership, and response-shape tests are designed and reviewed.

## B. Proposed Route

Future route:

```text
GET /api/admin/prompt-runtime/status
```

## C. Ownership

Recommended owner:

- `backend/app/api/admin.py` if admin routes are centralized.

Fallback owner:

- `backend/app/api/prompt_runtime_admin.py` only if there is no existing centralized admin API module.

The route should not live in broad public chat APIs.

## D. Security Requirements

The future endpoint must be:

- localhost-only or authenticated admin-only
- unavailable to public clients
- read-only
- protected from prompt body exposure
- protected from memory, user message, and chat history exposure
- protected from secrets or environment dumps
- protected from reference prompt content exposure
- unable to execute commands or tools
- optionally rate-limited or guarded behind a development/admin flag

## E. Response Shape

The response should be based on `get_prompt_runtime_status()`:

```json
{
  "runtime_enabled": false,
  "env_var": "GRANDPA_USE_RUNTIME_PROMPTS",
  "supported_modes": [],
  "active_consumer": "chat_service",
  "available_prompt_files": [],
  "missing_expected_prompt_files": [],
  "metadata_fields": [],
  "reference_folder_used": false,
  "safe_to_expose": true
}
```

Only relative prompt file paths should be returned.

## F. Explicitly Forbidden Fields

The endpoint must never return:

- `system_prompt`
- `prompt_text`
- `memory_context`
- `user_request`
- `chat_history`
- `secrets`
- environment values other than boolean runtime flag state
- reference prompt contents
- prompt file contents

## G. Threat Model

Risks:

- accidental prompt leakage
- exposing memory or private user data
- remote access abuse
- using diagnostics as an execution path
- leaving a debug endpoint open in production
- leaking secret-related environment variables
- exposing reference prompt folder details beyond a safe false/true usage flag

## H. Future Validation Plan

Required tests before implementation:

- endpoint requires admin or localhost guard
- response is JSON-safe
- response contains no prompt bodies
- response contains no memory text
- response contains no user messages
- response contains no reference prompt content
- response cannot execute commands
- route reuses `get_prompt_runtime_status()`
- `command_router.py` remains untouched
- public chat APIs do not expose diagnostics

## I. Rollback Plan

If the endpoint is added later and must be rolled back:

1. Disable route registration.
2. Remove admin router include.
3. Keep `get_prompt_runtime_status()` and `scripts/dev/prompt_runtime_status.py`.
4. Return to CLI-only diagnostics.

## J. Future Implementation Checklist

- Confirm admin auth or localhost-only guard.
- Reuse `backend/app/core/prompt_runtime_status.py`.
- Add route tests.
- Add security tests.
- Update route ownership docs.
- Avoid prompt body snapshots in tests.
- Confirm no reference prompt dependency.
- Confirm no command execution.
