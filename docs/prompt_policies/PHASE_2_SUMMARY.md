# Phase 2 Summary

Status: COMPLETE as documentation/design only.

## Policy Docs Created

- `CORE_ASSISTANT_POLICY.md`
- `CODING_AGENT_POLICY.md`
- `TOOL_USAGE_POLICY.md`
- `AUTOMATION_SAFETY_POLICY.md`
- `MEMORY_POLICY.md`
- `VOICE_MODE_POLICY.md`
- `SCREEN_VISION_POLICY.md`
- `RESEARCH_BROWSER_POLICY.md`
- `RESPONSE_STYLE_POLICY.md`
- `FUTURE_MULTI_AGENT_POLICY.md`

## Highest-Priority Future Runtime Integrations

1. Add prompt-builder sections for identity, safety, tools, memory, and response style.
2. Add mode-specific prompt policies for coding, voice, vision, automation, and research.
3. Add a shared risk taxonomy for command router and prompt builders.
4. Add prompt behavior tests before runtime integration.
5. Keep reference prompt folders ignored and outside runtime.

## Recommended Future Architecture

```text
User request
  -> command/router or chat entrypoint
  -> prompt policy selector
  -> context builder
  -> safety/risk policy block
  -> mode-specific policy block
  -> provider manager
  -> verifier/validation layer
  -> response formatter
```

## Biggest Risks To Avoid

- Copying leaked prompt text into runtime.
- Letting prompt policy bypass command-router safety.
- Mixing voice brevity with weak confirmations.
- Giving screen/vision actions permission based only on observation.
- Claiming tests, tools, sources, or memories were checked when they were not.

## Implementation Roadmap Suggestions

1. Create prompt-policy data models or constants in a later phase.
2. Add tests for prompt section inclusion/exclusion.
3. Wire policies into existing `core.prompts` builders.
4. Add mode-specific adapters for terminal chat, API chat, and future voice/vision.
5. Add verification hooks for coding and automation workflows.
