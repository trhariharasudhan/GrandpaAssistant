# GrandpaAssistant Project Structure Guide

This file is the quick orientation map for the repository.

## 1) Top-Level Folders

```text
GrandpaAssistant/
|- backend/       # Python assistant runtime, API, and feature logic
|- frontend/      # React + Electron desktop UI
|- scripts/       # Helper scripts (mostly Windows launch/build)
|- plugins/       # Local plugin examples
|- docs/          # Product scope, roadmap, and structure docs
|- main.py        # Thin launcher to backend/main.py
```

## 2) Backend Layout

```text
backend/
|- main.py
|- app/
|  |- api/        # FastAPI endpoints
|  |- core/       # Assistant loop, command router, tray, overlay, UI glue
|  |- shared/     # Config, DB, sound, LLM client, shared helpers
|  |- features/   # Domain modules
|     |- productivity/
|     |- system/
|     |- automation/
|     |- intelligence/
|     |- voice/
|     |- vision/
|     |- integrations/
|     |- security/
|     |- modules/ # Compatibility aliases for legacy imports
|- assets/        # Static runtime assets (sounds, models)
|- data/          # Local runtime state (JSON/SQLite)
|- logs/          # Runtime logs
```

## 3) Frontend Layout

```text
frontend/
|- src/
|  |- components/
|  |- constants/
|  |- utils/
|  |- App.jsx
|  |- main.jsx
|- electron/      # Electron main/preload
|- assets/
```

## 4) What To Edit For Common Tasks

- New voice/text command behavior: `backend/app/core/command_router.py`
- Voice runtime state and APIs: `backend/app/api/web_api.py`
- Voice recognition/tuning internals: `backend/app/features/voice/listen.py`
- Productivity feature logic: `backend/app/features/productivity/`
- System controls: `backend/app/features/system/`
- UI actions and controls: `frontend/src/App.jsx`
- UI reusable blocks: `frontend/src/components/`
- Settings defaults: `backend/app/shared/utils/config.py`

## 5) Practical Rules To Keep Structure Clean

1. Put new backend feature code in the correct domain folder under `backend/app/features/`.
2. Do not add new business logic into `features/modules/`; that folder is alias-only.
3. Keep temporary test files in `scripts/` or local ignored paths, not the repo root.
4. Update this file when adding major new folders or moving module ownership.

## 6) Why `.env` And `.env.example` Both Exist

- `.env` is your real local secrets/runtime config (machine-specific, never commit).
- `.env.example` is a safe template with placeholder values so setup is easy for new machines/users.
- They are intentionally both needed; they are not duplicate files.

## 7) Runtime Files You Can Ignore In Explorer

- `__pycache__/` folders
- `.venv/`
- `runtime/data/chat_history.json`
- `runtime/data/apps_cache.json`
- `runtime/data/assistant.db`
- `runtime/data/chat_state.json`

These are generated while running the app and are not source code.
