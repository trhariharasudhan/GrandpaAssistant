# V1 Smoke Checklist

Date: 02 April 2026

This file tracks Phase 8 smoke status for the V1 scope in [`docs/V1_SCOPE.md`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\docs\V1_SCOPE.md).

## Automated Runs

1. Frontend build
   - Command: `cmd /c npm run build` (run in `frontend`)
   - Result: PASS
2. Chat, sessions, streaming, export, file upload + RAG
   - Command: `cmd /c ".venv\Scripts\activate.bat && python scripts\dev\chat_rag_smoke_check.py"`
   - Result: PASS (`overall_ok=True`)
3. Voice mode
   - Command: `cmd /c ".venv\Scripts\activate.bat && python scripts\dev\voice_smoke_check.py"`
   - Result: PASS (`overall_ok=True`)
4. Tasks, reminders, notes
   - Command: `cmd /c ".venv\Scripts\activate.bat && python scripts\dev\productivity_smoke_check.py"`
   - Result: PASS (`overall_ok=True`)
5. Planner and focus mode
   - Command: `cmd /c ".venv\Scripts\activate.bat && python scripts\dev\planner_focus_smoke_check.py"`
   - Result: PASS (`overall_ok=True`)
6. App startup and health readiness
   - Command: `cmd /c ".venv\Scripts\activate.bat && python scripts\dev\startup_smoke_check.py"`
   - Result: PASS (`overall_ok=True`)

## Phase 8 Coverage Map

- [x] App startup
  - Startup flow is validated by `scripts/dev/startup_smoke_check.py`.
- [x] Chat send/reply
- [x] Streaming reply
- [x] Session create/switch/delete
- [x] Export chat
- [x] File upload + RAG
- [x] Voice mode
- [x] Tasks/reminders/notes
- [x] Object detection, only if kept in V1
  - Marked not required because object detection is in V2 bucket per scope freeze.

## Current Result

- Critical blockers found: none in automated V1 scope checks.
- Phase 8 smoke coverage is complete for the V1 scope.
