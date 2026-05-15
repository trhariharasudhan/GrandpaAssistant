# Phase 14 Planner Payload Verifier

## Purpose

Phase 14 adds a verifier/self-review helper for internal planner payloads.

The verifier checks whether a planner payload is structurally safe enough for a future LLM planning call, while still preventing execution.

## Verification Fields

`verify_planner_payload(...)` returns:

- `valid`
- `safe_to_use_for_llm`
- `safe_to_execute`
- `errors`
- `warnings`
- `risk_level`
- `requires_confirmation`
- `checked_fields`

The result does not include `system_prompt`, `user_request`, memory content, or prompt bodies.

## Safety Rules

A payload can be `safe_to_use_for_llm` only when:

- `mode` is `planning`
- `system_prompt` exists
- `execution_allowed` is false
- `tools_allowed` is false
- `risk_level` is valid
- required fields exist

High-risk payloads may be valid for future LLM planning only if `requires_confirmation` is true.

## Why `safe_to_execute` Is Always False

Planning is not execution. This phase deliberately prevents planner payloads from being treated as executable actions. Any future executor must be separate, confirmed, and tested.

## Future Protection

The verifier gives future planner integration a safe gate before a model call or downstream planning workflow. It catches malformed payloads, missing safety flags, and accidental execution/tool permissions.

## Remaining Limitations

- No LLM/provider call is made.
- No API route exists.
- No automation is connected.
- The verifier does not evaluate generated plan quality yet.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_planner_payload_verifier -v
```

```powershell
.\.venv\Scripts\python.exe scripts/dev/prompt_runtime_status.py --check
```
