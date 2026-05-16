# Project Knowledge Commit Guide

## Suggested Commit Grouping

Recommended single milestone commit:

- project knowledge runtime modules
- developer CLIs
- project knowledge tests
- project knowledge documentation
- prompt runtime status/test updates needed for safe project context observability

## Recommended Commit Message

```text
Add local project knowledge runtime with safe lexical retrieval
```

## Files Safe To Stage

- `backend/app/project_knowledge/`
- `scripts/dev/project_snapshot.py`
- `scripts/dev/project_chunk_summary.py`
- `scripts/dev/project_search.py`
- `scripts/dev/project_context.py`
- `scripts/dev/project_context_status.py`
- `tests/test_project_*.py`
- `tests/test_chat_service_runtime_prompt.py`
- `tests/test_prompt_runtime_status.py`
- `tests/test_prompt_runtime_observability.py`
- `backend/app/core/chat_service.py`
- `backend/app/core/runtime_prompt_adapter.py`
- `backend/app/core/prompt_runtime_observability.py`
- `backend/app/core/prompt_runtime_status.py`
- `docs/project_knowledge/`

## Files Not To Stage

- `reference/system_prompts_leaks/`
- local cache/runtime/log files
- `.venv/` or `.python311/`
- unrelated frontend/mobile files
- unrelated generated artifacts

## Pre-Push Checklist

- [ ] RAG unittest suite passed.
- [ ] Prompt/runtime related tests passed.
- [ ] Project knowledge CLIs passed.
- [ ] Terminal chat smoke passed in legacy and flagged modes.
- [ ] py_compile passed.
- [ ] `git status --short` reviewed.
- [ ] No reference folder files staged.

## Optional Tag

```text
project-knowledge-runtime-v1
```
