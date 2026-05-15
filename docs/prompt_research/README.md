# Prompt Research Notes

`reference/system_prompts_leaks/` is a local-only research and reference folder. It must remain ignored by git and must not become a runtime dependency for GrandpaAssistant.

Leaked prompt text must not be copied verbatim into GrandpaAssistant code, docs intended for runtime use, tests, prompt builders, provider modules, or configuration. The goal is to study reusable architecture patterns only, then design original GrandpaAssistant behavior in later phases.

Useful areas to study:

- coding agent behavior
- planning
- tool usage
- safety
- memory
- voice behavior
- screen/vision workflows
- multi-agent orchestration

Implementation should happen only in later phases after the patterns are summarized at a high level and rewritten as original GrandpaAssistant-specific designs.

Do not load files from `reference/system_prompts_leaks/` in backend code.
