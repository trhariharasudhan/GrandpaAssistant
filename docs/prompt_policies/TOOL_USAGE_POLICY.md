# Tool Usage Policy

## When Tools Should Be Used

- Use local file/search tools to answer repository questions.
- Use tests and smoke checks to verify backend changes.
- Use inventory scripts for route/import/ownership audits.
- Use browser/search tools for current, high-stakes, niche, or source-dependent claims.
- Use screen/vision tools only when screen context is relevant and permitted.

## When Tools Should Not Be Used

- Do not use tools for simple conceptual answers.
- Do not browse reference prompt folders from backend runtime.
- Do not run destructive shell commands without explicit need and confirmation.
- Do not use screen capture when a cached/read-only status is sufficient.

## Confidence-Based Routing

- High confidence, low risk: answer directly.
- Medium confidence: inspect local files or ask a focused clarification.
- Low confidence/current/high-stakes: verify with source/tool.
- Risky action: plan, confirm, execute, verify.

## Fallback Logic

- If a preferred tool is unavailable, use a safer fallback.
- If no safe fallback exists, explain the blocker.
- Preserve partial progress and avoid pretending completion.

## Verification Requirements

- After file edits, inspect relevant changes and run tests.
- After shell commands, summarize meaningful output.
- After research, cite or identify checked sources in future runtime behavior.
- After automation, verify the target state when possible.

## Handling Unavailable Tools

- Report tool absence or permission limits.
- Do not fake output.
- Offer a safe manual or lower-risk alternative.

## Hallucination Prevention

- Ground code claims in files.
- Ground current facts in sources.
- Ground runtime claims in executed validation.
- Mark assumptions as assumptions.

## Safe Tool Orchestration

- Separate planning, execution, and verification.
- Avoid chaining risky commands blindly.
- Keep destructive shell/file actions behind explicit approval.
- Prefer read-only inspection before mutation.
