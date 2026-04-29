# GrandpaAssistant 🤖🔥

A **Windows-first AI desktop assistant** built with **Python, FastAPI, React, and local AI (Ollama)** — designed to bring voice, automation, and intelligence into one unified system.

---

## 🚀 Demo (Coming Soon)

> Add screenshots / demo video here for best impact

---

## ✨ Features

* 🎙️ Voice + Text interaction (wake word support)
* ⚡ Fast local AI responses using multi-model routing
* 🧠 Session memory (remembers context & user info)
* 🖥️ Desktop automation (apps, volume, brightness, typing)
* 📊 Productivity tools (tasks, notes, reminders, dashboard)
* 🧩 Unified command system (single execution pipeline)
* 🌐 React + Electron desktop UI
* 🔌 FastAPI backend (chat, voice, UI, mobile support)

---

## 🧠 Architecture

All inputs flow through one unified pipeline:

```
Voice / Text / UI / Mobile
        ↓
AI + Context Layer
        ↓
Unified Command Router
        ↓
Module System
        ↓
Response (Text / Voice)
```

### 🔥 Key Highlights

* Single command pipeline (no duplicate logic)
* Modular and scalable design
* Supports multi-step execution
* Backward compatible with legacy modules

---

## 🛠️ Tech Stack

* **Backend:** Python, FastAPI
* **Frontend:** React, Vite, Electron
* **AI:** Ollama (Mistral, Phi3, DeepSeek)
* **Voice:** Whisper, Piper / Coqui
* **OCR:** Tesseract
* **Database:** SQLite

---

## ⚙️ Setup

### 1. Clone

```bash
git clone https://github.com/trhariharasudhan/GrandpaAssistant.git
cd GrandpaAssistant
```

---

### 2. Backend Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
```

---

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

---

### 4. Install Local AI (Ollama)

```bash
ollama pull mistral:7b
ollama pull phi3:mini
ollama pull deepseek-coder:6.7b
```

---

## ▶️ Run

### Backend

```bash
python backend\desktop_backend_entry.py
```

### Frontend

```bash
cd frontend
npm run dev
```

### Optional (Chat API)

```bash
python backend\fastapi_chat.py
```

---

## 📡 API Endpoints

**Desktop API**

* `GET /api/health`
* `POST /api/command`
* `POST /api/voice/start`
* `POST /api/voice/stop`

**Chat API**

* `POST /chat`
* `POST /chat/stream`
* `GET /chat/history`

---

## 📁 Project Structure

```
GrandpaAssistant/
├── backend/
├── frontend/
├── mobile/
├── runtime/   (ignored)
├── docs/
├── scripts/
└── README.md
```

---

## 🔐 Privacy & Local Data

* All user data stored locally (`runtime/`)
* No external data sharing by default
* Secrets are ignored via `.gitignore`

---

## 🧪 Validation

```bash
python -m unittest discover -s tests -v
```

---

## ⚠️ Notes

* Windows-first (desktop automation dependent)
* Requires microphone for voice mode
* Ollama must be running for AI responses

---

## 🧭 Roadmap

* 🌍 Web deployment
* 📱 Mobile improvements
* 🧠 Smarter memory system
* ⚡ Faster response optimization

---

## 👨‍💻 Author

**Hari Hara Sudhan**

---

## ⭐ Support

If you like this project:

👉 Star the repo
👉 Share it
👉 Contribute

---

## 📜 License

Add a license (MIT recommended) before public distribution.
