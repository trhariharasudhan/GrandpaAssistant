# RAG Phase 4 Retrieval Context

## Purpose

RAG Phase 4 adds a packaging layer that turns safe lexical search results into compact retrieval context blocks for future prompt use. It does not inject those blocks into runtime prompts yet.

## Architecture

```text
query
  -> project_search
  -> capped/redacted snippets
  -> retrieval_context blocks
  -> optional prompt text formatter
  -> safe summary metadata
```

New pieces:

- `retrieval_context.py`: builds context blocks, formats prompt-ready text, and summarizes metadata.
- `scripts/dev/project_context.py`: local CLI for previewing context packaging or summary-only metadata.

## Why This Layer Exists

Search results are useful, but prompts need consistent context formatting. This layer gives GrandpaAssistant a future-safe boundary where retrieval output can be:

- size-limited
- redacted
- deterministic
- source-labeled
- summarized without snippets

## Formatting Strategy

Formatted prompt text starts with:

```text
PROJECT KNOWLEDGE CONTEXT
```

Each block includes:

- file path
- line range
- capped snippet

Blocks are separated by a fixed separator and total output is capped by configuration.

## Safety Boundaries

- read-only
- no project file edits
- no command/tool execution
- no embeddings or vector DB
- no cloud service
- no API route
- no command router integration
- no runtime prompt integration
- no full file dumps
- snippets are capped and redacted
- ignored/reference folders are not loaded

## CLI Examples

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_context.py "prompt builder"
.\.venv\Scripts\python.exe scripts/dev/project_context.py "runtime adapter" --limit 3
.\.venv\Scripts\python.exe scripts/dev/project_context.py "chat_service" --summary-only --compact
```

## Why No Prompt Injection Yet

Prompt injection needs separate controls:

- opt-in runtime flag behavior
- token budget checks
- source labeling in final prompts
- tests proving legacy behavior is unchanged
- observability that does not expose snippets or secrets

This phase creates the package format only.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_project_file_filters tests.test_project_file_discovery tests.test_project_snapshot tests.test_project_content_reader tests.test_project_chunker tests.test_project_chunk_summary tests.test_project_tokenizer tests.test_project_lexical_index tests.test_project_search tests.test_project_retrieval_context -v
```

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_context.py "prompt builder"
.\.venv\Scripts\python.exe scripts/dev/project_context.py "runtime adapter" --limit 3
.\.venv\Scripts\python.exe scripts/dev/project_context.py "chat_service" --summary-only --compact
```

```powershell
.\.venv\Scripts\python.exe -m py_compile backend/app/project_knowledge/__init__.py backend/app/project_knowledge/config.py backend/app/project_knowledge/file_discovery.py backend/app/project_knowledge/file_filters.py backend/app/project_knowledge/file_metadata.py backend/app/project_knowledge/project_snapshot.py backend/app/project_knowledge/content_reader.py backend/app/project_knowledge/chunker.py backend/app/project_knowledge/project_chunks.py backend/app/project_knowledge/tokenizer.py backend/app/project_knowledge/lexical_index.py backend/app/project_knowledge/project_search.py backend/app/project_knowledge/retrieval_context.py scripts/dev/project_context.py
```

## Recommended RAG Phase 5

Add an opt-in internal adapter that can pass retrieval context into prompt-runtime builders under a feature flag, with tests proving legacy chat behavior remains unchanged.
