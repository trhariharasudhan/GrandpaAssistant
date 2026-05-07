# GrandpaAssistant

GrandpaAssistant is a Windows-first Python backend for a local desktop assistant. The current active setup is backend-only: it runs from `backend\desktop_backend_entry.py` and keeps assistant logic, FastAPI endpoints, voice hooks, productivity modules, IoT helpers, plugins, tests, and Windows support scripts in this repository.

## Current Scope

- Python backend runtime for the Windows desktop assistant
- FastAPI chat and desktop APIs
- Local assistant command routing and module system
- Voice, productivity, system control, IoT, memory, and plugin integrations
- Local data under ignored runtime/data paths

App-client workspaces are not part of the active project right now. The backend still contains protected companion API logic where those features are part of the assistant backend.

## Project Layout

```text
GrandpaAssistant/
|-- backend/      Python assistant backend and runtime entry points
|-- docs/         Architecture, setup, validation, and release notes
|-- plugins/      Local assistant plugins
|-- scripts/      Backend, diagnostics, IoT, voice, and Windows helper scripts
|-- tests/        Backend unit tests
|-- runtime/      Local runtime output (ignored)
|-- main.py       Root launcher helper
|-- README.md
```

## Requirements

- Windows 10/11
- Python 3.11 recommended
- Optional: Ollama for local LLM responses
- Optional: microphone, Piper/Coqui/Whisper tooling, Tesseract, and IoT credentials depending on enabled features

## Setup

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
```

Optional local AI models:

```bat
ollama pull mistral:7b
ollama pull phi3:mini
ollama pull deepseek-coder:6.7b
```

## Run

Start the backend desktop assistant:

```bat
python backend\desktop_backend_entry.py
```

Optional chat API entry point:

```bat
python backend\fastapi_chat.py
```

Useful Windows helper scripts:

```bat
scripts\windows\start_assistant_console.cmd
scripts\windows\start_assistant_admin.cmd
scripts\windows\check_assistant_health.cmd
```

## API Surface

Desktop API examples:

- `GET /api/health`
- `POST /api/command`
- `POST /api/voice/start`
- `POST /api/voice/stop`

Chat API examples:

- `POST /chat`
- `POST /chat/stream`
- `GET /chat/history`

## Local Data And Secrets

Runtime output is local and should stay out of git. Secret-bearing files under `backend\data`, including app auth secrets, tokens, and credential files, are ignored by `.gitignore`.

Use checked-in example files such as `backend\assets\iot_credentials.example.json` as templates, then place real local credentials in ignored data/config locations.

## Validation

Run these checks before shipping backend changes:

```bat
python -m unittest discover -s tests -v
python scripts\dev\startup_smoke_check.py
```

Compile backend Python files:

```powershell
Get-ChildItem backend -Recurse -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
```

## Notes

- Backend runtime must remain runnable with `python backend\desktop_backend_entry.py`.
- Some optional capabilities need local services or hardware to be configured before they report fully ready.
- Keep secrets, generated databases, logs, and runtime output untracked.
