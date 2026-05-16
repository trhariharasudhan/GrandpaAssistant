# GrandpaAssistant Architecture Milestone Report

## Executive Summary

GrandpaAssistant now has two major backend foundations in place:

- **Prompt Runtime Foundation v1**: a file-backed, feature-flagged runtime prompt system with safe adapter, mode selection, metadata, status helpers, and local diagnostics.
- **Project Knowledge Runtime v1**: a local-first, read-only project knowledge pipeline with safe discovery, content reading, chunking, lexical search, retrieval context packaging, feature-flagged prompt context integration, and metadata-only status tooling.

Both foundations are intentionally conservative. Legacy behavior remains the default, runtime prompts are off by default, project context is off by default, and only `chat_service` is wired as a controlled consumer.

Detailed rollout reports:

- `docs/prompt_runtime/PROMPT_RUNTIME_ROLLOUT_REPORT.md`
- `docs/project_knowledge/PROJECT_KNOWLEDGE_RUNTIME_V1_ROLLOUT_REPORT.md`

## Prompt Runtime Foundation v1

Prompt Runtime Foundation v1 gives GrandpaAssistant a modular prompt layer without rewriting the existing backend or route system.

Core runtime pieces:

- `backend/app/prompts/`: original GrandpaAssistant prompt files grouped by base, modes, safety, and tool rules.
- `backend/app/core/prompt_loader.py`: safe prompt file loading and prompt inventory helpers.
- `backend/app/core/prompt_builder.py`: deterministic system prompt composition.
- `backend/app/core/prompt_modes.py`: supported runtime prompt modes.
- `backend/app/core/runtime_prompt_adapter.py`: optional bridge from legacy prompt behavior to file-backed runtime prompts.
- `backend/app/core/prompt_mode_resolver.py`: conservative deterministic mode selection.
- `backend/app/core/prompt_memory_context.py`: safe memory context normalization and secret filtering.
- `backend/app/core/prompt_runtime_observability.py`: metadata helpers that do not expose prompt bodies.
- `backend/app/core/prompt_runtime_status.py`: metadata-only runtime prompt status helper.
- `scripts/dev/prompt_runtime_status.py`: local CLI diagnostics.

Active prompt behavior:

- Runtime prompts are available only when `GRANDPA_USE_RUNTIME_PROMPTS` is enabled.
- `chat_service` is the only runtime prompt consumer.
- `chat_service` currently selects only `default` and `coding` modes.
- Legacy prompt behavior remains the default when the flag is absent or false.

Dormant prompt/runtime pieces:

- `voice`, `vision`, `research`, `automation`, and `planning` prompt modes exist for future phases but are not broadly wired into execution paths.
- Planner payload and verifier helpers exist for future task decomposition, but they do not call LLMs, execute tools, or touch command routing.
- Admin diagnostics endpoint design exists, but no API route has been added.

## Project Knowledge Runtime v1

Project Knowledge Runtime v1 gives GrandpaAssistant a safe local retrieval foundation without cloud services, vector databases, embeddings, API routes, or autonomous editing.

Core project knowledge pieces:

- `backend/app/project_knowledge/config.py`: supported extensions, ignored directories, scan limits, read limits, search limits, and context limits.
- `file_filters.py`, `file_metadata.py`, `file_discovery.py`, `project_snapshot.py`: metadata-only project discovery and snapshots.
- `content_reader.py`: safe text reading with binary rejection, size caps, decoding fallback, and obvious secret redaction.
- `chunker.py`, `project_chunks.py`: deterministic chunks and metadata-only chunk summaries.
- `tokenizer.py`, `lexical_index.py`, `project_search.py`: local in-memory lexical search.
- `retrieval_context.py`: capped retrieval context blocks and safe summaries.
- `project_context_adapter.py`: feature-flagged bridge from lexical retrieval to runtime prompt `extra_context`.
- `project_context_status.py`: metadata-only project context readiness and flag status.
- `cache.py`, `cached_search.py`: local JSON cache helpers for safe lexical retrieval reuse.

Developer CLIs:

- `scripts/dev/project_snapshot.py`
- `scripts/dev/project_chunk_summary.py`
- `scripts/dev/project_search.py`
- `scripts/dev/project_context.py`
- `scripts/dev/project_context_status.py`
- `scripts/dev/project_cache.py`

Active project knowledge behavior:

- Local metadata and CLI tooling are available.
- Lexical search and retrieval context packaging are implemented.
- A local JSON cache exists under ignored `runtime/cache/project_knowledge/` to speed future lexical retrieval preparation.
- Project context can reach `chat_service` only when both runtime flags are enabled.

Dormant project knowledge behavior:

- No embeddings.
- No vector database.
- No API/admin endpoint.
- No command router integration.
- No autonomous file edits or tool execution.
- No vector DB or embeddings.

## Feature Flags

Prompt runtime flag:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
```

Project context flag:

```powershell
$env:GRANDPA_USE_PROJECT_CONTEXT = "1"
```

Accepted true values are:

- `1`
- `true`
- `yes`
- `on`

Rollout behavior:

- With both flags off, GrandpaAssistant uses legacy behavior.
- With only `GRANDPA_USE_RUNTIME_PROMPTS` on, `chat_service` can use file-backed runtime prompts.
- With both flags on, `chat_service` can include capped and redacted project retrieval context.
- With `GRANDPA_USE_PROJECT_CONTEXT` on but runtime prompts off, project context is not injected.

## What Is Active Now

Active and safe today:

- Backend-only prompt runtime modules.
- Runtime prompt adapter behind `GRANDPA_USE_RUNTIME_PROMPTS`.
- `chat_service` as the only prompt runtime consumer.
- Conservative `default`/`coding` mode selection in `chat_service`.
- Prompt runtime status CLI.
- Local project file discovery, metadata snapshots, content reading, chunking, lexical search, retrieval context packaging, and status CLIs.
- Feature-flagged project context adapter for `chat_service`.
- Metadata-only observability for prompt runtime and project context.

## What Is Dormant

Intentionally dormant:

- Planner/task decomposition execution.
- Voice, vision, research, automation, and planning runtime mode routing beyond explicit internal helpers/tests.
- Project context in API routes.
- Project context in `command_router.py`.
- Embeddings and vector database storage.
- Persistent project index cache.
- Admin/API diagnostics endpoints.
- Any autonomous edits, commands, UI automation, or tool execution based on retrieved context.

## Safety Boundaries

Global safety boundaries:

- No frontend/mobile integration.
- No `command_router.py` integration for prompt runtime or project knowledge.
- No public API route added for prompt runtime or project knowledge diagnostics.
- No automatic code editing.
- No command/tool execution.
- No cloud/vector DB dependency.
- No reference prompt repository runtime dependency.
- `reference/system_prompts_leaks/` remains ignored and local-only.

Prompt runtime safety:

- Runtime prompts are off by default.
- Legacy behavior remains the default fallback.
- Metadata/status helpers do not expose prompt bodies.
- Prompt status CLI does not expose prompt text, memory content, user messages, or secrets.
- Planner payload/verifier helpers are internal only and never execute.

Project knowledge safety:

- File discovery obeys ignored directories and supported extensions.
- Content reads are capped and binary files are rejected.
- Obvious secret-like values are redacted before chunking/search/context packaging.
- Search snippets and retrieval context blocks are capped.
- Status helpers and status CLIs expose metadata only, not snippets or context bodies.
- Project context injection requires both `GRANDPA_USE_RUNTIME_PROMPTS` and `GRANDPA_USE_PROJECT_CONTEXT`.
- Cache artifacts stay local under ignored `runtime/cache/` and are not intended for Git.

## Tests And Validation Summary

Prompt runtime validation coverage includes:

- Prompt loading and missing-file behavior.
- Prompt building and mode inclusion.
- Runtime adapter fallback behavior.
- Conservative prompt mode resolution.
- Safe metadata generation.
- Prompt runtime status helper and CLI.
- Memory context sanitization.
- Chat service runtime prompt behavior.
- Planner payload and verifier safety.

Project knowledge validation coverage includes:

- File filters, discovery, metadata snapshots.
- Safe content reading and redaction.
- Chunking limits, overlap, deterministic chunk IDs, and line ranges.
- Metadata-only chunk summary.
- Tokenization for code identifiers, paths, and prose.
- Lexical index/search ranking and capped snippets.
- Retrieval context packaging and formatting.
- Project context adapter feature-flag behavior.
- Project context status helper and CLI.

Representative validation commands:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_prompt_loader tests.test_prompt_builder tests.test_runtime_prompt_adapter tests.test_prompt_mode_resolver tests.test_prompt_runtime_observability tests.test_prompt_runtime_status tests.test_prompt_runtime_status_cli tests.test_prompt_memory_context tests.test_chat_service_runtime_prompt tests.test_planner_prompt_payload tests.test_planner_payload_verifier -v
```

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_project_file_filters tests.test_project_file_discovery tests.test_project_snapshot tests.test_project_content_reader tests.test_project_chunker tests.test_project_chunk_summary tests.test_project_tokenizer tests.test_project_lexical_index tests.test_project_search tests.test_project_retrieval_context tests.test_project_context_adapter tests.test_project_context_status tests.test_project_context_status_cli -v
```

```powershell
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --check
.\.venv\Scripts\python.exe scripts/dev/project_context_status.py --check
```

Manual smoke examples:

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

## Current Runtime Architecture

Current high-level flow when all flags are off:

```text
user message
  -> chat_service
  -> legacy prompt behavior
  -> existing provider/runtime path
```

Current high-level flow when runtime prompts are enabled:

```text
user message
  -> chat_service
  -> prompt_mode_resolver
  -> runtime_prompt_adapter
  -> prompt_builder + prompt files
  -> existing provider/runtime path
```

Current high-level flow when both runtime prompts and project context are enabled:

```text
user message
  -> chat_service
  -> project_context_adapter
  -> project_search / retrieval_context
  -> capped redacted context
  -> runtime_prompt_adapter
  -> prompt_builder + prompt files + extra_context
  -> existing provider/runtime path
```

## Rollback

Fast runtime rollback:

```powershell
Remove-Item Env:\GRANDPA_USE_PROJECT_CONTEXT -ErrorAction SilentlyContinue
Remove-Item Env:\GRANDPA_USE_RUNTIME_PROMPTS -ErrorAction SilentlyContinue
```

Code rollback:

- Revert the Prompt Runtime Foundation v1 milestone commit if prompt runtime modules must be removed.
- Revert the Project Knowledge Runtime v1 milestone commit if project knowledge modules must be removed.
- Keep `reference/system_prompts_leaks/` untracked and ignored.

## Next Roadmap

Recommended next phases:

1. Stabilize existing backend milestones with periodic full validation.
2. Add optional lightweight on-disk lexical index cache with explicit invalidation and safe metadata.
3. Stabilize the local cache with release validation before broader adoption.
4. Design embeddings support before implementation; keep local-first and avoid cloud dependencies by default.
5. Prototype local embeddings only after the lexical path remains stable.
6. Add admin-only diagnostics endpoint only after route ownership and auth/localhost guards are finalized.
7. Wire broader prompt modes gradually, one consumer at a time, with feature flags and tests.
8. Keep `command_router.py` untouched until a dedicated migration phase is planned and covered by tests.
9. Add planner/task-decomposition integration only as a non-executing advisory layer first.

## Release State

Prompt Runtime Foundation v1 and Project Knowledge Runtime v1 are release-ready backend foundations with conservative rollout controls. The active system remains safe-by-default, and the dormant pieces are positioned for future incremental phases without changing existing desktop assistant behavior.
