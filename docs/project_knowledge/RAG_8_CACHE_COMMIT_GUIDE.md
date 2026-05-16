# RAG-8 Cache Commit Guide

## Suggested Files To Stage

Runtime modules:

- `backend/app/project_knowledge/cache.py`
- `backend/app/project_knowledge/cached_search.py`
- `backend/app/project_knowledge/config.py`

Developer CLI:

- `scripts/dev/project_cache.py`

Tests:

- `tests/test_project_cache.py`
- `tests/test_cached_project_search.py`

Docs:

- `docs/project_knowledge/RAG_PHASE_8_CACHE.md`
- `docs/project_knowledge/RAG_PHASE_9_CACHE_STABILIZATION.md`
- `docs/project_knowledge/RAG_8_CACHE_COMMIT_GUIDE.md`
- `docs/project_knowledge/PROJECT_KNOWLEDGE_RUNTIME_V1.md`
- `docs/ARCHITECTURE_MILESTONE_REPORT.md`

## Files Not To Stage

- `runtime/cache/`
- `reference/system_prompts_leaks/`
- `.env`
- secret files
- virtual environments
- `__pycache__/`
- `.pytest_cache/`
- logs
- runtime databases
- build artifacts
- frontend/mobile files
- `backend/app/core/command_router.py`

## Recommended Commit Message

```text
Add local project knowledge cache for safe lexical retrieval
```

## Optional Tag

```text
project-knowledge-cache-v1
```

## Pre-Push Checklist

- Full project knowledge test suite passed.
- Cache CLI status/rebuild/status/clear passed.
- Project context status CLI check passed.
- Project snapshot and search CLIs passed.
- `py_compile` passed for project knowledge modules and CLIs.
- `runtime/cache/` is ignored and not staged.
- `reference/system_prompts_leaks/` is untracked and not staged.
- No API routes were added.
- No `command_router.py` changes were staged.
- No frontend/mobile changes were staged.
- No secrets, `.env`, venv, cache, log, or runtime DB files were staged.

## Suggested Stage Commands

```powershell
git add backend/app/project_knowledge/cache.py
git add backend/app/project_knowledge/cached_search.py
git add backend/app/project_knowledge/config.py
git add scripts/dev/project_cache.py
git add tests/test_project_cache.py
git add tests/test_cached_project_search.py
git add docs/project_knowledge/RAG_PHASE_8_CACHE.md
git add docs/project_knowledge/RAG_PHASE_9_CACHE_STABILIZATION.md
git add docs/project_knowledge/RAG_8_CACHE_COMMIT_GUIDE.md
git add docs/project_knowledge/PROJECT_KNOWLEDGE_RUNTIME_V1.md
git add docs/ARCHITECTURE_MILESTONE_REPORT.md
```
