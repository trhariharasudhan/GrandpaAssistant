# Phase 4 Runtime Prompt Adapter

## Purpose

Phase 4 adds an optional adapter between the existing prompt flow and the file-backed runtime prompt foundation from Phase 3.

The adapter keeps legacy prompt behavior as the default. Runtime prompts are used only when explicitly enabled by argument or environment variable.

## Adapter

Module:

- `backend/app/core/runtime_prompt_adapter.py`

Main function:

- `get_runtime_system_prompt(...)`

The function accepts:

- `mode`
- `memory_context`
- `extra_context`
- `use_runtime_prompts`
- `fallback_prompt`

## Environment Flag

Runtime prompts can be enabled for testing with:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
```

Accepted true values:

- `1`
- `true`
- `yes`
- `on`

Disable safely by clearing the variable:

```powershell
Remove-Item Env:\GRANDPA_USE_RUNTIME_PROMPTS
```

## Fallback Behavior

- If runtime prompts are disabled, the adapter returns `fallback_prompt`.
- If no fallback is provided, it returns a safe minimal GrandpaAssistant prompt.
- If runtime prompt building fails, it returns the same fallback path.
- Missing prompt files do not crash the adapter.

## Integration Point Found

The safest central integration point is the existing `core.prompts` package export surface. Phase 4 exports the optional adapter from that package without changing existing prompt builders, chat APIs, command routing, or provider behavior.

## Safety Notes

- The adapter does not read from `reference/system_prompts_leaks/`.
- The adapter does not call any model provider.
- Existing APIs and runtime paths keep their legacy prompt behavior by default.

## Next Steps

1. Add behavior tests around one existing prompt consumer.
2. Enable runtime prompts behind `GRANDPA_USE_RUNTIME_PROMPTS` only in that consumer.
3. Compare prompt behavior with legacy fallback.
4. Expand integration one channel at a time.
