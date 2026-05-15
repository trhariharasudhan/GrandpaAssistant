# Prompt Builder Audit

Phase 6 backend-only prompt-building consolidation audit. This phase creates a shared prompt boundary and routes low-risk callers through adapters without removing old prompt functions.

| Module | Prompt Inputs | Memory Source | Context Source | Language Style | Used By | Migration Status |
| --- | --- | --- | --- | --- | --- | --- |
| `backend/app/core/prompts/*` | `PromptBuildRequest`, user message, channel, persona, tone, context blocks | Passed saved-memory lines | Passed history, local knowledge, context blocks | Tamil, Tanglish, English, English-only mixed-input mode | New shared boundary | COMPLETE |
| `backend/app/core/chatbot/prompt_builder.py` | Terminal user message, saved terminal memories, recent terminal history | `ChatMemory.list_memories()` | `ChatMemory.recent_messages()` | Same-language Tamil/Tanglish/English | `ChatbotEngine.reply()` | MIGRATED_WRAPPER |
| `backend/app/cli/chat.py` | User CLI input and slash commands | Indirect through `ChatbotEngine` | Terminal session history | Terminal prompt builder | Terminal chatbot CLI | NO_DIRECT_PROMPT |
| `backend/app/shared/brain/ai_engine.py` | Command-router prompt, persona, compact voice flag | `brain.memory_engine`, semantic memory | Emotion, mood, cognition, recent `conversation_history` | English-only for mixed input | `command_router.ask_ollama` paths and web/browser intelligence | MIGRATED_WRAPPER |
| `backend/app/api/web_api.py` | Session, user message, mood snapshot, chat settings | Semantic memory, session document context | Emotion, mood, cognition, tool mode, document context | English-only mixed-input guidance | Active desktop backend API | MIGRATED_WRAPPER |
| `backend/app/api/chat_api.py` | Message, history, mood, hardware context | Direct memory search, semantic memory | Hardware manager, emotion, mood, cognition | English-only mixed-input guidance | Alternate chat API app | MIGRATED_WRAPPER |
| `backend/app/core/command_router.py` | Commands passed to `ask_ollama` | Indirect through `ai_engine` | Follow-up/topic context | Indirect through `ai_engine` | Desktop command router | INDIRECT |

## Shared Boundary

`backend/app/core/prompts` now owns reusable primitives for system/personality prompts, Tamil/English/Tanglish style instructions, saved memories, recent history, local knowledge context, safety rules, code-answer instructions, terminal vs desktop/voice/API channel differences, and route-specific chat prompt adapters.

## Migration Notes

- Terminal chatbot behavior now flows through `core.prompts.build_terminal_prompt()`.
- `brain.ai_engine._build_prompt()` now uses `core.prompts.build_prompt()` while preserving its existing persona, memory, emotion, mood, intelligence, and compact voice instructions.
- `web_api.py` and `chat_api.py` now keep their old helper names, but delegate prompt assembly to `core.prompts.route_adapters`.
- Existing public prompt functions remain in place as wrappers.
