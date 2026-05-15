# Phase 6 Runtime Prompt Mode Selection

## Scope

Phase 6 keeps `chat_service` as the only runtime prompt consumer and adds conservative mode selection between:

- `default`
- `coding`

Runtime prompts still remain off by default.

## Why Only Default And Coding

`default` and `coding` are the lowest-risk modes for the current normal chat path. Voice, vision, research, and automation need stronger channel-specific context and safety gates before runtime selection should affect live prompts.

## Detection Rules

Mode detection is handled by `backend/app/core/prompt_mode_resolver.py`.

The resolver is:

- deterministic
- local-only
- keyword/pattern based
- conservative
- safe on empty input
- free of LLM calls

It returns `coding` only when the message has clear coding signals such as stack traces, explicit code/debug phrases, coding tool commands, known file extensions, or coding terms combined with error/fix/test context.

## Runtime Flag

When `GRANDPA_USE_RUNTIME_PROMPTS` is unset or off, chat_service returns the exact legacy prompt even for coding-like messages.

Enable runtime prompts:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
```

Disable runtime prompts:

```powershell
Remove-Item Env:\GRANDPA_USE_RUNTIME_PROMPTS
```

## Coding Examples

These route to `coding` when runtime prompts are enabled:

- `fix this code`
- `debug this stack trace`
- `python -m unittest tests.test_chat`
- `FastAPI endpoint error`
- `import error in app.py`
- `intha python bug fix pannu`

## Default Examples

These stay `default`:

- `hi da how are you`
- `tell me a joke`
- `plan my day`
- `what is a class in school`
- `function hall booking help`

## Limitations

- No mode selection is wired into API routes or command routing.
- No voice, vision, research, or automation mode selection yet.
- The resolver may miss vague coding requests by design.
- It may need telemetry or manual feedback before broader use.

## Next Phase Recommendation

Phase 7 should add prompt-runtime observability for tests and diagnostics, such as reporting whether legacy or runtime prompts were selected without exposing full prompt text or secrets.
