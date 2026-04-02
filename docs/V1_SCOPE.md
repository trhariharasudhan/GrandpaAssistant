# GrandpaAssistant V1 Scope Freeze

This file locks the V1 scope so we can ship a stable build without feature sprawl.

## V1 Goal

Ship a reliable daily-use personal desktop assistant for Windows with strong chat, voice wake, productivity, and document Q&A flows.

## V1 Must-Have Features (In Scope)

1. Chat baseline
   - Send/receive chat messages
   - Streaming response
   - Session create/switch/delete
2. Voice wake baseline
   - Wake word trigger
   - Follow-up listening window
   - Interrupt commands (`stop`, `wait`, `cancel`, `listen`)
3. Productivity baseline
   - Tasks: add/list/complete/delete
   - Reminders: add/list/delete
   - Notes: add/list/search
4. File upload + RAG baseline
   - Upload PDF, DOCX, TXT
   - Ask questions over uploaded docs
   - Source citations in answers
   - Remove document from session
5. Planner and dashboard baseline
   - `plan my day`
   - `what should I do now`
   - Basic daily dashboard/status center

## V2 Bucket (Out of V1)

1. Object detection extras and advanced camera perception experiments
2. Advanced automation experiments and niche model workflows
3. Smart-home and security-heavy integrations (IoT controls, face unlock, voice biometrics)

## Freeze Rules

1. No new feature classes in V1 after this freeze.
2. Only bug fixes, stability fixes, and UX polish are allowed for V1.
3. Any new idea that is not in the V1 must-have list moves to the V2 bucket.

## Exit Criteria for V1

1. All in-scope features pass smoke testing without critical blockers.
2. Voice and productivity flows work reliably in normal daily usage.
3. Setup and startup are reproducible on a clean Windows machine.
