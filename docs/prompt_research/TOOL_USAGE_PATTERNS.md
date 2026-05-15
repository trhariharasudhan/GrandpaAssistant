# Tool Usage Patterns

These patterns are adapted for GrandpaAssistant and do not quote reference prompt text.

## When To Use Tools

- Use file/search tools when answering questions about the local codebase.
- Use tests or smoke checks after backend changes.
- Use inventory scripts when route/import ownership is being audited.
- Use web/search tools for current, high-stakes, niche, or source-dependent facts.
- Use screen/vision tools only when the user asks about visible UI or screen context.
- Use shell tools for concrete local validation, not for speculation.

## When Not To Use Tools

- Do not browse or inspect reference prompt files from backend runtime.
- Do not run shell commands for simple conceptual answers.
- Do not use automation tools for actions that only need explanation.
- Do not run destructive commands unless explicitly requested and confirmed.
- Do not use screen capture when cached/read-only context is enough.

## Verification After Tool Use

- For code edits: run focused tests first, then broader tests when risk warrants it.
- For shell commands: report the meaningful result, not just that a command ran.
- For browser research: cite checked sources and separate evidence from inference.
- For file edits: inspect changed files or relevant diff before finalizing.
- For startup/runtime work: run startup smoke and terminal smoke when applicable.

## Fallback Behavior

- If a preferred tool is unavailable, use a safer lower-capability path.
- If validation cannot run, say exactly what was not verified.
- If a source is unavailable, do not invent the missing content.
- If a command fails, preserve state and explain the failure.

## Avoiding Fake Results

- Never claim tests passed without running them.
- Never cite a source that was not checked.
- Never summarize a file as if read when only its name was seen.
- Never say a runtime changed if only docs changed.
- Never imply reference prompt text was copied into GrandpaAssistant.

## Tool Routing Ideas For GrandpaAssistant

- Route read-only status commands to specialized handlers.
- Route shell/file/git mutations through a safety gate.
- Route voice commands through a concise response policy.
- Route screen/vision commands through observe-then-act stages.
- Route research through search, source-read, synthesis, verification, final response.
- Route memory commands through explicit save/read/delete intent categories.
