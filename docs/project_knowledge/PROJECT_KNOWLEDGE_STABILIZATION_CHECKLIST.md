# Project Knowledge Stabilization Checklist

## Module Checklist

- [ ] `config.py` defines safe limits and ignored directories.
- [ ] `file_filters.py` rejects unsafe paths.
- [ ] `file_discovery.py` discovers metadata deterministically.
- [ ] `content_reader.py` caps reads and redacts obvious secrets.
- [ ] `chunker.py` caps chunks and preserves ranges.
- [ ] `lexical_index.py` stays in-memory.
- [ ] `project_search.py` returns capped/redacted snippets.
- [ ] `retrieval_context.py` packages bounded context.
- [ ] `project_context_adapter.py` requires both flags.
- [ ] `project_context_status.py` exposes metadata only.

## Safety Checklist

- [ ] No API route added.
- [ ] No `command_router.py` changes.
- [ ] No frontend/mobile changes.
- [ ] No embeddings/vector DB/cloud dependency.
- [ ] No automatic file edits.
- [ ] No command/tool execution path.
- [ ] No context bodies or snippets in status output.
- [ ] No user messages or prompt bodies in status output.
- [ ] `reference/system_prompts_leaks/` remains ignored and not loaded.

## Validation Checklist

- [ ] Run the RAG unittest suite.
- [ ] Run prompt/runtime integration tests.
- [ ] Run py_compile for project knowledge modules and dev CLIs.

## CLI Checklist

- [ ] `project_snapshot.py --compact`
- [ ] `project_chunk_summary.py --compact`
- [ ] `project_search.py "prompt builder" --limit 5 --compact`
- [ ] `project_context.py "prompt builder" --summary-only --compact`
- [ ] `project_context_status.py --check`
- [ ] `prompt_runtime_status.py --check`

## Smoke Checklist

- [ ] Legacy flags off smoke passes.
- [ ] Runtime-only smoke passes.
- [ ] Runtime plus project context smoke passes.

## Rollback Checklist

- [ ] Disable `GRANDPA_USE_PROJECT_CONTEXT`.
- [ ] Disable `GRANDPA_USE_RUNTIME_PROMPTS`.
- [ ] Re-run legacy terminal smoke.
- [ ] Revert milestone commit only if code rollback is required.

## Go/No-Go Checklist

- [ ] All tests pass.
- [ ] All CLI checks pass.
- [ ] Flags are off by default.
- [ ] No unsafe exposure found.
- [ ] No accidental runtime/API/UI surface added.
- [ ] Documentation is complete.
