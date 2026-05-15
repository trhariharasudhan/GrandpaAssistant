# Agent Architecture Ideas

This document proposes future GrandpaAssistant architecture ideas based on high-level patterns from the reference prompt repository. It does not copy prompt text.

## Planner Agent

Purpose: Decide the safest path before action.

Responsibilities:

- Classify user intent.
- Decide whether a tool is needed.
- Identify risk level.
- Create a short execution plan for multi-step work.
- Defer to command router safety rules for actions.

## Executor Agent

Purpose: Carry out approved steps.

Responsibilities:

- Run safe read-only tools.
- Apply approved file edits.
- Invoke backend services.
- Preserve runtime entrypoints.
- Return concrete results for verification.

## Reviewer/Verifier Agent

Purpose: Check the work before final response.

Responsibilities:

- Run tests and smoke checks.
- Inspect diffs.
- Detect behavior drift.
- Verify route/handler ownership.
- Report residual risk.

## Memory Agent

Purpose: Manage memory safely.

Responsibilities:

- Separate session context from saved memory.
- Summarize user preferences.
- Avoid overwriting current instructions with stale memory.
- Require explicit commands for memory writes/deletes.

## Coding Agent

Purpose: Handle repository work.

Responsibilities:

- Inspect before edit.
- Make small patches.
- Preserve existing style.
- Run targeted and full validation.
- Keep final answers grounded in files changed and tests run.

## Vision Agent

Purpose: Handle screen and visual context.

Responsibilities:

- Explain visible/cached screen context.
- Keep capture separate from action.
- Flag uncertainty.
- Hand off click/type actions to automation safety.

## Automation Agent

Purpose: Handle desktop, Windows, IoT, contact, and notification actions.

Responsibilities:

- Require confirmation for risky actions.
- Keep read-only status separate from mutations.
- Verify action results when possible.
- Respect privacy and external communication boundaries.

## Research Agent

Purpose: Handle web/source-backed research.

Responsibilities:

- Search when current or source-dependent facts matter.
- Prefer primary sources.
- Summarize without long excerpts.
- Identify inference versus evidence.

## Recommended Future Architecture Diagram

```text
User request
  -> process_command(...) public entrypoint
  -> intent classifier / planner
  -> risk classifier
  -> read-only handler registry
  -> action safety gate if mutation/external/system action
  -> specialized agent/service:
       - coding
       - memory
       - voice
       - vision
       - automation
       - research
       - provider/LLM
  -> verifier:
       - tests
       - smoke checks
       - source checks
       - screen/app state checks
  -> final response formatter
```

## Implementation Recommendation

Start with shared policy modules and tests before adding any actual multi-agent runtime. Keep `process_command(...)` public until action-heavy paths have exact behavioral coverage.
