# Prompt Runtime Release Prep

## Architecture Summary

The prompt-runtime foundation is a modular, file-backed prompt system for GrandpaAssistant. Runtime prompt text lives under `backend/app/prompts`, while lightweight helpers in `backend/app/core` handle loading, composition, mode validation, adapter fallback, observability, status reporting, memory context sanitization, and dormant planner payload preparation.

Runtime prompts remain behind `GRANDPA_USE_RUNTIME_PROMPTS` and are off by default. `chat_service` is the only active runtime prompt consumer.

## Completed Phases

- Phase 0: reference research setup and `.gitignore` protection.
- Phase 1: high-level prompt pattern research.
- Phase 2: original GrandpaAssistant policy design.
- Phase 3: runtime prompt foundation.
- Phase 4: optional runtime prompt adapter.
- Phase 5: first feature-flagged `chat_service` consumer.
- Phase 6: conservative default/coding mode selection.
- Phase 7: safe observability metadata.
- Phase 8: internal status helper.
- Phase 9: local CLI status command.
- Phase 10: rollout report.
- Phase 11: safe memory context sanitizer and optional injection path.
- Phase 12: dormant planning mode.
- Phase 13: planner payload helper.
- Phase 14: planner payload verifier.
- Phase 15: diagnostics endpoint design only.
- Phase 16: stabilization checklist and full validation.

## Changed File Review By Category

### Runtime Modules

- `backend/app/core/prompt_modes.py`
- `backend/app/core/prompt_loader.py`
- `backend/app/core/prompt_builder.py`
- `backend/app/core/runtime_prompt_adapter.py`
- `backend/app/core/prompt_mode_resolver.py`
- `backend/app/core/prompt_memory_context.py`
- `backend/app/core/chat_service.py`
- `backend/app/core/prompts/__init__.py`

### Prompts

- `backend/app/prompts/base/core.txt`
- `backend/app/prompts/safety/automation_safety.txt`
- `backend/app/prompts/tools/tool_rules.txt`
- `backend/app/prompts/modes/default.txt`
- `backend/app/prompts/modes/coding.txt`
- `backend/app/prompts/modes/voice.txt`
- `backend/app/prompts/modes/vision.txt`
- `backend/app/prompts/modes/research.txt`
- `backend/app/prompts/modes/planning.txt`

### Planner Modules

- `backend/app/core/planner_prompt_payload.py`
- `backend/app/core/planner_payload_verifier.py`

### Observability And Status

- `backend/app/core/prompt_runtime_observability.py`
- `backend/app/core/prompt_runtime_status.py`

### CLI And Dev Scripts

- `scripts/dev/prompt_runtime_status.py`

### Tests

- `tests/test_prompt_loader.py`
- `tests/test_prompt_builder.py`
- `tests/test_runtime_prompt_adapter.py`
- `tests/test_prompt_mode_resolver.py`
- `tests/test_prompt_runtime_observability.py`
- `tests/test_prompt_runtime_status.py`
- `tests/test_prompt_runtime_status_cli.py`
- `tests/test_prompt_memory_context.py`
- `tests/test_chat_service_runtime_prompt.py`
- `tests/test_planner_prompt_payload.py`
- `tests/test_planner_payload_verifier.py`

### Docs

- `docs/prompt_research/*`
- `docs/prompt_policies/*`
- `docs/prompt_runtime/*`

## Runtime Safety Boundaries

- Runtime prompts are off by default.
- No prompt bodies are exposed by status helpers or CLI diagnostics.
- No memory content, user messages, secrets, or environment dumps are exposed.
- `reference/system_prompts_leaks` is ignored and not loaded at runtime.
- No API route was created.
- `command_router.py` is not part of this rollout.
- Frontend/mobile are out of scope.
- Planner payloads are internal and non-executable.
- `safe_to_execute` is always false in planner verification.

## Feature Flag Behavior

Enable runtime prompts:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
```

Disable runtime prompts:

```powershell
Remove-Item Env:\GRANDPA_USE_RUNTIME_PROMPTS
```

Accepted true values:

- `1`
- `true`
- `yes`
- `on`

## Current Active Consumers

- `chat_service` only.

## Dormant Features

- `voice`, `vision`, `research`, `automation`, and `planning` prompt modes are available to the builder/status surface but not broadly wired.
- Planner payload and verifier helpers are internal only.
- Admin diagnostics endpoint is design-only.

## Test Coverage Summary

Coverage includes:

- prompt file loading and path safety
- prompt builder composition
- adapter fallback behavior
- mode resolution
- metadata safety
- status helper safety
- CLI output safety
- memory context sanitization
- chat-service legacy/runtime behavior
- planner payload construction
- planner verifier safety checks

## Known Limitations

- Runtime prompt rollout is intentionally narrow.
- Only `default` and `coding` are selected by live `chat_service`.
- No long-term memory source is wired into `chat_service`.
- No LLM planner call exists.
- No admin/API diagnostics route exists.

## Rollback Strategy

1. Clear `GRANDPA_USE_RUNTIME_PROMPTS`.
2. Keep legacy prompt behavior active.
3. If needed, revert the small `chat_service` adapter integration.
4. Keep CLI diagnostics and docs for later review.
5. Do not remove prompt files unless the whole rollout is intentionally reverted.

## Recommended Future Roadmap

1. Review and commit the prompt-runtime foundation as one milestone.
2. Run broader backend validation beyond prompt-runtime tests.
3. Design memory-source integration for `chat_service`.
4. Add a planner LLM-call design with verifier gates, still no execution.
5. Implement an admin-only diagnostics endpoint only if needed.
6. Expand voice/vision/research modes one consumer at a time.
