# RAG Phase 6 Context Observability

## Purpose

RAG Phase 6 adds safe project context observability for feature flag state, readiness, search type, limits, and exposure guarantees. It does not expose context bodies, snippets, file contents, user messages, secrets, or prompt text.

## Status Helper

Module:

- `backend/app/project_knowledge/project_context_status.py`

Main function:

- `get_project_context_status(project_root=None)`

The helper returns JSON-safe metadata:

- project context flag state
- environment variable names
- runtime prompt requirement
- local lexical search support
- active consumer
- exposure flags
- context limits
- last retrieval placeholder

## Exposed Fields

Safe fields include:

- `project_context_enabled`
- `env_var`
- `requires_runtime_prompts`
- `runtime_prompt_env_var`
- `available`
- `safe_to_expose`
- `supported_search`
- `embeddings_enabled`
- `vector_db_enabled`
- `active_consumer`
- `context_body_exposed`
- `snippet_body_exposed`
- `reference_folder_used`
- `limits`
- `last_retrieval`

## Forbidden Fields

The status helper and CLI must not expose:

- context text
- snippets
- file contents
- user messages
- secrets
- prompt bodies
- memory content
- reference prompt contents

## CLI

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_context_status.py
.\.venv\Scripts\python.exe scripts/dev/project_context_status.py --compact
.\.venv\Scripts\python.exe scripts/dev/project_context_status.py --check
```

`--check` exits `0` only when the status is safe to expose, reference usage is false, and body exposure flags are false.

## Feature Flag Behavior

Project context remains off by default. Runtime prompt integration still requires both:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
$env:GRANDPA_USE_PROJECT_CONTEXT = "1"
```

The status helper may report that the project context flag is enabled, but it does not build retrieval context or expose query/content.

## No API Route Yet

This phase intentionally adds only local helpers and a dev CLI. A future admin/debug endpoint would need separate access controls and tests.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_project_file_filters tests.test_project_file_discovery tests.test_project_snapshot tests.test_project_content_reader tests.test_project_chunker tests.test_project_chunk_summary tests.test_project_tokenizer tests.test_project_lexical_index tests.test_project_search tests.test_project_retrieval_context tests.test_project_context_adapter tests.test_project_context_status tests.test_project_context_status_cli tests.test_prompt_runtime_status -v
```

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_context_status.py
.\.venv\Scripts\python.exe scripts/dev/project_context_status.py --compact
.\.venv\Scripts\python.exe scripts/dev/project_context_status.py --check
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --check
```

```powershell
.\.venv\Scripts\python.exe -m py_compile backend/app/project_knowledge/__init__.py backend/app/project_knowledge/config.py backend/app/project_knowledge/file_discovery.py backend/app/project_knowledge/file_filters.py backend/app/project_knowledge/file_metadata.py backend/app/project_knowledge/project_snapshot.py backend/app/project_knowledge/content_reader.py backend/app/project_knowledge/chunker.py backend/app/project_knowledge/project_chunks.py backend/app/project_knowledge/tokenizer.py backend/app/project_knowledge/lexical_index.py backend/app/project_knowledge/project_search.py backend/app/project_knowledge/retrieval_context.py backend/app/project_knowledge/project_context_adapter.py backend/app/project_knowledge/project_context_status.py scripts/dev/project_context_status.py backend/app/core/prompt_runtime_status.py
```

## Recommended RAG Phase 7

Add a project knowledge release report and stabilization checklist before broader integration work.
