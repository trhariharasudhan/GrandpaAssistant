# Prompt Runtime Commit Guide

## Suggested Commit Grouping

Recommended as one milestone commit:

- prompt runtime core modules
- prompt files
- `chat_service` feature-flagged integration
- status CLI
- planner payload/verifier helpers
- tests
- research, policy, rollout, and release docs

If splitting into multiple commits is preferred:

1. Research and policy docs.
2. Runtime prompt foundation and adapter.
3. `chat_service` integration and tests.
4. Observability/status/CLI.
5. Planner payload/verifier.
6. Rollout/release documentation.

## Recommended Commit Message

```text
Add modular prompt runtime foundation with safe rollout architecture
```

## Files Safe To Stage

- `.gitignore`
- `backend/app/core/prompt_*.py`
- `backend/app/core/runtime_prompt_adapter.py`
- `backend/app/core/planner_*payload*.py`
- `backend/app/core/chat_service.py`
- `backend/app/core/prompts/__init__.py`
- `backend/app/prompts/**`
- `scripts/dev/prompt_runtime_status.py`
- `tests/test_prompt_*.py`
- `tests/test_runtime_prompt_adapter.py`
- `tests/test_chat_service_runtime_prompt.py`
- `tests/test_planner_*.py`
- `docs/prompt_research/**`
- `docs/prompt_policies/**`
- `docs/prompt_runtime/**`

## Files Not To Stage

- `reference/system_prompts_leaks/**`
- frontend/mobile files
- local caches and `__pycache__`
- generated logs
- secrets, tokens, credentials, or runtime data
- unrelated backend changes

## Pre-Push Checklist

- Run prompt-runtime unittest suite.
- Run CLI status checks.
- Run legacy and runtime smoke tests.
- Confirm no prompt bodies are exposed in diagnostics.
- Confirm runtime prompts are off by default.
- Confirm no API diagnostics route was added.
- Confirm no command router changes are included.

## Release Tagging Suggestion

After merge, consider a lightweight milestone tag such as:

```text
prompt-runtime-foundation-v1
```

Use the repository's existing release/tag naming convention if one exists.
