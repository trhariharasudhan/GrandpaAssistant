# RAG Phase 9: Cache Stabilization And Release Prep

## Purpose

RAG-9 stabilizes the RAG-8 lightweight cache layer for release. It does not add new runtime features, API routes, embeddings, vector databases, command execution, prompt integration changes, or command router behavior.

## RAG-8 Cache Architecture Summary

The cache layer stores safe project knowledge artifacts as local JSON so lexical retrieval can reuse prepared data instead of rebuilding discovery, chunking, and indexing every run.

Core files:

- `backend/app/project_knowledge/cache.py`
- `backend/app/project_knowledge/cached_search.py`
- `scripts/dev/project_cache.py`
- `tests/test_project_cache.py`
- `tests/test_cached_project_search.py`

The cached artifacts are produced from the existing read-only pipeline:

```text
project files
  -> discovery/filtering
  -> safe content reader
  -> redacted chunks
  -> lexical index
  -> local JSON cache
```

## Cache Location

The cache is stored under:

```text
runtime/cache/project_knowledge/
```

The repository already ignores `runtime/`, so cache artifacts remain local-only and should not be staged.

## Schema Version Behavior

The cache uses `CACHE_SCHEMA_VERSION = 1`.

The manifest records:

- schema version
- created timestamp
- project root
- file count
- chunk count
- index type
- safe flag
- file metadata used for invalidation

If the schema version does not match the current code, the cache is treated as invalid and rebuilt.

## Invalidation Rules

The cache is invalidated when:

- cache files are missing
- manifest JSON is malformed
- schema version changes
- index type changes
- project root changes
- discovered file count changes
- discovered file sizes change
- project files have newer modified timestamps than the manifest

This invalidation is intentionally lightweight. Future phases may add content hashes if stronger cache correctness is needed.

## CLI Usage

Status:

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_cache.py status
```

Rebuild:

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_cache.py rebuild
```

Clear:

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_cache.py clear
```

Compact JSON:

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_cache.py status --compact
```

CLI output is metadata-only. It does not print chunk bodies, snippets, full file contents, prompt bodies, secrets, or user messages.

## Safety Boundaries

- Read-only with respect to project files.
- Cache writes are limited to ignored local runtime storage.
- No project files are modified.
- No commands or tools are executed.
- No API routes are added.
- No `command_router.py` changes.
- No frontend/mobile changes.
- No embeddings, vector DB, cloud services, or external APIs.
- No reference prompt repository dependency.
- No file contents or context bodies in status output.
- No prompt/runtime integration changes in RAG-9.

## Known Limitations

- Cache invalidation uses metadata, not content hashes.
- Cache format is JSON only; no SQLite or optimized binary format.
- Cached search is available as a helper, but the existing runtime prompt path is not changed in this phase.
- Cache rebuild can still be expensive on large projects.
- No persistent embedding or semantic index exists yet.

## Validation Commands

Full project knowledge validation:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_project_file_filters tests.test_project_file_discovery tests.test_project_snapshot tests.test_project_content_reader tests.test_project_chunker tests.test_project_chunk_summary tests.test_project_tokenizer tests.test_project_lexical_index tests.test_project_search tests.test_project_retrieval_context tests.test_project_context_adapter tests.test_project_context_status tests.test_project_context_status_cli tests.test_project_cache tests.test_cached_project_search -v
```

CLI validation:

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_cache.py status
.\.venv\Scripts\python.exe scripts/dev/project_cache.py rebuild
.\.venv\Scripts\python.exe scripts/dev/project_cache.py status
.\.venv\Scripts\python.exe scripts/dev/project_cache.py clear
.\.venv\Scripts\python.exe scripts/dev/project_context_status.py --check
.\.venv\Scripts\python.exe scripts/dev/project_snapshot.py --compact
.\.venv\Scripts\python.exe scripts/dev/project_search.py "prompt builder" --limit 5 --compact
```

Compile validation:

```powershell
$files = Get-ChildItem backend\app\project_knowledge\*.py | ForEach-Object { $_.FullName }
.\.venv\Scripts\python.exe -m py_compile @files scripts\dev\project_cache.py scripts\dev\project_snapshot.py scripts\dev\project_chunk_summary.py scripts\dev\project_search.py scripts\dev\project_context.py scripts\dev\project_context_status.py
```

## Rollback Plan

Runtime behavior rollback:

- No feature flag changes are required because RAG-9 does not alter active runtime behavior.
- Clear local cache if needed:

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_cache.py clear
```

Code rollback:

- Revert the RAG-8/RAG-9 cache commit.
- Keep `runtime/cache/` ignored.
- Keep `reference/system_prompts_leaks/` untracked and ignored.

## Release Readiness

RAG-9 is ready for commit when:

- full project knowledge tests pass
- cache CLI status/rebuild/status/clear pass
- project context status check passes
- py_compile passes
- `runtime/cache/` is not staged
- no reference files are tracked or staged
- no API routes, command router files, frontend/mobile files, secrets, caches, logs, or runtime DB files are staged
