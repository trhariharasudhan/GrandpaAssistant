# Grandpa Assistant Completion Checklist

This checklist is the practical finish line for turning the current codebase into a stable product.

## Phase 1: Environment Recovery

- [x] Fix Python installation so `python`, `py`, and `.venv` work normally on Windows.
- [x] Recreate `.venv` and reinstall backend dependencies from [`backend/requirements.txt`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\backend\requirements.txt).
- [x] Reinstall frontend packages in [`frontend`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\frontend).
- [x] Confirm `python main.py` stays running.
- [x] Confirm `npm run dev` works in [`frontend`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\frontend).

Acceptance:
- Backend starts without silent exit.
- Frontend loads without build/runtime errors.

## Phase 2: Startup Stability

- [x] Fix any startup crash in UI mode.
- [x] Confirm text mode, voice mode, and UI mode all launch cleanly.
- [x] Verify API server starts from [`backend/app/api/web_api.py`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\backend\app\api\web_api.py).
- [x] Verify tray mode still works.

Acceptance:
- `python main.py` opens the assistant UI reliably.
- No immediate exit, no hidden startup exception.

## Phase 3: Core Feature Freeze

- [ ] Mark V1 must-have features only.
- [ ] Keep stable:
  - chat
  - voice wake
  - tasks/reminders/notes
  - file upload + RAG
  - planner/dashboard
- [ ] Move optional features to V2 bucket:
  - object detection extras
  - advanced automation experiments
  - niche model workflows

Acceptance:
- V1 scope is small, clear, and testable.

## Phase 4: Chat and RAG Completion

- [x] Verify PDF upload.
- [x] Verify DOCX upload.
- [x] Verify TXT upload.
- [x] Add remove document action from chat session.
- [x] Add source citation in answers for uploaded docs.
- [x] Add multiple-document retrieval support.
- [x] Add empty/error state for unreadable files.

Acceptance:
- User can upload a file, ask questions, and get reliable document-based answers.

## Phase 5: Voice Mode Completion

- [ ] Verify wake word flow end-to-end.
- [ ] Verify follow-up window.
- [ ] Verify interrupt commands: `stop`, `wait`, `cancel`, `listen`.
- [ ] Verify sleeping/awake/follow-up/speaking states in UI.
- [ ] Add desktop popup/chime settings if still missing.
- [ ] Add full voice tuning controls:
  - wake threshold
  - follow-up timeout
  - wake retry
  - fallback toggle

Acceptance:
- Voice mode feels hands-free and predictable.

## Phase 6: Tasks, Planner, and Daily Use

- [ ] Stabilize task add/list/complete/delete.
- [ ] Stabilize reminder add/list/delete.
- [ ] Stabilize notes add/list/search.
- [ ] Add or finalize `plan my day`.
- [ ] Add or finalize `what should I do now`.
- [ ] Add focus mode if it is part of V1.

Acceptance:
- Assistant is useful for daily personal productivity.

## Phase 7: UI and UX Final Polish

- [ ] Clean settings layout.
- [ ] Improve loading and error states.
- [ ] Keep composer, upload, and session flow simple.
- [ ] Make RAG attachments visible and manageable.
- [ ] Ensure theme consistency across all panels.
- [ ] Remove low-value clutter from dashboard/settings.

Acceptance:
- UI feels intentional, stable, and easy to use.

## Phase 8: Testing Pass

- [ ] Create a smoke checklist file.
- [ ] Run and verify:
  - app startup
  - chat send/reply
  - streaming reply
  - session create/switch/delete
  - export chat
  - file upload + RAG
  - voice mode
  - tasks/reminders/notes
  - object detection, only if kept in V1
- [ ] Fix all user-facing blockers found in smoke pass.

Acceptance:
- No known critical blocker in normal daily use flow.

## Phase 9: Repo Cleanup

- [ ] Remove temporary test files and logs.
- [ ] Update [`.gitignore`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\.gitignore) for new temp/runtime outputs.
- [ ] Keep runtime data out of source control where possible.
- [ ] Remove stale docs and duplicated instructions.

Acceptance:
- Repo looks clean and maintainable.

## Phase 10: Release Readiness

- [ ] Update [`README.md`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\README.md).
- [ ] Add quick setup instructions.
- [ ] Add first-run notes for Python, OCR, and API keys.
- [ ] Verify `scripts/windows` launchers.
- [ ] Build desktop/package flow once.

Acceptance:
- Another machine/user can set it up with minimal confusion.

## Priority Order

1. Environment recovery
2. Startup stability
3. Chat + RAG completion
4. Voice completion
5. Planner/productivity stabilization
6. UI polish
7. Testing pass
8. Repo cleanup
9. Release readiness

## Immediate Next Actions

1. Fix broken Python installation / `.venv`
2. Confirm `python main.py` stays alive
3. Test uploaded PDF/DOCX RAG flow
4. Add document remove button
5. Run full smoke checklist
