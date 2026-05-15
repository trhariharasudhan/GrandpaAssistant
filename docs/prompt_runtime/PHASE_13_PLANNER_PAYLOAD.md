# Phase 13 Planner Payload Helper

## Purpose

Phase 13 adds an internal helper that prepares a planner prompt payload for future task decomposition.

It does not call an LLM, execute commands, run tools, touch command routing, expose an API route, or automate anything.

## Payload Fields

`build_planner_prompt_payload(...)` returns a JSON-safe dictionary with:

- `mode`
- `user_request`
- `system_prompt`
- `memory_context_included`
- `execution_allowed`
- `tools_allowed`
- `requires_confirmation`
- `risk_level`
- `risks`
- `metadata`

`execution_allowed` and `tools_allowed` are always false.

## Safety Boundaries

- Internal helper only.
- No provider calls.
- No command execution.
- No automation.
- No API route.
- No `command_router.py` dependency.
- No reference prompt dependency.

The payload includes a system prompt because it is a future LLM-call preparation object, but status helpers and CLI output must not expose that prompt.

## Risk Classification

High risk examples include destructive file actions, system power actions, registry changes, payment/transfer requests, and credential/secret handling.

Medium risk examples include software install/uninstall, system settings changes, browser/UI automation, communication actions, and network scanning.

Low risk examples include documentation plans, coding refactor plans, architecture plans, and learning roadmaps.

## Future Phase 14

Phase 14 can add a verifier/self-review layer for planner payloads before any future model call is considered. Execution should remain separate from planning.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_planner_prompt_payload -v
```

```powershell
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --check
```
