# GrandpaAssistant Project Structure Guide

This is the backend-only orientation map for the active repository.

## Top-Level Folders

```text
GrandpaAssistant/
|- backend/       # Python assistant runtime, APIs, feature logic, assets
|- scripts/       # Backend smoke checks and Windows helper scripts
|- plugins/       # Local plugin examples
|- docs/          # Architecture, validation, and setup notes
|- tests/         # Backend unit tests
|- runtime/       # Local runtime output, ignored by git
|- main.py        # Thin launcher to backend/main.py
```

## Backend Layout

```text
backend/
|- desktop_backend_entry.py
|- main.py
|- fastapi_chat.py
|- app/
|  |- api/        # FastAPI endpoints
|  |- core/       # Assistant loop and command routing
|  |- shared/     # Config, DB, auth, LLM client, diagnostics, helpers
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
|- assets/        # Static runtime assets and examples
```

## Common Edit Points

- Command behavior: `backend/app/core/command_router.py`
- Desktop assistant loop: `backend/app/core/assistant.py`
- Desktop/API runtime: `backend/app/api/web_api.py`
- Chat API runtime: `backend/app/api/chat_api.py`
- Voice internals: `backend/app/features/voice/`
- OCR and vision internals: `backend/app/features/vision/`
- Settings defaults: `backend/app/shared/utils/config.py`
- Startup diagnostics: `backend/app/shared/startup_diagnostics.py`

## Practical Rules

1. Put new backend feature code in the matching domain folder under `backend/app/features/`.
2. Do not add business logic into `features/modules/`; that folder is compatibility-only.
3. Keep temporary files in ignored runtime/temp paths.
4. Keep backend runnable with `python backend\desktop_backend_entry.py`.
