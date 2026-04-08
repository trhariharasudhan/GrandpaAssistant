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

- [x] Mark V1 must-have features only.
- [x] Keep stable:
  - chat
  - voice wake
  - tasks/reminders/notes
  - file upload + RAG
  - planner/dashboard
- [x] Move optional features to V2 bucket:
  - object detection extras
  - advanced automation experiments
  - niche model workflows
- [x] Publish V1 scope freeze doc: [`docs/V1_SCOPE.md`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\docs\V1_SCOPE.md).

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

- [x] Verify wake word flow end-to-end.
- [x] Verify follow-up window.
- [x] Verify interrupt commands: `stop`, `wait`, `cancel`, `listen`.
- [x] Verify sleeping/awake/follow-up/speaking states in UI.
- [x] Add desktop popup/chime settings if still missing.
- [x] Add full voice tuning controls:
  - wake threshold
  - follow-up timeout
  - wake retry
  - fallback toggle
- [x] Add voice smoke script for repeatable checks: [`scripts/dev/voice_smoke_check.py`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\scripts\dev\voice_smoke_check.py).

Acceptance:
- Voice mode feels hands-free and predictable.

## Phase 6: Tasks, Planner, and Daily Use

- [x] Stabilize task add/list/complete/delete.
- [x] Stabilize reminder add/list/delete.
- [x] Stabilize notes add/list/search.
- [x] Add or finalize `plan my day`.
- [x] Add or finalize `what should I do now`.
- [x] Add focus mode if it is part of V1.

Acceptance:
- Assistant is useful for daily personal productivity.

## Phase 7: UI and UX Final Polish

- [x] Clean settings layout.
- [x] Improve loading and error states.
- [x] Keep composer, upload, and session flow simple.
- [x] Make RAG attachments visible and manageable.
- [x] Ensure theme consistency across all panels.
- [x] Remove low-value clutter from dashboard/settings.

Acceptance:
- UI feels intentional, stable, and easy to use.

## Phase 8: Testing Pass

- [x] Create a smoke checklist file: [`docs/V1_SMOKE_CHECKLIST.md`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\docs\V1_SMOKE_CHECKLIST.md).
- [x] Run and verify:
  - app startup
  - chat send/reply
  - streaming reply
  - session create/switch/delete
  - export chat
  - file upload + RAG
  - voice mode
  - tasks/reminders/notes
  - object detection, only if kept in V1
- [x] Fix all user-facing blockers found in smoke pass.
  - No user-facing critical blockers found in the final smoke pass.

Acceptance:
- No known critical blocker in normal daily use flow.

## Phase 9: Repo Cleanup

- [x] Remove temporary test files and logs.
- [x] Update [`.gitignore`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\.gitignore) for new temp/runtime outputs.
- [x] Keep runtime data out of source control where possible.
  - Verified runtime folders are not tracked (`git ls-files runtime/data`, `git ls-files runtime/logs`).
- [x] Remove stale docs and duplicated instructions.
  - Consolidated tracking docs under `docs/` only.

Acceptance:
- Repo looks clean and maintainable.

## Phase 10: Release Readiness

- [x] Update [`README.md`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\README.md).
- [x] Add quick setup instructions.
- [x] Add first-run notes for Python, OCR, and API keys.
- [x] Verify `scripts/windows` launchers.
- [x] Build desktop/package flow once.
  - Verified with `cmd /c npm run desktop:build` in `frontend` (PASS).

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

1. Run `scripts\windows\final_release_check.cmd`.
2. Run the manual validation steps in `docs\REAL_WORLD_VALIDATION_CHECKLIST.md`.
3. Export the desktop release manifest with `scripts\windows\export_release_manifest.cmd`.
4. If needed, replace the local Smart Home demo config with your real local device config.
