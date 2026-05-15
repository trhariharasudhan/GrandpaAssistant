# Phase 9 Prompt Runtime Status CLI

## Purpose

Phase 9 adds a local developer-only CLI script that prints the safe prompt runtime status JSON from `get_prompt_runtime_status()`.

This is for local diagnostics only. It is not an API route.

## Commands

Pretty JSON:

```powershell
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py
```

Compact JSON:

```powershell
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --compact
```

Safety check:

```powershell
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --check
```

`--check` exits `0` only when `safe_to_expose` is true and `reference_folder_used` is false.

## Safe Output Shape

```json
{
  "active_consumer": "chat_service",
  "available_prompt_files": ["base/core.txt"],
  "env_var": "GRANDPA_USE_RUNTIME_PROMPTS",
  "metadata_fields": ["runtime_enabled"],
  "missing_expected_prompt_files": [],
  "reference_folder_used": false,
  "runtime_enabled": false,
  "safe_to_expose": true,
  "supported_modes": ["default"]
}
```

The exact lists may vary as prompt files and modes evolve.

## Intentionally Not Shown

The CLI does not show:

- full system prompt text
- prompt file contents
- memory content
- extra context content
- user messages
- secrets, tokens, or credentials
- reference prompt text

## Debugging Value

The command helps verify whether runtime prompts are enabled, which prompt files are present, which modes are supported, and whether the status payload is safe for future controlled diagnostics.

## Why Not An API Route

An API route would require route ownership, authentication, response-shape review, and exposure-risk tests. This phase keeps diagnostics local and developer-only.

## Rollout Report

See `docs/prompt_runtime/PROMPT_RUNTIME_ROLLOUT_REPORT.md` for the full Phases 0-9 rollout summary, safety boundaries, validation commands, and recommended next phases.
