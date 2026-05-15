# Prompt Runtime Rollout Report

## Executive Summary

GrandpaAssistant now has a production-safe prompt runtime foundation that is original to this project, file-backed, testable, observable, and feature-flagged.

What was built:

- Local runtime prompt files under `backend/app/prompts`.
- Safe prompt loading, composition, mode validation, and mode resolution.
- Optional runtime prompt adapter with legacy fallback.
- `chat_service` as the first and only runtime prompt consumer.
- Safe metadata/status helpers that never expose prompt bodies.
- Local developer CLI for prompt runtime diagnostics.

Why it matters:

- Prompt behavior can now evolve without rewriting chat/API routing.
- Runtime prompts are modular and testable.
- Rollout is reversible through one environment flag.
- Legacy prompt behavior remains the default.

Current rollout status:

- Runtime prompts are still OFF by default.
- Only `chat_service` can consume runtime prompts.
- Only `default` and `coding` mode selection are active in `chat_service`.

## Phase-By-Phase Summary

### Phase 0: Reference Setup

Purpose: Prepare safe local research around the reference prompt repository.

Files created/changed summary:

- `.gitignore` verified for `reference/system_prompts_leaks/`.
- `docs/prompt_research/README.md`.
- `docs/prompt_research/REFERENCE_AUDIT.md`.

Safety boundary:

- Reference files are local research only.
- Reference prompts are not runtime dependencies.

Validation result:

- Reference folder ignore rule verified.
- Documentation-only setup confirmed.

### Phase 1: Pattern Research

Purpose: Study high-level assistant architecture patterns without copying leaked prompt text.

Files created/changed summary:

- `docs/prompt_research/PROMPT_PATTERNS_FOR_GRANDPAASSISTANT.md`.
- `docs/prompt_research/HIGH_VALUE_RULES.md`.
- `docs/prompt_research/SAFETY_PATTERNS.md`.
- `docs/prompt_research/TOOL_USAGE_PATTERNS.md`.
- `docs/prompt_research/AGENT_ARCHITECTURE_IDEAS.md`.
- `docs/prompt_research/REFERENCE_AUDIT.md` updated.

Safety boundary:

- Research captured reusable patterns only.
- No runtime code changed.

Validation result:

- Research docs created.
- Python/runtime files unchanged.

### Phase 2: Original Policy Design

Purpose: Design GrandpaAssistant-owned assistant policies.

Files created/changed summary:

- Policy docs under `docs/prompt_policies/`.
- `docs/prompt_policies/PHASE_2_SUMMARY.md`.
- `docs/prompt_research/REFERENCE_AUDIT.md` updated.

Safety boundary:

- Policies are original project design material.
- No prompt loading or runtime behavior added.

Validation result:

- Policy docs created.
- Runtime files unchanged.

### Phase 3: Runtime Prompt Foundation

Purpose: Add a lightweight file-backed runtime prompt foundation.

Files created/changed summary:

- Prompt files under `backend/app/prompts`.
- `backend/app/core/prompt_modes.py`.
- `backend/app/core/prompt_loader.py`.
- `backend/app/core/prompt_builder.py`.
- `tests/test_prompt_loader.py`.
- `tests/test_prompt_builder.py`.
- `docs/prompt_runtime/PHASE_3_RUNTIME_FOUNDATION.md`.

Safety boundary:

- No existing runtime callers migrated.
- No LLM calls in loader or builder.
- Reference folder not used.

Validation result:

- Focused prompt loader/builder tests passed.
- New modules compiled.

### Phase 4: Runtime Adapter

Purpose: Bridge legacy prompt behavior and the new runtime builder through an optional adapter.

Files created/changed summary:

- `backend/app/core/runtime_prompt_adapter.py`.
- `backend/app/core/prompts/__init__.py` optional export.
- `tests/test_runtime_prompt_adapter.py`.
- `docs/prompt_runtime/PHASE_4_RUNTIME_ADAPTER.md`.

Safety boundary:

- Existing prompt behavior remains default.
- Adapter returns legacy fallback unless runtime prompts are enabled.

Validation result:

- Adapter tests passed.
- Prompt modules compiled.

### Phase 5: First Consumer Integration

Purpose: Wire runtime prompts into one safe consumer path.

Files created/changed summary:

- `backend/app/core/chat_service.py`.
- `tests/test_chat_service_runtime_prompt.py`.
- `docs/prompt_runtime/PHASE_5_FIRST_CONSUMER_INTEGRATION.md`.

Safety boundary:

- `chat_service` is the only consumer.
- Legacy prompt remains exact when the feature flag is off.
- No API route or command router changes.

Validation result:

- Prompt and chat-service runtime tests passed.
- Modified modules compiled.

### Phase 6: Safe Mode Selection

Purpose: Select between `default` and `coding` modes for `chat_service` when runtime prompts are enabled.

Files created/changed summary:

- `backend/app/core/prompt_mode_resolver.py`.
- `backend/app/core/chat_service.py`.
- `tests/test_prompt_mode_resolver.py`.
- `tests/test_chat_service_runtime_prompt.py`.
- `docs/prompt_runtime/PHASE_6_MODE_SELECTION.md`.

Safety boundary:

- Deterministic local mode detection only.
- No LLM call for mode selection.
- Legacy default remains exact when the flag is off.

Validation result:

- Mode resolver and chat-service tests passed.
- Changed modules compiled.

### Phase 7: Observability Metadata

Purpose: Add safe prompt runtime metadata without exposing prompt text.

Files created/changed summary:

- `backend/app/core/prompt_runtime_observability.py`.
- `backend/app/core/runtime_prompt_adapter.py`.
- `backend/app/core/chat_service.py`.
- `tests/test_prompt_runtime_observability.py`.
- Updated adapter and chat-service runtime tests.
- `docs/prompt_runtime/PHASE_7_OBSERVABILITY.md`.

Safety boundary:

- Metadata includes source, mode, fallback state, prompt length, and reason only.
- No prompt bodies, memory content, user messages, or secrets.

Validation result:

- Observability tests passed.
- New/modified modules compiled.

### Phase 8: Status Helper

Purpose: Add an internal debug/status helper for prompt runtime readiness.

Files created/changed summary:

- `backend/app/core/prompt_runtime_status.py`.
- `tests/test_prompt_runtime_status.py`.
- `docs/prompt_runtime/PHASE_8_STATUS_HELPER.md`.

Safety boundary:

- Internal helper only.
- No API route.
- Relative prompt file paths only.
- No prompt contents.

Validation result:

- Status tests passed.
- Status module compiled.

### Phase 9: Local CLI Status Command

Purpose: Add a local developer CLI for safe prompt runtime diagnostics.

Files created/changed summary:

- `scripts/dev/prompt_runtime_status.py`.
- `tests/test_prompt_runtime_status_cli.py`.
- `docs/prompt_runtime/PHASE_9_STATUS_CLI.md`.

Safety boundary:

- Local script only.
- No API route.
- JSON output contains safe metadata only.

Validation result:

- CLI tests passed.
- Manual CLI commands passed.
- CLI script compiled.

### Phase 11: Memory Context Injection

Purpose: Add safe optional memory context formatting for runtime prompts.

Files created/changed summary:

- `backend/app/core/prompt_memory_context.py`.
- `backend/app/core/chat_service.py`.
- Prompt runtime adapter/metadata tests updated.
- `tests/test_prompt_memory_context.py`.
- `docs/prompt_runtime/PHASE_11_MEMORY_CONTEXT.md`.

Safety boundary:

- Runtime prompts remain off by default.
- Memory content is not exposed through metadata, status, CLI output, logs, or APIs.
- `chat_service` has no separate long-term memory source wired in this phase, so live provider calls still pass no memory context.

Validation result:

- Memory context tests passed.
- Prompt runtime status check passed.

### Phase 12: Dormant Planning Mode

Purpose: Add a future planner/task-decomposition prompt mode without connecting it to execution.

Files created/changed summary:

- `backend/app/prompts/modes/planning.txt`.
- `backend/app/core/prompt_modes.py`.
- `backend/app/core/prompt_builder.py`.
- `backend/app/core/prompt_mode_resolver.py`.
- `backend/app/core/prompt_runtime_status.py`.
- Prompt loader, builder, resolver, status, and chat-service tests updated.
- `docs/prompt_runtime/PHASE_12_PLANNING_MODE.md`.

Safety boundary:

- Planning mode is dormant.
- `chat_service` still selects only `default` or `coding`.
- No command routing, automation, UI, file, or execution behavior changed.

Validation result:

- Planning mode tests passed.
- Prompt runtime status check passed.

### Phase 13: Planner Payload Helper

Purpose: Add a planner-only payload helper for future task decomposition.

Files created/changed summary:

- `backend/app/core/planner_prompt_payload.py`.
- `tests/test_planner_prompt_payload.py`.
- `docs/prompt_runtime/PHASE_13_PLANNER_PAYLOAD.md`.

Safety boundary:

- No LLM/provider calls.
- No command/tool execution.
- No API route.
- No command router or automation wiring.
- Payload is internal and status/CLI helpers do not expose its prompt body.

Validation result:

- Planner payload tests passed.
- Prompt runtime status check passed.

### Phase 14: Planner Payload Verifier

Purpose: Add a verifier/self-review helper for planner payload safety.

Files created/changed summary:

- `backend/app/core/planner_payload_verifier.py`.
- `backend/app/core/planner_prompt_payload.py`.
- `tests/test_planner_payload_verifier.py`.
- Planner payload tests updated.
- `docs/prompt_runtime/PHASE_14_PLANNER_VERIFIER.md`.

Safety boundary:

- No LLM/provider calls.
- No command/tool execution.
- `safe_to_execute` is always false.
- Verification results do not include prompt bodies, user request text, or memory content.

Validation result:

- Planner verifier tests passed.
- Prompt runtime status check passed.

### Phase 15: Diagnostics Endpoint Design

Purpose: Design a future admin-only prompt-runtime diagnostics endpoint without implementing it.

Files created/changed summary:

- `docs/prompt_runtime/PHASE_15_DIAGNOSTICS_ENDPOINT_DESIGN.md`.
- `docs/prompt_runtime/PROMPT_RUNTIME_ROUTE_OWNERSHIP_PLAN.md`.

Safety boundary:

- Documentation only.
- No API route implemented.
- No backend runtime code changed.
- Future endpoint must be admin/local-only, read-only, and based on `get_prompt_runtime_status()`.

Validation result:

- Docs created.
- No route or runtime code required for this phase.

### Phase 16: Stabilization Checklist And Full Validation

Purpose: Freeze feature work, document the release checklist, and run the full prompt-runtime validation suite.

Files created/changed summary:

- `docs/prompt_runtime/PROMPT_RUNTIME_STABILIZATION_CHECKLIST.md`.

Safety boundary:

- No new runtime features added.
- No API route added.
- No command router, frontend, or mobile changes.

Validation result:

- Full prompt-runtime unit suite run.
- Prompt runtime CLI checks run.
- Legacy and runtime smoke commands run where safe.
- Prompt runtime modules compiled.

## Current Architecture

Runtime prompt files live under:

- `backend/app/prompts/base`
- `backend/app/prompts/modes`
- `backend/app/prompts/safety`
- `backend/app/prompts/tools`

Core modules:

- `prompt_loader`: safely loads prompt files relative to `backend/app/prompts`.
- `prompt_builder`: composes base, mode, safety, tool, memory, and extra-context sections.
- `prompt_memory_context`: sanitizes optional memory context for runtime prompts.
- `prompt_modes`: defines supported modes and validation helpers.
- `runtime_prompt_adapter`: chooses legacy fallback or runtime prompt based on the feature flag.
- `prompt_mode_resolver`: conservatively chooses `default` or `coding` for `chat_service`.
- `planning` mode exists for future use but is not selected by `chat_service`.
- `prompt_runtime_observability`: creates safe metadata without prompt text.
- `prompt_runtime_status`: reports internal status and readiness metadata.
- `planner_prompt_payload`: builds internal planning payloads without execution.
- `planner_payload_verifier`: validates planner payload safety flags without exposing prompt/request text.

Consumer:

- `chat_service` is the only runtime prompt consumer.

Developer CLI:

- `scripts/dev/prompt_runtime_status.py`.

## Feature Flag Usage

Enable:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
```

Disable:

```powershell
Remove-Item Env:\GRANDPA_USE_RUNTIME_PROMPTS
```

Accepted true values:

- `1`
- `true`
- `yes`
- `on`

## Safety Boundaries

- `reference/system_prompts_leaks` is ignored and never loaded at runtime.
- No prompt bodies are exposed through status helpers.
- No API route was added for prompt status.
- `command_router.py` was not touched.
- Frontend/mobile were untouched.
- Legacy behavior remains default.
- Runtime prompts are active only when `GRANDPA_USE_RUNTIME_PROMPTS` is enabled.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_prompt_loader tests.test_prompt_builder tests.test_runtime_prompt_adapter tests.test_prompt_mode_resolver tests.test_prompt_runtime_observability tests.test_prompt_runtime_status tests.test_prompt_runtime_status_cli tests.test_chat_service_runtime_prompt -v
```

```powershell
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --compact
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --check
```

## Manual Smoke Test Commands

Legacy mode:

```powershell
Remove-Item Env:\GRANDPA_USE_RUNTIME_PROMPTS -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "hi da"
```

Runtime mode:

```powershell
$env:GRANDPA_USE_RUNTIME_PROMPTS = "1"
.\.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "fix this python code"
```

## Known Limitations

- Only `chat_service` consumes runtime prompts.
- Only `default` and `coding` mode selection are active.
- Voice, vision, research, automation, and planning modes exist but are not broadly wired.
- No admin/API diagnostic endpoint exists yet.
- `memory_context` injection is supported by the builder but not integrated into a runtime memory path yet.
- `chat_service` can accept sanitized memory context internally, but no existing long-term memory source is connected to that path yet.
- No planner agent exists yet.

## Recommended Next Phases

- Phase 11: memory context injection into runtime prompts.
- Phase 12: planner/task decomposition prompt mode.
- Phase 13: verification/self-review layer.
- Phase 14: expand modes carefully.
- Phase 15: admin-only debug endpoint if needed.

## Release Checklist

- Gitignore verified for the reference prompt folder.
- Tests passed.
- CLI status passed.
- Prompt bodies not exposed.
- Legacy default verified.
- Environment flag documented.
- Rollback path documented: clear `GRANDPA_USE_RUNTIME_PROMPTS` to return to legacy prompt behavior.
