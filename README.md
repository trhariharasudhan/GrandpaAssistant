# GrandpaAssistant

GrandpaAssistant is a Windows-first personal desktop assistant built with Python, FastAPI, React, and local AI tools. It combines voice and text interaction, local memory, OCR-based screen actions, system controls, productivity workflows, and an offline multi-model backend powered by Ollama.

The project is designed for a personal Windows machine and keeps the core assistant workflow local wherever possible.

## What It Does

- Voice and text assistant modes
- Local AI replies through Ollama
- Multi-model routing for general, fast, and coding prompts
- OCR and screen-reading tools with Tesseract
- Window, app, and desktop context awareness
- Tasks, reminders, notes, and dashboard workflows
- System controls for apps, audio, brightness, screenshots, and more
- React/Electron frontend support
- Tray/background mode for desktop usage

## Architecture At A Glance

The repo currently has three main runtime layers:

- `backend/main.py` + `backend/app/core/assistant.py`
  - legacy terminal and tray assistant loop
  - voice mode, text mode, quick overlay, tray startup
- `backend/app/api/web_api.py`
  - main desktop/web/mobile API used by the React/Electron UI
  - chat sessions, auth, UI state, mobile companion, voice status, command bridge
- `backend/fastapi_chat.py` + `backend/app/api/chat_api.py`
  - smaller chat-first FastAPI surface for offline multi-model requests and diagnostics

The frontend has two shells on top of the desktop API:

- `frontend/`
  - React + Vite interface
- `frontend/electron/`
  - Electron wrapper that manages the backend process and desktop window/tray behavior

There is also a separate mobile companion client:

- `mobile/`
  - Expo React Native app that talks to the desktop API for pairing, remote commands, and mobile chat

## Local AI Stack

The repo now includes an offline FastAPI backend that routes requests by intent:

- General prompts -> `mistral:7b`
- Fast replies -> `phi3:mini`
- Coding prompts -> `deepseek-coder:6.7b`

Available API endpoints:

- `GET /health`
- `GET /models`
- `POST /ask`
- `POST /chat`
- `POST /chat/stream`

Example `/ask` request:

```json
{
  "prompt": "Write a Python function that returns the square of a number.",
  "mode": "coding"
}
```

`mode` supports:

- `auto`
- `general`
- `fast`
- `coding`

## Quick Start

### 1. Prerequisites

Recommended for the Windows setup in this repo:

- Windows 10 or Windows 11
- Python 3.11
- Ollama
- Tesseract OCR
- Node.js and npm for the frontend
- Microphone and speakers for voice features
- Webcam for gesture/vision features

### 2. Clone the Repository

```powershell
git clone https://github.com/trhariharasudhan/GrandpaAssistant.git
cd GrandpaAssistant
```

### 3. Install Python Dependencies

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

### 4. Install Frontend Dependencies

```powershell
cd frontend
npm install
cd ..
```

### 5. Install the Offline AI Stack

Fast path for the local Ollama setup:

```powershell
scripts\windows\setup_offline_ai_stack.ps1
```

That script installs the required Python AI packages, pulls the local Ollama models, and warms up the offline model cache for:

- `sentence-transformers/all-MiniLM-L6-v2`
- `ai4bharat/IndicBERTv2-MLM-only`
- Whisper base

### 6. Verify Ollama Models

```powershell
ollama list
```

Expected core models:

- `mistral:7b`
- `phi3:mini`
- `deepseek-coder:6.7b`

### 7. Run the Backend

For the desktop UI, Electron shell, and mobile companion API, run the desktop backend:

```powershell
python backend\desktop_backend_entry.py
```

If you want the legacy assistant launcher with the terminal/tray workflow:

```powershell
python main.py
```

If you want only the smaller chat-first FastAPI service from `backend/fastapi_chat.py`:

```powershell
uvicorn main:app --host 127.0.0.1 --port 8000
```

## Optional Manual Offline Setup

If you want to install the local AI dependencies manually instead of using the setup script:

```powershell
pip install fastapi uvicorn requests opencv-python pytesseract sentence-transformers faiss-cpu fasttext vaderSentiment transformers
```

Then pull the Ollama models:

```powershell
ollama pull mistral:7b
ollama pull phi3:mini
ollama pull deepseek-coder:6.7b
```

Other optional local tools used by this project:

- Whisper for voice input
- Piper TTS for voice output
- IndicBERT through `transformers`

## Frontend and Desktop Launchers

React/Electron helpers are available under [`scripts/windows/`](scripts/windows/).

Common launch options:

```powershell
scripts\windows\start_react_desktop.cmd
scripts\windows\start_react_frontend.cmd
scripts\windows\start_react_electron.cmd
scripts\windows\build_react_desktop.cmd
```

Release and validation helpers:

```powershell
scripts\windows\check_assistant_health.cmd
scripts\windows\final_release_check.cmd
scripts\windows\export_release_manifest.cmd
scripts\windows\watch_hardware_changes.cmd
scripts\windows\validate_iot_setup.cmd
```

## App Authentication

The desktop/web app now includes a built-in local account system backed by SQLite.

- The first registered account becomes the `admin`
- Sessions are stored locally in the app database
- Chat archive and audit events are stored in SQLite

New auth endpoints:

- `GET /api/auth/bootstrap-status`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/auth/users`
- `GET /api/auth/audit`
- `GET /api/auth/chat-archive`

On first UI launch, create the first account from the login screen. After that, sign in normally.

## Project Structure

- [`main.py`](main.py) - root launcher and FastAPI app export
- [`backend/main.py`](backend/main.py) - backend bootstrap
- [`backend/app/api/`](backend/app/api/) - FastAPI endpoints
- [`backend/app/core/`](backend/app/core/) - assistant loop, routing, tray, overlays, UI wiring
- [`backend/app/shared/`](backend/app/shared/) - shared infrastructure, config, LLM helpers, DB utilities
- [`backend/app/features/`](backend/app/features/) - productivity, system, automation, vision, integrations, intelligence modules
- [`frontend/src/`](frontend/src/) - React app
- [`frontend/electron/`](frontend/electron/) - Electron shell
- [`scripts/windows/`](scripts/windows/) - Windows startup and build helpers
- [`docs/`](docs/) - docs, plans, structure notes

Detailed structure reference:

- [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)

## Docs

- [`docs/README.md`](docs/README.md)
- [`docs/PRODUCTION_AI_ASSISTANT_BLUEPRINT.md`](docs/PRODUCTION_AI_ASSISTANT_BLUEPRINT.md)
- [`docs/REAL_WORLD_VALIDATION_CHECKLIST.md`](docs/REAL_WORLD_VALIDATION_CHECKLIST.md)
- [`docs/FUTURE_FEATURE_ROADMAP.md`](docs/FUTURE_FEATURE_ROADMAP.md)
- [`docs/V1_SCOPE.md`](docs/V1_SCOPE.md)
- [`docs/PROJECT_COMPLETION_CHECKLIST.md`](docs/PROJECT_COMPLETION_CHECKLIST.md)

## Common Commands

Run the legacy assistant launcher:

```powershell
python main.py
```

Run the desktop/web/mobile backend used by React, Electron, and mobile:

```powershell
python backend\desktop_backend_entry.py
```

Run only the smaller chat-first FastAPI backend:

```powershell
uvicorn main:app --host 127.0.0.1 --port 8000
```

Start directly in tray mode:

```powershell
python main.py --tray
```

Verify Ollama:

```powershell
ollama list
```

Run automated validation:

```powershell
python -m unittest discover -s tests -v
python scripts\dev\productivity_smoke_check.py
python scripts\dev\startup_smoke_check.py
```

Build the frontend:

```powershell
cd frontend
npm run build
```

## Local Data and Privacy

Runtime data is stored locally under `backend/data/` and includes settings, notes, reminders, assistant state, and other machine-specific files.

This repo intentionally ignores private/runtime files such as:

- local tokens
- OCR/runtime caches
- SQLite state
- assistant settings and personal memory

If you make the repo public, do not commit personal data from `backend/data/`.

## Troubleshooting

### `python` not found

Install Python 3.11 and add it to `PATH`.

### Ollama replies are not working

Make sure Ollama is running and the required models are installed:

```powershell
ollama list
```

### OCR is not working

Install Tesseract OCR and keep it available in `PATH` or at:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

### Voice mode issues

Check:

- microphone permissions
- input level in Windows
- installed voice/audio dependencies

### Frontend issues

Reinstall frontend dependencies:

```powershell
cd frontend
npm install
```

## Current Status

This repository is actively evolving. The current codebase includes:

- the existing desktop assistant runtime
- frontend/dashboard work
- system and productivity upgrades
- the new offline Ollama multi-model backend

## License

No license file is currently included in this repository. Add one before wider redistribution if you want clear reuse terms.
