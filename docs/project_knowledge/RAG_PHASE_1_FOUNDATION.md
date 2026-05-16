# RAG Phase 1 Foundation

## Purpose

RAG Phase 1 adds the first safe local project knowledge foundation for GrandpaAssistant. It produces a metadata-only project snapshot that can later support local search and retrieval.

## Snapshot Flow

```text
project root
  -> file filters
  -> deterministic discovery
  -> safe metadata
  -> project snapshot JSON
```

## Snapshot Contents

The snapshot includes:

- project root
- total file count
- indexed extension counts
- largest files by size
- recently modified files
- discovered file metadata

It does not include file contents.

## Why No Embeddings Or Vector DB Yet

Embeddings and vector databases add dependency, privacy, storage, and prompt-injection risks. This phase establishes the local, read-only metadata layer first.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_project_file_filters tests.test_project_file_discovery tests.test_project_snapshot -v
```

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_snapshot.py
```

```powershell
.\.venv\Scripts\python.exe -m py_compile backend/app/project_knowledge/config.py backend/app/project_knowledge/file_discovery.py backend/app/project_knowledge/file_filters.py backend/app/project_knowledge/file_metadata.py backend/app/project_knowledge/project_snapshot.py scripts/dev/project_snapshot.py
```

## Recommended RAG Phase 2

Add a local content chunking layer that reads file contents only inside strict size/type limits, redacts obvious secrets, and never exposes chunks through diagnostics by default.
