# Runtime Testing Guide

Use this guide when you want a clear PASS/FAIL answer for whether the GrandpaAssistant backend runtime actually started.

## One-Command Runtime Check

From the repository root, run:

```bat
scripts\dev\runtime_backend_check.cmd
```

The helper starts `backend\desktop_backend_entry.py`, waits up to 45 seconds, checks common backend ports, prints endpoint PASS/FAIL results, and stops the backend process before exiting.

It checks port `8765` first and also checks `8000`. If port `8765` fails, review the report for `8000`.

## Manual Backend Start

If you want to start the backend manually:

```bat
.venv\Scripts\python.exe backend\desktop_backend_entry.py
```

The backend may start quietly because uvicorn logging is intentionally set to warning level by default. Silent startup is okay if the health URL responds.

## Stop The Backend

Press:

```text
Ctrl + C
```

## URLs To Test

Open these locally after starting the backend:

```text
http://127.0.0.1:8765/api/health
http://127.0.0.1:8765/api/backend/stability
http://127.0.0.1:8765/api/debug/dashboard
http://127.0.0.1:8765/api/debug/docs-summary
```

If port `8765` does not respond, check the same paths on port `8000`:

```text
http://127.0.0.1:8000/api/health
```

## Expected Result

The runtime helper should print:

- backend process started: `YES`
- detected port, usually `8765`
- each endpoint with `PASS`
- HTTP status codes
- short response previews
- `overall: PASS`

If startup fails, the helper prints backend stdout/stderr previews to make silent startup failures easier to diagnose.
