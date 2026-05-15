# Reference Audit

Date: 2026-05-15

## Reference Folder

`reference/system_prompts_leaks/` exists locally.

The folder is intended for local research only and is ignored through `.gitignore`.

## High-Level Folders Found

- `.github`
- `Anthropic`
- `Google`
- `Misc`
- `OpenAI`
- `Perplexity`
- `xAI`

## Most Useful For GrandpaAssistant

- `OpenAI`: useful to study coding-agent structure, tool-use boundaries, planning behavior, and multi-agent orchestration patterns.
- `Anthropic`: useful to study safety, careful tool usage, and assistant behavior framing.
- `Google`: useful to study planning, multimodal, and possible screen/vision workflow patterns.
- `Misc`: may contain cross-cutting examples, but should be reviewed carefully before using any ideas.

## Treat Carefully Or Avoid

- All folders must be treated as leaked-reference material. Do not copy prompt text verbatim.
- `.github` should be treated as repository metadata unless a later research phase explicitly needs workflow context.
- Provider-specific folders should not be used to imitate brand-specific wording, internal policy text, or proprietary prompt structure.

## Runtime Confirmation

No backend runtime code was changed in this phase.

No Python source files were modified.

GrandpaAssistant backend must not load or depend on `reference/system_prompts_leaks/`.

## Phase 1 High-Level Pattern Audit

Reviewed folders:

- `reference/system_prompts_leaks/Anthropic/`
- `reference/system_prompts_leaks/OpenAI/`
- `reference/system_prompts_leaks/Google/`
- `reference/system_prompts_leaks/Perplexity/`
- `reference/system_prompts_leaks/Misc/`
- `reference/system_prompts_leaks/xAI/`

High-level file counts observed:

- Anthropic: 38 files
- OpenAI: 82 files
- Google: 19 files
- Perplexity: 2 files
- Misc: 24 files
- xAI: 10 files

Documents created:

- `docs/prompt_research/PROMPT_PATTERNS_FOR_GRANDPAASSISTANT.md`
- `docs/prompt_research/HIGH_VALUE_RULES.md`
- `docs/prompt_research/SAFETY_PATTERNS.md`
- `docs/prompt_research/TOOL_USAGE_PATTERNS.md`
- `docs/prompt_research/AGENT_ARCHITECTURE_IDEAS.md`

The review focused on high-level architecture patterns only:

- coding assistant behavior
- planning before acting
- tool usage discipline
- shell and file safety
- memory/context boundaries
- voice and screen/vision workflows
- research/browser behavior
- multi-agent orchestration
- verification, hallucination reduction, and final-answer style

No backend runtime code was changed.

No Python source files were modified.

No reference prompt text should be copied verbatim into GrandpaAssistant.

Next phase recommendation: create original GrandpaAssistant prompt-policy design docs from these patterns, without editing runtime prompt builders yet.

## Phase 2 Original Prompt Policy Design

Status: COMPLETE.

Original GrandpaAssistant policy docs created under `docs/prompt_policies/`:

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
- `PHASE_2_SUMMARY.md`

No backend runtime code was changed.

No Python source files were modified.

No runtime prompt loading was added.

The policy documents are original GrandpaAssistant design material and must not copy leaked prompt text verbatim.
