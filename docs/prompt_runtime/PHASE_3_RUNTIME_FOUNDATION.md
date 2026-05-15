# Phase 3 Runtime Prompt Foundation

## Overview

Phase 3 adds a lightweight runtime prompt foundation for GrandpaAssistant without changing existing chat, command routing, provider, frontend, or mobile behavior.

The new foundation is file-backed, modular, and limited to GrandpaAssistant-owned prompt text. It does not read from `reference/system_prompts_leaks/`.

## Runtime Prompt Flow

```text
mode request
  -> core.prompt_modes.validate_mode
  -> core.prompt_loader.load_prompt
  -> core.prompt_builder.build_system_prompt
  -> composed system prompt
```

Prompt composition order:

1. `backend/app/prompts/base/core.txt`
2. `backend/app/prompts/modes/<mode>.txt`
3. `backend/app/prompts/safety/automation_safety.txt`
4. `backend/app/prompts/tools/tool_rules.txt`
5. optional memory context
6. optional extra context

Exact duplicate sections are removed while preserving order.

## Supported Modes

- `default`
- `coding`
- `voice`
- `vision`
- `research`
- `automation`

`automation` currently reuses the automation safety prompt as its mode-specific section. Duplicate removal prevents the safety section from appearing twice.

## New Modules

- `backend/app/core/prompt_modes.py`: supported mode constants and validation helpers.
- `backend/app/core/prompt_loader.py`: safe file loading from `backend/app/prompts`.
- `backend/app/core/prompt_builder.py`: runtime system prompt composition.

## Future Plug-In Points

- Voice can pass short-term conversation state through `extra_context`.
- Vision can pass structured screen/OCR observations through `extra_context`.
- Memory can pass retrieved memories through `memory_context`.
- A future planner can choose a mode before prompt composition.
- Provider-specific adapters can consume the composed prompt without knowing file paths.

## Safety Notes

- Prompt files are original GrandpaAssistant runtime text.
- Missing prompt files return an empty string and log a warning.
- Path traversal outside `backend/app/prompts` is rejected.
- No LLM calls happen in the loader or builder.
- No reference prompt files are loaded.

## Migration Strategy

1. Keep the existing `core.prompts` and chatbot prompt builder behavior unchanged.
2. Add tests around this runtime prompt foundation.
3. In a later phase, add optional adapters from existing prompt builders to this foundation.
4. Migrate one channel at a time with behavior tests.
5. Keep old prompt builders as compatibility wrappers until migration is verified.
