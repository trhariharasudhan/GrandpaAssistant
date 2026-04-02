# GrandpaAssistant

GrandpaAssistant is a Windows-first personal desktop assistant built with Python. It combines voice interaction, text commands, personal memory, local AI, OCR-based screen tools, desktop automation, tray mode, dashboard reporting, and task workflows in a single assistant project.

It is designed for local usage on a personal Windows machine and uses Ollama for general AI replies, Tesseract OCR for screen reading, and local JSON/SQLite storage for memory, tasks, reminders, notes, and settings.

## Highlights

- Voice mode with wake word support
- Text mode for direct terminal usage
- Mode-specific replies
  - text mode gives text replies
  - voice mode gives voice replies
- Personal memory system backed by `memory.json` and SQLite
- Task, reminder, note, and dashboard workflows
- Weather, battery, and daily brief support
- App launch and system control commands
- OCR-based screen reading, text finding, and click actions
- Active window and app-specific context awareness
- Hand mouse mode using webcam gestures
- Tray/background mode
- Configurable sound and voice settings

## Completion Tracker

- Full finish checklist: [`PROJECT_COMPLETION_CHECKLIST.md`](C:\Users\ASUS\OneDrive\Desktop\GrandpaAssistant\PROJECT_COMPLETION_CHECKLIST.md)

## Feature Set

### Core Interaction

- Voice mode with wake word
- Text mode
- Stop speaking
- Dictation mode
- Startup, success, and error feedback sounds

### Personal Memory

- Answer questions from saved profile data
- Update saved memory by command
- Remove selected memory fields by command
- Profile summary
- Personal snapshot
- Focus suggestions
- Proactive nudges

### Productivity

- Add, list, complete, and delete tasks
- Add, list, and delete reminders
- Add, list, and delete notes
- Daily brief
- Urgent reminder report
- Full dashboard / status center

### Automation and Routines

- Preset modes
  - work mode
  - study mode
  - movie mode
- Custom routine creation and deletion
- Volume and brightness actions inside routines
- App launching inside routines

### Vision and Screen Actions

- Read full screen text
- Find text on screen
- Click visible text on screen
- Check whether screen text is visible
- Active app detection
- Current window title detection
- Browser tab summary
- Code editor file/context summary
- File Explorer folder summary
- WhatsApp screen summary

### System Controls

- Open installed apps
- Rescan installed apps
- Open File Explorer
- Screenshot capture
- Battery info
- Wi-Fi, Bluetooth, and Airplane Mode settings
- Minimize, maximize, restore, and switch app windows
- Lock, sleep, sign out, restart, and shutdown
- Smart confirmation for risky actions

### AI and Search

- Local AI replies through Ollama
- Wikipedia-style topic lookup
- Intent router with command registry
- Command history logging

### Settings and Config

- Show current settings
- Change wake word
- Change voice timeout values
- Enable/disable tray startup
- Mute/unmute sounds
- Toggle start/success/error sounds
- Voice profiles
  - normal
  - sensitive
  - noise cancel

## Tech Stack

- Python
- Ollama
- SpeechRecognition + PyAudio
- pyttsx3
- MediaPipe
- OpenCV
- PyAutoGUI
- Tesseract OCR
- pystray
- Pillow
- SQLite

## Project Structure

- `backend/app/core/` - assistant runtime, routing, tray, overlay, and UI orchestration
- `backend/app/api/` - local HTTP API used by the frontend
- `backend/app/shared/` - shared backend infra such as config, database, sound, and common helpers
- `backend/app/features/` - feature modules like tasks, notes, calendar, vision, voice, and automation
- `backend/data/` - runtime data and local persistence
- `backend/assets/` - sound assets and local model files
- `backend/main.py` - backend entry point
- `frontend/` - React + Electron UI
- `main.py` - thin root launcher that forwards to the backend entry point

## Requirements

Before running the assistant, make sure you have:

- Windows 10 or Windows 11
- Python 3.10 or newer
- Microphone for voice mode
- Speakers or headphones for voice replies
- Ollama installed locally
- Tesseract OCR installed for screen-reading features
- Webcam for hand mouse mode

## Installation

### 1. Clone the repository

```powershell
git clone https://github.com/trhariharasudhan/GrandpaAssistant.git
cd GrandpaAssistant
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Then activate the environment again.

### 3. Install dependencies

```powershell
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 4. Install Ollama

Download Ollama:

- [https://ollama.com/](https://ollama.com/)

Pull the model used by the project:

```powershell
ollama pull phi3
```

Make sure Ollama is running before using AI replies.

### 5. Install Tesseract OCR

Tesseract is required for OCR features such as:

- `read screen`
- `find <text>`
- `click <text>`

Recommended Windows build:

- [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki)

The project supports:

- `C:\Program Files\Tesseract-OCR\tesseract.exe`
- or `tesseract` available in `PATH`

## Running the Assistant

### Normal startup

```powershell
python backend/main.py
```

### React frontend startup

```powershell
scripts\windows\start_react_ui.cmd
```

This opens:

- Python backend assistant
- React frontend dev UI

Manual option:

```powershell
python backend/main.py
cd frontend
npm install
npm run dev
```

### React frontend with browser

```powershell
scripts\windows\start_react_full.cmd
```

This opens:

- Python backend
- React dev server
- browser at `http://127.0.0.1:4173`

### React desktop shell

```powershell
scripts\windows\start_react_desktop.cmd
```

This opens:

- Python backend
- React dev server
- Electron desktop shell

### Frontend-only launchers

If the backend is already running in tray or another window:

```powershell
scripts\windows\start_react_frontend.cmd
scripts\windows\start_react_electron.cmd
```

### Build portable desktop app

```powershell
scripts\windows\build_react_desktop.cmd
```

### Setup portable app shortcut

```powershell
scripts\windows\setup_portable_desktop.cmd
```

To enable startup launch for the packaged app:

```powershell
scripts\windows\setup_portable_desktop.cmd /startup-on
```

### Start directly in tray mode

```powershell
python backend/main.py --tray
```

At startup choose:

- `1` for voice mode
- `2` for text mode

## Usage Examples

### Voice Mode

Wake word:

```text
hey grandpa
```

Example voice commands:

```text
what time
weather
dashboard
start dictation
stop dictation
background mode
```

### Text Mode

Example text commands:

```text
what time
what is my name
weather in chennai
dashboard
open notepad
take a note buy milk tomorrow
list notes
read screen
find login
click search
```

## Command Groups

### Time and Calendar

- `what time`
- `what is date`
- `what day`
- `current month`
- `current year`
- `week number`

### Memory and Profile

- `what is my name`
- `my father details`
- `my github`
- `my goals`
- `tell me about myself`
- `personal snapshot`
- `what should i focus on`
- `give me a suggestion`

### Memory Updates

- `update my father age to 58`
- `set my wake up time to 6 am`
- `remove my twitter`

### Tasks, Reminders, and Notes

- `add task finish report`
- `list tasks`
- `complete task 1`
- `remind me to pay EB bill tomorrow`
- `list reminders`
- `take a note call client next week`
- `list notes`
- `delete note 1`

### Dashboard and Daily Status

- `daily brief`
- `check reminders`
- `dashboard`
- `status center`
- `full report`

### Weather

- `weather`
- `what is the weather`
- `weather in bangalore`
- `forecast in chennai`

### Apps and System

- `open notepad`
- `open explorer`
- `switch to chrome`
- `minimize chrome`
- `maximize chrome`
- `restore chrome`
- `close notepad`
- `take screenshot`
- `restart`
- `shutdown`

### Vision and OCR

- `read screen`
- `find login`
- `click search`
- `is submit visible`
- `what app am i using`
- `what window is open`
- `what am i seeing`
- `summarize current browser page`
- `summarize current code editor`
- `what folder am i in`

### Dictation

- `start dictation`
- `stop dictation`
- `start detection`
- `stop detection`

Supported dictation phrases:

- `comma`
- `full stop`
- `question mark`
- `new line`
- `enter`
- `backspace`

### Modes and Tray

- `list modes`
- `start work mode`
- `start study mode`
- `start movie mode`
- `create mode coding volume 25 brightness 60 apps chrome, notepad`
- `background mode`
- `restore assistant`

### Settings

- `show settings`
- `mute sounds`
- `unmute sounds`
- `turn off success sound`
- `enable tray startup`
- `disable tray startup`
- `set wake word to hey captain`
- `set initial timeout to 20`
- `set active timeout to 90`
- `enable sensitive voice mode`
- `enable noise cancel mode`

## Local Data Files

Common runtime files under `backend/data/`:

- `memory.json` - personal memory profile
- `assistant.db` - SQLite database for memory/history
- `tasks.json` - tasks and reminders
- `notes.json` - saved notes
- `settings.json` - local settings

If this repository is public, review personal data before pushing runtime files.

## Troubleshooting

### Voice mode is not detecting well

Try:

- `enable sensitive voice mode`
- `enable noise cancel mode`
- restart the assistant after changing voice mode
- check Windows microphone input level

### `python` command not found

Install Python and ensure it is added to `PATH`.

### AI not responding

Make sure Ollama is installed, running, and that the required model is pulled:

```powershell
ollama list
```

### OCR not working

Make sure Tesseract OCR is installed and reachable through the configured path or system `PATH`.

### Tray mode not working

Make sure required dependencies are installed:

- `pystray`
- `Pillow`

### Hand mouse not starting

Check:

- webcam permission
- MediaPipe and OpenCV installation
- whether another app is already using the camera

## Git Ignore Recommendation

Keep local runtime files out of source control when needed:

```gitignore
.venv/
__pycache__/
*.pyc
backend/data/settings.json
```

## License

No license file is currently included in this repository. Add a license if you plan to distribute or publish the project widely.
