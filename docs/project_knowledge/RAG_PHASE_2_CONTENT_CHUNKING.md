# RAG Phase 2 Content Chunking

## Purpose

RAG Phase 2 adds a safe, read-only content reader and chunker for local project files. It prepares code and documentation chunks for future retrieval work without adding embeddings, vector databases, APIs, prompt injection, or automation.

## Content Reading Safety Model

The reader only accepts files that already pass the project knowledge filters:

- supported extensions only
- ignored directories skipped
- symlinks rejected
- file size limits enforced
- binary files rejected
- malformed paths handled without raising

Files are read up to a strict byte limit. Larger safe files are truncated before decoding. Decoding prefers UTF-8 and falls back to UTF-8 replacement so malformed text cannot crash the reader.

## Redaction Rules

Before text is returned to the internal chunker, obvious secret-like values are redacted:

- password
- token
- api_key
- secret
- credential
- otp
- pin
- bearer values
- private key lines

The goal is not perfect secret detection. It is a first protective layer before future retrieval and prompt use.

## Chunking Strategy

Chunks are deterministic and include:

- chunk id
- chunk index
- text
- character range
- approximate line range
- relative path and extension metadata

Chunk size, overlap, and maximum chunks per file are capped in `config.py`.

## Diagnostics Boundary

`scripts/dev/project_chunk_summary.py` prints only counts and safe metadata:

- files considered
- files chunked
- total chunks
- redacted file count
- truncated file count
- errors

It does not print chunk text.

## Still Not Added

- no embeddings
- no vector DB
- no cloud service
- no API route
- no prompt/runtime integration
- no command router integration
- no file edits

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_project_file_filters tests.test_project_file_discovery tests.test_project_snapshot tests.test_project_content_reader tests.test_project_chunker tests.test_project_chunk_summary -v
```

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_snapshot.py --compact
.\.venv\Scripts\python.exe scripts/dev/project_chunk_summary.py --compact
```

```powershell
.\.venv\Scripts\python.exe -m py_compile backend/app/project_knowledge/__init__.py backend/app/project_knowledge/config.py backend/app/project_knowledge/file_discovery.py backend/app/project_knowledge/file_filters.py backend/app/project_knowledge/file_metadata.py backend/app/project_knowledge/project_snapshot.py backend/app/project_knowledge/content_reader.py backend/app/project_knowledge/chunker.py backend/app/project_knowledge/project_chunks.py scripts/dev/project_snapshot.py scripts/dev/project_chunk_summary.py
```
