# V1 Backend Smoke Checklist

Date: 02 April 2026

This checklist tracks backend-only smoke coverage for the V1 scope in `docs/V1_SCOPE.md`.

## Automated Runs

1. Chat, sessions, streaming, export, file upload, and RAG
   - Command: `python scripts\dev\chat_rag_smoke_check.py`
   - Expected: `overall_ok=True`
2. Voice mode
   - Command: `python scripts\dev\voice_smoke_check.py`
   - Expected: `overall_ok=True`
3. Tasks, reminders, and notes
   - Command: `python scripts\dev\productivity_smoke_check.py`
   - Expected: `overall_ok=True`
4. Planner and focus mode
   - Command: `python scripts\dev\planner_focus_smoke_check.py`
   - Expected: `overall_ok=True`
5. Backend startup and API health readiness
   - Command: `python scripts\dev\startup_smoke_check.py`
   - Expected: `overall_ok=True`

## Coverage Map

- [x] Backend startup
- [x] Chat send/reply
- [x] Streaming reply
- [x] Session create/switch/delete
- [x] Export chat
- [x] File upload and RAG
- [x] Voice mode
- [x] Tasks/reminders/notes
- [x] Optional object detection guarded behind dependency checks

## Current Result

- Critical blockers found: none in automated backend V1 scope checks.
