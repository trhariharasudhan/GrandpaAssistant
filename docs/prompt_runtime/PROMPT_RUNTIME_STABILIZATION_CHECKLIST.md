# Prompt Runtime Stabilization Checklist

## Current Architecture Summary

GrandpaAssistant has a file-backed runtime prompt foundation under `backend/app/prompts` with lightweight core modules for loading, composing, selecting, observing, and validating prompt behavior.

Current runtime consumer:

- `chat_service` only.

Current diagnostics:

- Internal status helper: `backend/app/core/prompt_runtime_status.py`.
- Local CLI: `scripts/dev/prompt_runtime_status.py`.

No API diagnostics route exists.

## Feature Flag Status

Runtime prompts are OFF by default.

Enable:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
```

Disable:

```powershell
Remove-Item Env:\GRANDPA_USE_RUNTIME_PROMPTS
```

Accepted true values:

- `1`
- `true`
- `yes`
- `on`

## Safety Boundaries

- No runtime dependency on `reference/system_prompts_leaks`.
- No prompt bodies exposed through status helpers or CLI.
- No memory content exposed through status helpers or CLI.
- No user messages, secrets, environment dumps, or leaked prompt text exposed.
- `command_router.py` is not part of prompt-runtime diagnostics.
- Frontend/mobile are out of scope.
- Planning payloads are internal and non-executable.
- `safe_to_execute` remains false for planner verification.

## Files And Modules Created Across Phases

Prompt files:

- `backend/app/prompts/base/core.txt`
- `backend/app/prompts/safety/automation_safety.txt`
- `backend/app/prompts/tools/tool_rules.txt`
- `backend/app/prompts/modes/default.txt`
- `backend/app/prompts/modes/coding.txt`
- `backend/app/prompts/modes/voice.txt`
- `backend/app/prompts/modes/vision.txt`
- `backend/app/prompts/modes/research.txt`
- `backend/app/prompts/modes/planning.txt`

Core modules:

- `backend/app/core/prompt_modes.py`
- `backend/app/core/prompt_loader.py`
- `backend/app/core/prompt_builder.py`
- `backend/app/core/runtime_prompt_adapter.py`
- `backend/app/core/prompt_mode_resolver.py`
- `backend/app/core/prompt_runtime_observability.py`
- `backend/app/core/prompt_runtime_status.py`
- `backend/app/core/prompt_memory_context.py`
- `backend/app/core/planner_prompt_payload.py`
- `backend/app/core/planner_payload_verifier.py`

CLI:

- `scripts/dev/prompt_runtime_status.py`

## Tests To Run Before Release

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_prompt_loader tests.test_prompt_builder tests.test_runtime_prompt_adapter tests.test_prompt_mode_resolver tests.test_prompt_runtime_observability tests.test_prompt_runtime_status tests.test_prompt_runtime_status_cli tests.test_prompt_memory_context tests.test_chat_service_runtime_prompt tests.test_planner_prompt_payload tests.test_planner_payload_verifier -v
```

## CLI Checks To Run Before Release

```powershell
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --compact
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --check
```

## Manual Smoke Tests

Legacy:

```powershell
Remove-Item Env:\GRANDPA_USE_RUNTIME_PROMPTS -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "hi da"
```

Runtime:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
.\.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "fix this python code"
```

## Rollback Plan

1. Clear `GRANDPA_USE_RUNTIME_PROMPTS`.
2. Keep legacy prompt behavior active.
3. If needed, remove the `chat_service` adapter call and restore direct legacy prompt construction.
4. Keep docs and tests for future controlled rollout.
5. Continue using CLI-only diagnostics.

## Known Limitations

- Only `chat_service` consumes runtime prompts.
- Runtime prompts are disabled by default.
- Only `default` and `coding` modes are selected by live chat-service behavior.
- Voice, vision, research, automation, and planning modes are not broadly wired.
- No admin/API diagnostics endpoint exists.
- No planner LLM call exists.
- No execution path exists for planner payloads.
- No long-term memory source is wired into `chat_service` memory context yet.

## Go/No-Go Checklist

- [ ] Full prompt-runtime unit suite passes.
- [ ] CLI status command passes.
- [ ] CLI compact output is JSON-safe.
- [ ] CLI check exits 0.
- [ ] Legacy smoke test passes.
- [ ] Runtime smoke test passes.
- [ ] `py_compile` passes for prompt runtime modules.
- [ ] No prompt bodies exposed in status/CLI.
- [ ] No reference prompt files staged.
- [ ] No API route added.
- [ ] `command_router.py` unchanged for this rollout.
- [ ] Frontend/mobile untouched.
- [ ] Rollback path documented.
