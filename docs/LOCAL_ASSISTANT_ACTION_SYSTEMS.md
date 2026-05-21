# Local Assistant Action Systems

GrandpaAssistant now has backend foundations for four local-first action systems:

- Browser automation
- Chat application integrations
- Autonomous multi-step task planning
- Visual desktop understanding

These systems are modular and do not replace `command_router.py` or the existing `core.personal_assistant` flow.

## Browser Automation

Modules:

- `backend/app/browser_automation/session_manager.py`
- `backend/app/browser_automation/planner.py`
- `backend/app/browser_automation/executor.py`
- `backend/app/browser_automation/safety.py`
- `backend/app/browser_automation/memory.py`
- `backend/app/browser_automation/service.py`
- `backend/app/api/browser_automation_api.py`

Capabilities:

- Playwright-compatible persistent sessions.
- Chrome, Edge, Firefox, and Chromium support.
- DOM actions for navigation, click, fill, form fill, read, screenshot, upload, and download.
- Retry-aware execution and safe metadata memory.
- REST and server-sent event surfaces.

Safety:

- Buying, ordering, booking, applying, sending, posting, deleting, and sensitive fields require confirmation.
- Captcha bypass, credential theft, private scraping, and robots bypass requests are blocked.

## Chat Integrations

Modules:

- `backend/app/chat_integrations/manager.py`
- `backend/app/chat_integrations/storage.py`
- `backend/app/chat_integrations/notifications.py`
- `backend/app/chat_integrations/smart_reply.py`
- `backend/app/api/chat_integrations_api.py`

Supported targets:

- WhatsApp Web
- Telegram
- Discord
- Slack

Capabilities:

- Parse notification text into safe message records.
- Read locally remembered messages.
- Search local contacts.
- Suggest smart replies.
- Summarize unread messages.
- Draft send/media/voice-message requests.
- Mute thread metadata locally.

Safety:

- Message approval mode is enabled by default.
- Real platform adapters are reported as missing until connected.
- Local message memory is encrypted at rest with a local key.
- Tests do not use real accounts, networks, or notification listeners.

## Autonomous Agent

Modules:

- `backend/app/autonomous_agent/planner.py`
- `backend/app/autonomous_agent/executor.py`
- `backend/app/autonomous_agent/state.py`
- `backend/app/autonomous_agent/manager.py`
- `backend/app/api/autonomous_agent_api.py`

Capabilities:

- Goal decomposition.
- Task graph construction.
- Tool selection.
- Persistent task state.
- Action history.
- Streaming progress events.
- Human-in-the-loop checkpoints.

Examples:

- `I am hungry` becomes preference question, food site step, confirmation checkpoint.
- `Book a cab home` becomes pickup/drop question, cab site step, confirmation checkpoint.
- `Send today's report to manager` becomes draft, approval checkpoint, message-send step.

Safety:

- The agent does not execute high-risk final actions without approval.
- Unsupported tools pause safely.
- Failure recovery returns safe next-step guidance.

## Visual Desktop

Modules:

- `backend/app/visual_desktop/capture.py`
- `backend/app/visual_desktop/ocr.py`
- `backend/app/visual_desktop/ui_detector.py`
- `backend/app/visual_desktop/reasoning.py`
- `backend/app/visual_desktop/action_planner.py`
- `backend/app/visual_desktop/safe_executor.py`
- `backend/app/visual_desktop/service.py`
- `backend/app/api/visual_desktop_api.py`

Capabilities:

- Explicit screen analysis.
- OCR summary extraction when adapters are available.
- UI element heuristic detection.
- Button recognition from OCR text.
- Visual action planning.
- Safe action execution envelope.

Safety:

- No hidden background screenshots.
- API responses do not include screenshot image bodies by default.
- Low-confidence clicks require confirmation.
- Dangerous visual actions are blocked.
- Real UI clicking remains adapter-driven and approval-gated.

## API Prefixes

- `/api/browser`
- `/api/chat-integrations`
- `/api/agent`
- `/api/visual-desktop`

## Validation

Focused tests:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_chat_integrations tests.test_autonomous_agent_system tests.test_visual_desktop_system tests.test_browser_automation_engine -v
```

Full validation:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m backend.app.cli.chat --smoke "hi da"
.venv\Scripts\python.exe scripts\dev\startup_smoke_check.py
```

## Limitations

- Real WhatsApp, Telegram, Discord, and Slack adapters are not connected yet.
- The autonomous planner is deterministic and validation-first; future LLM planning must remain registry-limited and approval-gated.
- Visual desktop understanding uses OCR/UI heuristics unless optional computer vision adapters are available.
- Browser automation requires Playwright and local browser runtimes for real browser control.

