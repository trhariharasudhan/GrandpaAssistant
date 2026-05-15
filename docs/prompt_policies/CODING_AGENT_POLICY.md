# Coding Agent Policy

## Inspect Before Editing

- Read relevant files before making changes.
- Use fast search for code discovery.
- Understand existing patterns, imports, tests, and entrypoints before modifying behavior.

## Minimal Targeted Changes

- Keep edits scoped to the user's request.
- Avoid unrelated refactors.
- Prefer small patches over broad rewrites.
- Preserve public APIs and runtime commands unless the user explicitly asks for a breaking change.

## Architecture Stability

- Respect existing module boundaries.
- Do not move action-heavy command logic without exact tests.
- Keep compatibility shims until deprecation criteria are met.
- Preserve backend runtime paths.

## Verification

- Add or update tests when behavior changes.
- Run focused tests first, then broader tests when risk warrants it.
- Do not say tests passed unless they were run.
- If validation cannot run, state that clearly.

## Test-First Mindset

- For routing, prompt behavior, safety behavior, and action dispatch, write tests before or alongside changes.
- Use mocks for hardware, network, shell, and UI automation.
- Avoid tests that mutate real system state.

## Avoid Unnecessary Rewrites

- Reuse existing helper APIs.
- Add abstractions only when they remove real duplication or clarify ownership.
- Avoid style churn and formatting-only noise.

## Risky Refactors

- Explain why a risky refactor is needed.
- Split risky refactors into phases.
- Keep fallback/compatibility wrappers when callers may still depend on old names.

## Repo-Aware Behavior

- Respect dirty worktrees.
- Do not revert user changes.
- Keep docs, tests, scripts, backend runtime, plugins, and compatibility layers unless explicitly asked.

## File Modification Discipline

- Use narrow patches.
- Avoid destructive filesystem commands.
- Never edit generated, secret, or local runtime data unless the task explicitly targets it.
