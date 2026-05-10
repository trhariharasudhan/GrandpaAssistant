# GrandpaAssistant Terminal Chatbot

This is a terminal-only chatbot system. It does not use frontend, mobile, React, Electron, browser pages, HTML, CSS, or web dashboards.

## Install

From the repository root:

```powershell
pip install -r requirements.txt
```

## Run

```powershell
python -m backend.app.cli.chat
```

You will see:

```text
GrandpaAssistant Terminal Chat
Provider: fallback
Type /help for commands

You:
```

## Commands

```text
/exit or /quit       Stop chat
/clear               Clear current session messages and screen
/history             Show recent conversation
/reset               Start a new session
/help                Show commands
/provider            Show current AI provider
/model               Show current model
/memory              Show saved memory facts
/save <fact>         Save a memory fact
/forget <keyword>    Forget matching memory facts
/config              Show config without secrets
```

## Provider Setup

Config file:

```text
backend/app/config/terminal_chat.json
```

Environment variables:

```powershell
$env:AI_PROVIDER="fallback"   # openai, gemini, ollama, fallback
$env:AI_MODEL="gpt-4.1-mini"
$env:OPENAI_API_KEY="..."
$env:GEMINI_API_KEY="..."
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:GRANDPA_DB_PATH="runtime/data/grandpa_chat.db"
$env:GRANDPA_LOG_LEVEL="INFO"
```

Switch provider:

```powershell
$env:AI_PROVIDER="ollama"
$env:AI_MODEL="llama3:8b"
python -m backend.app.cli.chat
```

For OpenAI:

```powershell
$env:AI_PROVIDER="openai"
$env:AI_MODEL="gpt-4.1-mini"
$env:OPENAI_API_KEY="your_key_here"
python -m backend.app.cli.chat
```

For Gemini:

```powershell
$env:AI_PROVIDER="gemini"
$env:AI_MODEL="gemini-1.5-flash"
$env:GEMINI_API_KEY="your_key_here"
python -m backend.app.cli.chat
```

## Memory

SQLite database:

```text
runtime/data/grandpa_chat.db
```

Tables:

- `chat_sessions`
- `chat_messages`
- `user_memories`
- `app_events`

The bot stores user messages, assistant replies, timestamps, session id, provider, model, and a simple token estimate. It saves long-term facts only when you use `/save`.

Secrets are not saved as memories when they look like API keys, tokens, passwords, or credentials.

## Logs

Terminal-friendly logs:

```text
runtime/logs/grandpa.log
```

Logs include startup config without secret values, provider errors, and chat events.

## Smoke Test

```powershell
python scripts/smoke_test_terminal_chat.py
```

Expected checks:

- imports work
- DB initializes
- fallback provider replies
- chat memory insert/read works
- config loads
- intent router handles greeting/time/math

## Sample Chat

```text
GrandpaAssistant Terminal Chat
Provider: fallback
Type /help for commands

You: hi da
Grandpa: Hi da! Enna help venum?

You: /save my name is Hari
Grandpa: Saved da.

You: /memory
Grandpa: Saved memories:
1. my name is Hari

You: what is 10+25
Grandpa: 35
```
