# GrandpaAssistant

GrandpaAssistant is a Windows-focused personal desktop assistant built with Python. It combines voice and text interaction with local AI responses, system controls, application launching, OCR-based screen reading, calendar utilities, and gesture-based hand mouse control.

The project is designed for local usage on a personal machine. It uses Ollama for AI responses, Windows-native utilities for system actions, and a local JSON memory store for personal context.

## Features

- Voice mode with wake-word based interaction
- Text mode for direct command input
- Local AI responses through Ollama
- Personal memory lookup and storage
- Date, time, and calendar commands
- Application launch, switch, minimize, maximize, and close controls
- Volume and brightness controls
- Screenshot capture
- OCR-based screen reading and on-screen text click support
- Media controls for play, pause, next, and previous
- Hand mouse control using webcam gestures

## Tech Stack

- Python
- Ollama
- SpeechRecognition + PyAudio
- pyttsx3
- MediaPipe
- OpenCV
- PyAutoGUI
- Tesseract OCR

## Project Structure

Top-level files and folders:

- `main.py`
- `requirements.txt`
- `README.md`
- `brain/`
- `controls/`
- `core/`
- `data/`
- `modules/`
- `sounds/`
- `utils/`
- `vision/`
- `voice/`

Key folders:

- `core/` - main assistant loop and command routing
- `brain/` - AI engine, memory handling, and personal-question detection
- `modules/` - web, calendar, app scan, media, and system command logic
- `controls/` - brightness and volume controls
- `vision/` - hand mouse and OCR utilities
- `voice/` - speech input and output
- `data/` - local memory and cached app data
- `sounds/` - assistant sound effects

## Requirements

Before running the project, make sure you have:

- Windows 10 or Windows 11
- Python 3.10 or newer
- A working microphone for voice mode
- Speakers or headphones for spoken responses
- Ollama installed locally
- Tesseract OCR installed for screen-reading features
- Webcam for hand mouse control

## Installation

### 1. Clone or download the project

```powershell
git clone <your-repo-url>
cd GrandpaAssistant
```

If you downloaded a ZIP, extract it and open the project folder in PowerShell.

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Then activate the environment again.

### 3. Install Python dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install and prepare Ollama

Install Ollama from:

- [Ollama](https://ollama.com/)

Then pull the model used by this project:

```powershell
ollama pull phi3
```

Make sure Ollama is running before starting the assistant.

### 5. Install Tesseract OCR

Tesseract is required for:

- `read screen`
- `open file <text on screen>`

Install Tesseract and make sure `tesseract.exe` is available in one of these locations:

- `C:\Program Files\Tesseract-OCR\tesseract.exe`
- or in your system `PATH`

Recommended download:

- [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki)

## Usage

Run the assistant:

```powershell
python main.py
```

At startup you will be asked to choose an input mode:

- `1` - Voice mode
- `2` - Text mode

## How To Use

### Text Mode

Choose `2` when prompted, then type commands such as:

```text
what time
what is my name
tell me about india
open notepad
read screen
start mouse
stop mouse
take screenshot
increase volume
brightness down
```

Exit text mode with:

```text
exit
```

### Voice Mode

Choose `1` when prompted.

Wake word:

```text
hey grandpa
```

After the wake word, you can speak commands. To leave voice mode:

```text
exit assistant
```

## Example Commands

### Time and Date

- `what time`
- `what is date`
- `what day`
- `current month`
- `current year`
- `week number`

### Personal Memory

- `my name is Hari`
- `what is my name`
- `who am i`
- `clear memory`

### Web and AI

- `who is A. P. J. Abdul Kalam`
- `tell me about india`
- `what is artificial intelligence`

### Apps and System Controls

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

### Media and Device Controls

- `play`
- `pause`
- `next`
- `previous`
- `volume up`
- `volume down`
- `mute`
- `brightness up`
- `brightness down`

### Screen and Vision

- `read screen`
- `open file settings`
- `start mouse`
- `stop mouse`

## Notes

- The assistant is currently tailored for Windows.
- AI responses depend on Ollama being available at `http://localhost:11434`.
- Hand mouse mode uses the webcam and can be stopped with `Esc`.
- OCR output quality depends on screen clarity, font size, and UI complexity.
- Personal data is stored locally in `data/memory.json`.

## Troubleshooting

### `python` command not found

Install Python and ensure it is added to `PATH`.

### Voice input not working

Check:

- microphone permissions
- PyAudio installation
- Windows input device settings

### AI not responding

Make sure Ollama is installed, running, and that the `phi3` model has been pulled:

```powershell
ollama list
```

### OCR not working

Make sure Tesseract OCR is installed and `tesseract.exe` is reachable.

### Hand mouse not starting

Check:

- webcam access permissions
- MediaPipe and OpenCV installation
- whether another app is already using the camera

## Dependency Notes

The current `requirements.txt` matches the packages directly used by the project source files. During cleanup:

- added `comtypes` because it is directly imported for volume control
- removed unused `wikipedia`
- removed redundant `opencv-contrib-python`

## License

No license file is currently included in this project. Add one if you plan to publish or share it publicly.
