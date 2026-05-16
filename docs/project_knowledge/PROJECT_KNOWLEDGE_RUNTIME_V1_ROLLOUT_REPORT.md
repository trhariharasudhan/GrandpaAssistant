# Project Knowledge Runtime v1 Rollout Report

## Executive Summary

Project Knowledge Runtime v1 adds a local-first, read-only project knowledge foundation for GrandpaAssistant. It can discover project files, read safe text with redaction, prepare bounded chunks, search those chunks lexically, package retrieval context, and optionally pass that context to `chat_service` runtime prompts behind feature flags.

This matters because it gives GrandpaAssistant a tested retrieval foundation without adding cloud services, vector databases, embeddings, API routes, file edits, or command execution.

Current rollout status:

- RAG-1 through RAG-6 are implemented.
- Runtime prompt integration remains opt-in.
- Project context remains off by default.
- Both `GRANDPA_USE_RUNTIME_PROMPTS` and `GRANDPA_USE_PROJECT_CONTEXT` must be enabled for prompt context injection.

## Phase Summary

| Phase | Purpose | Key Files | Safety Boundaries | Validation |
| --- | --- | --- | --- | --- |
| RAG-1 | Metadata-only project snapshot | `config.py`, `file_filters.py`, `file_metadata.py`, `file_discovery.py`, `project_snapshot.py`, `scripts/dev/project_snapshot.py` | No file contents, no writes, ignored folders skipped | Project filter/discovery/snapshot tests |
| RAG-2 | Safe content reader and chunker | `content_reader.py`, `chunker.py`, `project_chunks.py`, `scripts/dev/project_chunk_summary.py` | Read caps, binary rejection, redaction, no chunk text in summary CLI | Content/chunker/summary tests |
| RAG-3 | Local lexical index and search | `tokenizer.py`, `lexical_index.py`, `project_search.py`, `scripts/dev/project_search.py` | In-memory only, capped/redacted snippets, no embeddings | Tokenizer/index/search tests |
| RAG-4 | Retrieval context packaging | `retrieval_context.py`, `scripts/dev/project_context.py` | Bounded context blocks, summary excludes text, no prompt injection | Retrieval context tests |
| RAG-5 | Feature-flagged context adapter | `project_context_adapter.py`, `chat_service.py`, runtime metadata updates | Requires both flags, metadata excludes context text | Adapter/chat/prompt metadata tests |
| RAG-6 | Safe status and observability | `project_context_status.py`, `scripts/dev/project_context_status.py`, prompt runtime status updates | Metadata only, no snippets, no bodies, no user messages | Status and CLI tests |

## Current Architecture

`backend/app/project_knowledge/` owns the project knowledge runtime:

- Discovery/filtering: determines safe local files by extension, ignored directories, file size, symlink status, and scan depth.
- Content reader: reads text safely, rejects binary files, caps bytes, and redacts obvious secret-like values.
- Chunker: converts safe text into deterministic chunks with character and line ranges.
- Lexical index: builds an in-memory inverted index over safe chunks.
- Project search: returns ranked, capped, redacted search results.
- Retrieval context: packages search results into bounded prompt-ready blocks and safe summaries.
- Project context adapter: bridges retrieval context to `chat_service` only when both feature flags are enabled.
- Project context status: reports safe readiness and flag metadata.

Developer CLIs:

- `scripts/dev/project_snapshot.py`
- `scripts/dev/project_chunk_summary.py`
- `scripts/dev/project_search.py`
- `scripts/dev/project_context.py`
- `scripts/dev/project_context_status.py`

## Feature Flags

Runtime prompts:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
```

Project context:

```powershell
$env:GRANDPA_USE_PROJECT_CONTEXT = "1"
```

Project context activates only when both flags are true. Both flags are off by default.

## Safety Boundaries

- No API route added.
- No `command_router.py` changes.
- No frontend/mobile changes.
- No embeddings, vector DB, cloud service, or external API dependency.
- No automatic edits or command execution.
- Snippets and context are capped and redacted.
- Status and status CLIs expose metadata only.
- Prompt/runtime metadata does not expose context bodies or snippets.
- `reference/system_prompts_leaks/` is ignored and not loaded.

## Validation Commands

RAG validation:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_project_file_filters tests.test_project_file_discovery tests.test_project_snapshot tests.test_project_content_reader tests.test_project_chunker tests.test_project_chunk_summary tests.test_project_tokenizer tests.test_project_lexical_index tests.test_project_search tests.test_project_retrieval_context tests.test_project_context_adapter tests.test_project_context_status tests.test_project_context_status_cli -v
```

Prompt/runtime validation:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_chat_service_runtime_prompt tests.test_prompt_runtime_status tests.test_prompt_runtime_observability -v
```

CLI checks:

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_snapshot.py --compact
.\.venv\Scripts\python.exe scripts/dev/project_chunk_summary.py --compact
.\.venv\Scripts\python.exe scripts/dev/project_search.py "prompt builder" --limit 5 --compact
.\.venv\Scripts\python.exe scripts/dev/project_context.py "prompt builder" --summary-only --compact
.\.venv\Scripts\python.exe scripts/dev/project_context_status.py --check
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --check
```

## Manual Smoke Tests

Legacy:

```powershell
Remove-Item Env:\GRANDPA_USE_RUNTIME_PROMPTS -ErrorAction SilentlyContinue
Remove-Item Env:\GRANDPA_USE_PROJECT_CONTEXT -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "hi da"
```

Runtime only:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
Remove-Item Env:\GRANDPA_USE_PROJECT_CONTEXT -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "where is prompt builder"
```

Runtime plus project context:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
$env:GRANDPA_USE_PROJECT_CONTEXT = "1"
.\.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "where is prompt builder"
```

## Known Limitations

- Lexical search only; no embeddings yet.
- No vector DB or persistent index cache yet.
- No API/admin endpoint.
- Only `chat_service` can consume project context, and only behind flags.
- No planner/tool execution.
- Snippets are capped, so this is not full-file reasoning.
- No persistent cache for faster repeated indexing yet.

## Release Checklist

- Tests passed.
- CLI checks passed.
- Feature flags remain off by default.
- No unsafe body exposure.
- No new APIs.
- Documentation updated.
- Rollback path documented.

## Rollback

To disable behavior without code changes:

```powershell
Remove-Item Env:\GRANDPA_USE_PROJECT_CONTEXT -ErrorAction SilentlyContinue
Remove-Item Env:\GRANDPA_USE_RUNTIME_PROMPTS -ErrorAction SilentlyContinue
```

To rollback the milestone code, revert the project knowledge runtime commit.

## Recommended Next Phases

- RAG-8: commit/release prep.
- RAG-9: optional lightweight on-disk index cache.
- RAG-10: embeddings design only.
- RAG-11: local embeddings prototype.
- RAG-12: admin-only diagnostics endpoint design/implementation if needed.
