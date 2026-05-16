# RAG Phase 5 Project Context Adapter

## Purpose

RAG Phase 5 adds a feature-flagged internal adapter that can pass safe project retrieval context into the runtime prompt builder path. It keeps legacy behavior unchanged by default.

## Feature Flags

Project context injection requires both flags:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
$env:GRANDPA_USE_PROJECT_CONTEXT = "1"
```

Accepted true values:

- `1`
- `true`
- `yes`
- `on`

If either flag is disabled or missing, project context is not injected.

## Adapter Flow

```text
chat_service user message
  -> runtime prompts enabled?
  -> project context enabled?
  -> project_context_adapter
  -> retrieval_context
  -> formatted PROJECT KNOWLEDGE CONTEXT
  -> runtime prompt extra_context
```

The adapter uses the user message as the retrieval query and relies on the RAG-4 packaging layer for caps and redaction.

## Safety Boundaries

- project context is off by default
- runtime prompts are still off by default
- no API route
- no command router integration
- no frontend/mobile changes
- no embeddings or vector DB
- no cloud service
- no command/tool execution
- no full file dumps
- snippets remain capped and redacted
- metadata does not include context text, snippets, file contents, or secrets
- reference folders are ignored and not loaded

## Failure Behavior

If project context building fails:

- chat continues without project context
- runtime prompt behavior remains available
- legacy fallback behavior remains unchanged
- metadata reports no project context included

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_project_file_filters tests.test_project_file_discovery tests.test_project_snapshot tests.test_project_content_reader tests.test_project_chunker tests.test_project_chunk_summary tests.test_project_tokenizer tests.test_project_lexical_index tests.test_project_search tests.test_project_retrieval_context tests.test_project_context_adapter tests.test_chat_service_runtime_prompt tests.test_prompt_runtime_observability -v
```

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_context.py "prompt builder" --summary-only --compact
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --check
```

Manual smoke:

```powershell
Remove-Item Env:\GRANDPA_USE_RUNTIME_PROMPTS -ErrorAction SilentlyContinue
Remove-Item Env:\GRANDPA_USE_PROJECT_CONTEXT -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "hi da"
```

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
Remove-Item Env:\GRANDPA_USE_PROJECT_CONTEXT -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "where is prompt builder"
```

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
$env:GRANDPA_USE_PROJECT_CONTEXT = "1"
.\.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "where is prompt builder"
```

## Limitations

- chat_service is the only possible consumer
- project context is not exposed through API routes
- no persistent index or cache exists yet
- retrieval still uses lexical search only
- context quality depends on the user message query

## Recommended RAG Phase 6

Add prompt-runtime observability for project context flag state and retrieval counts without exposing snippets or context text.
