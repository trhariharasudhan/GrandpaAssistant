# Phase 12 Planning Mode

## Purpose

Phase 12 adds a dormant `planning` runtime prompt mode for future planner and task-decomposition work.

The mode is available to the prompt loader, builder, mode validator, and status helper, but it is not wired into execution, automation, command routing, or live chat-service mode selection.

## Why Planning Mode Is Dormant

Planning is useful for complex task decomposition, but plans can lead toward risky execution if they are connected too early. This phase makes the prompt mode testable without allowing it to trigger actions.

## Planner Prompt Capabilities

The planning prompt can guide an assistant to:

- break complex requests into steps
- identify goals and assumptions
- identify risks and tools needed
- separate observation, planning, execution, and verification
- mark risky steps as requiring confirmation
- produce concise structured plans

## Planner Prompt Must Not

Planning mode must not:

- execute plans
- run commands
- automate UI
- change files
- trigger tools
- claim actions were completed

## Untouched Runtime Areas

`command_router.py`, automation behavior, frontend, and mobile were not touched.

`chat_service` still only selects `default` or `coding` mode during live runtime prompt use.

## Future Phase 13

Phase 13 can safely wire planning by adding a separate planner-only helper that returns a plan object or plan text without execution. It should include tests proving no command, automation, file, UI, or provider action is triggered by planning.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_prompt_loader tests.test_prompt_builder tests.test_prompt_mode_resolver tests.test_prompt_runtime_status tests.test_chat_service_runtime_prompt -v
```

```powershell
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --check
```
