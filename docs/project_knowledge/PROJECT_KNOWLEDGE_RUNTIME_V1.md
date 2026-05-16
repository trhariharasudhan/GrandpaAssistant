# Project Knowledge Runtime v1

## Architecture Overview

Project Knowledge Runtime v1 is a read-only local metadata foundation for GrandpaAssistant.

It contains:

- `config.py`: supported extensions, ignored directories, and scan limits.
- `file_filters.py`: safe path and file eligibility checks.
- `file_metadata.py`: metadata-only file summaries.
- `file_discovery.py`: deterministic recursive discovery.
- `project_snapshot.py`: JSON-safe project snapshot assembly.
- `content_reader.py`: safe text reading with binary rejection, read limits, and obvious secret redaction.
- `chunker.py`: deterministic text/file chunking for future retrieval.
- `project_chunks.py`: metadata-only chunk summary assembly.
- `tokenizer.py`: deterministic tokenization for code identifiers, paths, and prose.
- `lexical_index.py`: local in-memory lexical index and bounded search.
- `project_search.py`: safe project-level search helper.
- `retrieval_context.py`: compact retrieval context packaging and summary helpers.
- `project_context_adapter.py`: feature-flagged bridge from retrieval context to runtime prompt `extra_context`.
- `project_context_status.py`: safe metadata-only status for project context readiness and flags.
- `scripts/dev/project_snapshot.py`: local CLI snapshot command.
- `scripts/dev/project_chunk_summary.py`: local CLI chunk summary command.
- `scripts/dev/project_search.py`: local CLI lexical search command.
- `scripts/dev/project_context.py`: local CLI retrieval context command.
- `scripts/dev/project_context_status.py`: local CLI project context status command.

## Why Read-Only First

The first project knowledge phase built trust with metadata only. Phase 2 added an internal content reader and chunker, while diagnostics still expose summaries only. Phase 3 added a local in-memory lexical index and capped search snippets. Phase 4 packages safe search snippets into compact retrieval context blocks. Phase 5 adds an opt-in adapter that can pass that context to runtime prompts only when both runtime prompts and project context are enabled. Phase 6 adds safe metadata-only status for project context readiness. The system does not build embeddings, write persistent indexes, run tools, modify files, or expose project context by default.

## Supported Extensions

- `.py`
- `.md`
- `.json`
- `.yaml`
- `.yml`
- `.toml`
- `.ini`

## Ignored Directories

- `.git`
- `.codex`
- `.python311`
- `.venv`
- `venv`
- `node_modules`
- `dist`
- `build`
- `coverage`
- `__pycache__`
- `.pytest_cache`
- `.mypy_cache`
- `runtime`
- `logs`
- `reference`
- `system_prompts_leaks`

## Safety Boundaries

- Read-only scanning and chunk preparation.
- Snapshot diagnostics are metadata only.
- Chunk summary diagnostics never print chunk text.
- Content reads are capped and binary files are rejected.
- Obvious secret-like values are redacted before chunking.
- Search snippets are capped and redacted.
- Retrieval context blocks are capped and redacted.
- Retrieval summaries exclude snippet text.
- Project context status exposes flags and limits only, never context bodies or snippets.
- No automatic editing.
- No command execution.
- No prompt/runtime integration by default.
- Prompt/runtime project context is available only when both `GRANDPA_USE_RUNTIME_PROMPTS` and `GRANDPA_USE_PROJECT_CONTEXT` are enabled.
- No API route.
- No embeddings or vector DB.
- No external services.
- No reference prompt repository dependency.
- No file contents printed in diagnostics.

## Content And Chunk Limits

- maximum read bytes: `200000`
- maximum chunk characters: `2000`
- chunk overlap characters: `200`
- maximum chunks per file: `50`
- binary detection bytes: `4096`
- minimum token length: `2`
- maximum query characters: `500`
- maximum search results: `10`
- maximum result snippet characters: `500`
- maximum context results: `5`
- maximum context total characters: `6000`
- maximum context block characters: `1500`

## Chunk Summary CLI

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_chunk_summary.py
.\.venv\Scripts\python.exe scripts/dev/project_chunk_summary.py --compact
```

## Lexical Search CLI

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_search.py "prompt builder" --limit 5
.\.venv\Scripts\python.exe scripts/dev/project_search.py "chat_service runtime prompt" --limit 5 --compact
```

## Retrieval Context CLI

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_context.py "prompt builder"
.\.venv\Scripts\python.exe scripts/dev/project_context.py "runtime adapter" --limit 3
.\.venv\Scripts\python.exe scripts/dev/project_context.py "chat_service" --summary-only --compact
```

## Project Context Runtime Flags

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
$env:GRANDPA_USE_PROJECT_CONTEXT = "1"
```

Both flags are required. With either flag off, legacy/default behavior is preserved and project context is not injected.

## Project Context Status CLI

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_context_status.py
.\.venv\Scripts\python.exe scripts/dev/project_context_status.py --compact
.\.venv\Scripts\python.exe scripts/dev/project_context_status.py --check
```

## RAG-7 Stabilization

Release-readiness docs:

- `docs/project_knowledge/PROJECT_KNOWLEDGE_RUNTIME_V1_ROLLOUT_REPORT.md`
- `docs/project_knowledge/PROJECT_KNOWLEDGE_STABILIZATION_CHECKLIST.md`
- `docs/project_knowledge/PROJECT_KNOWLEDGE_COMMIT_GUIDE.md`

## Future Phases

Future phases can add a release report, admin-only diagnostics, embeddings, and broader integration. Each should remain local-first and separately tested.
