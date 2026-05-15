# Phase 7 Prompt Runtime Observability

## Purpose

Phase 7 adds safe metadata for the runtime prompt system so tests and future diagnostics can tell whether a prompt came from the legacy path or the file-backed runtime path.

The metadata is intentionally small and does not expose prompt bodies.

## Metadata Fields

`PromptRuntimeMetadata` contains:

- `runtime_enabled`
- `selected_mode`
- `source`
- `fallback_used`
- `prompt_length`
- `reason`

`source` is normalized to either `legacy` or `runtime`.

## What Metadata Must Never Contain

Metadata must not include:

- full system prompt text
- memory content
- extra context content
- user message text
- secrets, tokens, credentials, or private data
- reference prompt content

Only prompt length is reported.

## Debugging Value

This helps answer safe operational questions:

- Was `GRANDPA_USE_RUNTIME_PROMPTS` active?
- Which mode was selected?
- Did runtime prompt building fall back to legacy?
- Was the selected prompt empty or unavailable?

## Future Diagnostics

The metadata can later support admin or debug-only diagnostics without exposing sensitive prompt text. It should be surfaced only in controlled internal/debug contexts unless a public API contract is explicitly designed.

## Limitations

- `chat_service` remains the only runtime prompt consumer.
- Metadata is not exposed through FastAPI routes.
- Prompt length is useful for debugging but cannot prove prompt quality.
- The system still supports only `default` and `coding` mode selection in `chat_service`.
