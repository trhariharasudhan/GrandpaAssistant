# Grandpa Assistant Backend Completion Checklist

This checklist is the practical finish line for keeping the current backend-only codebase stable.

## Environment

- [x] Recreate `.venv` and install `backend/requirements.txt`.
- [x] Confirm `python backend\desktop_backend_entry.py` starts the assistant.
- [x] Confirm `python backend\main.py` starts the API runtime.
- [x] Confirm `python backend\fastapi_chat.py` exposes the chat API app.

Acceptance:
- Backend entry points start without silent exit.
- Missing optional dependencies are reported as warnings instead of startup crashes.

## Startup Stability

- [x] Validate startup with `scripts/dev/startup_smoke_check.py`.
- [x] Keep startup doctor checks for Python, data/log paths, settings, Ollama, OCR, voice, vision, IoT, and launchers.
- [x] Keep backend startup runnable without desktop UI packaging.

Acceptance:
- `python backend\desktop_backend_entry.py` remains the primary run path.

## Core Feature Freeze

- [x] Preserve chat, memory, voice, tasks, reminders, notes, file upload, RAG, automation, IoT, OCR, and vision systems.
- [x] Treat hardware and AI integrations as optional unless configured.
- [x] Keep protected entry points stable:
  - `backend/desktop_backend_entry.py`
  - `backend/main.py`
  - `backend/fastapi_chat.py`
  - `scripts/dev/startup_smoke_check.py`

Acceptance:
- Core backend behavior remains intact after cleanup.

## Testing Pass

- [x] Run `python -m unittest discover -s tests -v`.
- [x] Run `python scripts\dev\startup_smoke_check.py`.
- [x] Run backend-wide `python -m py_compile`.
- [x] Run additional smoke scripts when changing a feature area.

Acceptance:
- No known critical backend blocker in normal daily use flow.

## Repo Cleanup

- [x] Remove inactive app workspaces from the active project.
- [x] Remove obsolete startup/build scripts for removed UI packaging.
- [x] Keep runtime data and secrets ignored.
- [x] Keep docs aligned with backend-only architecture.

Acceptance:
- The repository presents a clear backend-only setup.

## Immediate Next Actions

1. Run the backend validation commands after every backend cleanup.
2. Keep optional dependency failures visible in diagnostics.
3. Continue splitting oversized route modules into routers when making feature changes.
