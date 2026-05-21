# Browser Automation Engine

GrandpaAssistant now has a modular browser automation foundation built around Playwright-compatible services. The engine is local-first, Windows-friendly, and designed to sit beside the existing assistant architecture without changing `command_router.py`.

## Architecture

- `backend/app/browser_automation/config.py` defines supported browsers, risk keywords, runtime paths, and execution limits.
- `backend/app/browser_automation/session_manager.py` owns persistent browser sessions for Chrome, Edge, Firefox, and Chromium.
- `backend/app/browser_automation/planner.py` creates deterministic browser action plans for common web tasks.
- `backend/app/browser_automation/safety.py` classifies plans and enforces confirmation/blocking rules.
- `backend/app/browser_automation/executor.py` executes safe plans through Playwright pages with retries, DOM actions, screenshots, uploads, downloads, and structured page reads.
- `backend/app/browser_automation/memory.py` stores local metadata about sessions and recent browser tasks without page dumps.
- `backend/app/browser_automation/service.py` provides the internal plan, execute, stream, and status interface.
- `backend/app/api/browser_automation_api.py` exposes REST/SSE endpoints for local backend callers.

## API Surface

- `GET /api/browser/status`
- `POST /api/browser/plan`
- `POST /api/browser/execute`
- `POST /api/browser/stream`
- `POST /api/browser/sessions/{session_id}/close`

The streaming endpoint emits server-sent events with planning, safety, step, and completion updates.

## Safety Model

The engine never finalizes sensitive web actions silently. Requests involving booking, ordering, buying, payment, login-like sensitive fields, application submission, posting, sending, deletion, or cancellation require confirmation. Requests that attempt to bypass captchas, steal data, scrape private data, or ignore robots controls are blocked.

Browser context memory stores safe operational metadata only: session ids, browsers, urls, page titles, and recent task names. It does not store passwords, cookies, page bodies, screenshots, or private form values.

## Playwright Setup

The service fails gracefully if Playwright is not installed. Real browser control requires Playwright and browser runtimes to be installed in the local environment. Tests use fake pages and do not launch real browsers.

## Supported Foundations

- Multi-browser persistent sessions.
- Intelligent deterministic planning for YouTube/music, LinkedIn/jobs, cab booking, food ordering, URL opening, and search.
- DOM actions: goto, click, fill, fill form, read, screenshot, upload, download.
- Structured data extraction with capped text previews.
- Retry-aware execution with safe logging.
- Human-like navigation delay configuration.
- REST and streaming update surfaces.

## Current Limitations

- The planner is deterministic with extension points for future AI planning; it does not yet perform unrestricted autonomous web reasoning.
- Visual understanding is represented by screenshot capture/debug hooks, but a full visual planner is not wired yet.
- Dangerous tasks such as booking cabs, ordering food, applying for jobs, or logging in stop at confirmation boundaries.
- Advanced upload/download workflows may need task-specific plan steps.
- No frontend UI was added for this engine.

## Validation

Run:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_browser_automation_engine -v
.venv\Scripts\python.exe -m unittest discover -s tests -v
```
