# Prompt Patterns For GrandpaAssistant

## Overview

This document summarizes reusable AI assistant architecture patterns observed from the local reference folder at `reference/system_prompts_leaks/`.

No leaked prompt text is copied here. These are original, high-level patterns adapted for GrandpaAssistant's backend-only Windows assistant architecture.

## Top Reusable Patterns

### 1. Role + Boundary Separation

Pattern: Strong assistants separate identity, operating boundaries, tool rules, safety rules, and final-answer style.

How it helps GrandpaAssistant:

- Keeps GrandpaAssistant's warm elder-assistant identity distinct from backend tool execution.
- Makes it easier to audit prompt-builder sections.
- Prevents voice/chat personality from leaking into safety-critical system actions.

Do not copy:

- Vendor-specific identity wording.
- Product-specific policy text.
- Internal tool naming or proprietary hierarchy.

### 2. Plan Before High-Risk Action

Pattern: Coding and automation agents pause to inspect context, form a short plan, and only then mutate files or use tools.

How it helps GrandpaAssistant:

- Useful before editing code, changing settings, running shell commands, or automating Windows actions.
- Matches the existing command-router cleanup approach: tests first, small extraction, then validation.

Do not copy:

- Exact planning templates.
- Forced verbose planning for tiny tasks.

### 3. Tool Discipline

Pattern: Tool-capable agents define when tools are mandatory, when tools are wasteful, and how to verify results.

How it helps GrandpaAssistant:

- Terminal chatbot can avoid fake claims by using tools only when needed.
- Desktop automation can require readback/verification after risky actions.
- Browser/research mode can cite source-derived conclusions instead of guessing.

Do not copy:

- Reference-specific tool schemas.
- Exact browser or shell instructions from leaked prompts.

### 4. Safety Layer Before Execution

Pattern: Assistants classify actions by risk and gate destructive or external actions behind confirmation.

How it helps GrandpaAssistant:

- Fits existing confirmation state in `command_router.py`.
- Helps separate read-only summaries from mutation commands.
- Supports future safety handlers for shell, files, apps, IoT, contacts, emergency flows, and security actions.

Do not copy:

- Policy phrasing.
- Overbroad refusal language that would make GrandpaAssistant less useful.

### 5. Context And Memory Hygiene

Pattern: Strong assistants distinguish conversation context, saved memory, local project state, active app/screen state, and temporary tool observations.

How it helps GrandpaAssistant:

- Prevents stale memories from overriding current user intent.
- Helps voice mode remain concise while coding/research mode can be detailed.
- Supports separate memory handlers and prompt context blocks.

Do not copy:

- Any specific memory fields from reference products.
- Vendor-specific hidden profile formats.

### 6. Multimodal And Screen Workflow Separation

Pattern: Vision/screen agents separate "what is visible" from "what action should be taken."

How it helps GrandpaAssistant:

- Screen explanation, OCR, object detection, and UI automation should remain distinct.
- Read-only screen summaries can be safe; click/type/execute actions need confirmation.

Do not copy:

- Exact screen-control instructions.
- Platform-specific UI claims not true for GrandpaAssistant.

### 7. Research Grounding

Pattern: Research assistants separate search, source reading, synthesis, and final answer.

How it helps GrandpaAssistant:

- Browser/research mode can avoid hallucination by requiring source-backed claims.
- Useful for medical/legal/financial or current-info questions.

Do not copy:

- Citation formats or source-prioritization text verbatim.

### 8. Multi-Agent Work Split

Pattern: Agentic systems split planning, execution, review, memory, research, and specialized tool work.

How it helps GrandpaAssistant:

- Future architecture can use planner/executor/verifier roles without rewriting all runtime behavior.
- Command router can remain public entrypoint while delegating specialized intent groups.

Do not copy:

- Product-specific agent names.
- Hidden routing policies from reference prompts.

### 9. Verification Before Final Answer

Pattern: Agents verify command output, tests, build status, or source evidence before finalizing.

How it helps GrandpaAssistant:

- Matches backend cleanup workflow.
- Reduces false "done" claims.
- Supports final answer sections for tests passed, risks, and next step.

Do not copy:

- Exact final response templates.

## Recommended Implementation Order

1. Strengthen prompt-builder section boundaries for identity, safety, memory, tools, and final answer style.
2. Add explicit mode rules for coding, voice, screen, research, and automation.
3. Add action risk categories shared by command router, terminal chatbot, and desktop automation.
4. Add verification contracts for shell, file edits, web research, and screen actions.
5. Add optional multi-agent orchestration only after the single-agent backend stays stable.

## What Not To Copy

- Leaked prompt text verbatim.
- Proprietary identity/personality wording.
- Hidden policy language.
- Tool schemas or internal product names.
- Provider-specific safety phrasing.
- Any reference file as a runtime dependency.
