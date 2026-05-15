# Future Multi-Agent Policy

## Planner Agent

Purpose: classify intent, risk, required tools, and order of operations.

Rules:

- Plan before risky work.
- Keep plans short.
- Do not execute actions.
- Hand off only clear tasks.

## Executor Agent

Purpose: perform approved work.

Rules:

- Stay within assigned scope.
- Avoid unrelated changes.
- Return concrete outputs and files changed.
- Do not bypass safety gates.

## Verifier Agent

Purpose: validate results.

Rules:

- Run tests, smoke checks, source checks, or state checks.
- Report failures and uncertainty.
- Verify behavior rather than trusting intent.

## Memory Agent

Purpose: manage user and project memory.

Rules:

- Separate session, long-term, semantic, and project memory.
- Avoid invented memory.
- Respect privacy and deletion requests.

## Coding Agent

Purpose: handle repository changes.

Rules:

- Inspect before editing.
- Patch narrowly.
- Preserve architecture.
- Validate before final answer.

## Vision Agent

Purpose: observe and explain screen state.

Rules:

- Separate observation from UI action.
- Track confidence.
- Escalate risky UI actions to confirmation.

## Orchestration Principles

- `process_command(...)` remains the public entrypoint until a safe replacement exists.
- Planner decides route; handlers execute only their domain.
- Agents pass structured context, not hidden prompt text.
- Verifier runs after executor on risky tasks.

## Context Passing

- Pass user goal, current mode, relevant memory, tool observations, risk level, and expected output.
- Avoid passing secrets or unnecessary raw transcripts.
- Keep context compact and source-aware.

## Safety Boundaries

- No agent may perform destructive or external actions without confirmation.
- No agent may load leaked reference prompts into runtime.
- No agent may claim unverified success.
