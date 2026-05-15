# Phase 8 Prompt Runtime Status Helper

## Purpose

Phase 8 adds an internal debug/status helper for the runtime prompt system. It reports safe operational metadata without exposing prompt bodies, memory content, user messages, secrets, or reference prompt content.

## Why No API Route Yet

The helper is intentionally internal. A future API/admin endpoint should be designed separately with authentication, response-shape review, and tests. This phase only creates the safe data source.

## Safe Fields Included

`get_prompt_runtime_status()` returns:

- `runtime_enabled`
- `env_var`
- `supported_modes`
- `active_consumer`
- `available_prompt_files`
- `missing_expected_prompt_files`
- `metadata_fields`
- `reference_folder_used`
- `safe_to_expose`

Prompt file paths are relative to `backend/app/prompts`.

## Unsafe Fields Excluded

The status helper must not include:

- full system prompt text
- prompt file contents
- memory content
- extra context content
- user messages
- secrets, tokens, or credentials
- reference prompt files or text

## Future Admin/Debug Endpoint

A later phase can expose this helper through a debug-only endpoint after adding auth, route ownership docs, and response-shape tests.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_prompt_runtime_status -v
```
