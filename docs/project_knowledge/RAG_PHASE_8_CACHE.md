# RAG Phase 8: Lightweight On-Disk Cache

## Purpose

RAG-8 adds a local JSON cache for safe project knowledge artifacts so lexical retrieval can be reused without rebuilding the full discovery, chunking, and indexing pipeline on every run.

The cache remains read-only with respect to project files. It writes only cache artifacts under the ignored local runtime cache directory.

## Cache Architecture

New modules:

- `backend/app/project_knowledge/cache.py`
- `backend/app/project_knowledge/cached_search.py`
- `scripts/dev/project_cache.py`

Cache location:

```text
runtime/cache/project_knowledge/
```

The repository already ignores `runtime/`, so cache files remain local-only.

## Stored Data

The cache stores JSON only:

- cache manifest
- safe file metadata
- redacted chunk text
- lexical index data
- schema version and timestamps

The cache does not use pickle, SQLite, embeddings, vector databases, cloud services, or external APIs.

## Manifest

Each cache includes metadata like:

```json
{
  "schema_version": 1,
  "created_at": "...",
  "project_root": "...",
  "file_count": 0,
  "chunk_count": 0,
  "index_type": "lexical",
  "safe": true
}
```

## Invalidation

The cache is invalidated when:

- the schema version changes
- the index type changes
- the project root changes
- discovered files are missing or added
- file sizes change
- project files have newer modified timestamps than the manifest

This is intentionally lightweight. Future phases can add content hashes if needed.

## CLI

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

CLI output is metadata-only and does not print chunk bodies.

## Safety Boundaries

- No project files are modified.
- No commands or tools are executed.
- No API routes are added.
- No `command_router.py` changes.
- No frontend/mobile changes.
- No embeddings or vector DB.
- No cloud dependencies.
- No reference prompt repository dependency.
- Cache files stay local under ignored `runtime/cache/`.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_project_cache tests.test_cached_project_search -v
```

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_cache.py status
.\.venv\Scripts\python.exe scripts/dev/project_cache.py rebuild
.\.venv\Scripts\python.exe scripts/dev/project_cache.py clear
```

## Recommended Next Phase

RAG-9 should stabilize cache behavior with release-prep validation, or design embeddings support without implementing it yet.
