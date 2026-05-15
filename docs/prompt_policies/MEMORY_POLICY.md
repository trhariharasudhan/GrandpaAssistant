# Memory Policy

## Recent Versus Long-Term Memory

- Recent conversation context helps with immediate continuity.
- Long-term memory stores stable user preferences and facts only when explicitly saved or confidently inferred through approved flows.
- Current user instruction overrides older memory.

## Semantic Retrieval

- Semantic memory should retrieve relevant context, not decide truth by itself.
- Retrieved memories should be ranked by relevance and confidence.
- Low-confidence memory should be phrased cautiously.

## Avoid Invented Memory

- Do not claim to remember something unless it exists in memory or current context.
- If memory is absent, say so.
- Do not invent names, preferences, projects, or past choices.

## User Preferences

- Store preferences separately from facts.
- Keep language/tone/style preferences visible to prompt builders.
- Allow users to update or remove preferences.

## Memory Summarization

- Summaries should be compact, factual, and source-aware.
- Avoid storing sensitive raw transcripts.
- Prefer "user prefers X" over vague emotional interpretations unless explicitly stated.

## Privacy-Aware Behavior

- Avoid saving secrets, credentials, medical details, financial data, or private communications unless the user explicitly asks and the storage policy allows it.
- Do not expose memory contents unnecessarily.

## Memory Confidence

- Track whether memory is explicit, inferred, stale, or uncertain.
- Use uncertain memory as a question, not a claim.
- Ask before using sensitive memory in actions.
