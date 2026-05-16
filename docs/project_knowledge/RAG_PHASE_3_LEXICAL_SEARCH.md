# RAG Phase 3 Lexical Search

## Purpose

RAG Phase 3 adds a local in-memory lexical search index over safe project chunks. It is still read-only and local-first. It does not add embeddings, vector databases, cloud APIs, prompt integration, command routing, or file mutation.

## Architecture

```text
safe discovery
  -> safe content reader
  -> chunker
  -> tokenizer
  -> in-memory lexical index
  -> bounded search results
```

New modules:

- `tokenizer.py`: deterministic token normalization for code, paths, and prose.
- `lexical_index.py`: in-memory document and inverted-index builder.
- `project_search.py`: safe project-level search helper.
- `scripts/dev/project_search.py`: local developer CLI for bounded JSON search results.

## Tokenization

The tokenizer is case-insensitive and handles:

- snake_case identifiers
- camelCase identifiers
- kebab-case phrases
- file paths
- normal prose

Tiny tokens and basic stop words are skipped.

## Scoring Summary

Search scoring is intentionally simple:

- term frequency adds relevance
- more matched query terms add relevance
- path/file-name matches receive a boost
- deterministic sorting breaks ties by relative path and chunk index

This keeps the first search layer explainable and dependency-free.

## Result Safety

Search results include capped snippets only. They do not dump full files or all chunks by default. Snippets are redacted again before output and capped by `MAX_RESULT_SNIPPET_CHARS`.

Result fields include:

- relative path
- chunk id
- chunk index
- score
- matched terms
- capped snippet
- line range
- metadata

## Why No Embeddings Yet

Lexical search gives the assistant a testable retrieval foundation without adding storage, dependency, privacy, or prompt-injection complexity. Embeddings can be considered only after local chunk safety, redaction, search limits, and diagnostics are stable.

## CLI Examples

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_search.py "prompt builder" --limit 5
.\.venv\Scripts\python.exe scripts/dev/project_search.py "chat_service runtime prompt" --limit 5 --compact
```

## Safety Boundaries

- read-only
- no project file edits
- no code execution
- no embeddings or vector DB
- no cloud services
- no API route
- no prompt/runtime integration
- no command router integration
- ignored/reference folders are not indexed
- snippets are capped and redacted

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_project_file_filters tests.test_project_file_discovery tests.test_project_snapshot tests.test_project_content_reader tests.test_project_chunker tests.test_project_chunk_summary tests.test_project_tokenizer tests.test_project_lexical_index tests.test_project_search -v
```

```powershell
.\.venv\Scripts\python.exe scripts/dev/project_search.py "prompt builder" --limit 5
.\.venv\Scripts\python.exe scripts/dev/project_search.py "chat_service runtime prompt" --limit 5 --compact
.\.venv\Scripts\python.exe scripts/dev/project_chunk_summary.py --compact
```

```powershell
.\.venv\Scripts\python.exe -m py_compile backend/app/project_knowledge/__init__.py backend/app/project_knowledge/config.py backend/app/project_knowledge/file_discovery.py backend/app/project_knowledge/file_filters.py backend/app/project_knowledge/file_metadata.py backend/app/project_knowledge/project_snapshot.py backend/app/project_knowledge/content_reader.py backend/app/project_knowledge/chunker.py backend/app/project_knowledge/project_chunks.py backend/app/project_knowledge/tokenizer.py backend/app/project_knowledge/lexical_index.py backend/app/project_knowledge/project_search.py scripts/dev/project_search.py scripts/dev/project_chunk_summary.py
```

## Recommended RAG Phase 4

Add a retrieval packaging layer that converts safe search results into compact context blocks for future prompt use, still behind tests and still not wired into chat_service by default.
