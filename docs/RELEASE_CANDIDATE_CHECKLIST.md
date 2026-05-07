# Release Candidate Checklist

Use this checklist before tagging or sharing a GrandpaAssistant backend release candidate.

## Required Validation

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\dev\full_backend_validation.py
.\.venv\Scripts\python.exe scripts\dev\startup_smoke_check.py
Get-ChildItem backend -Recurse -Filter *.py | ForEach-Object { .\.venv\Scripts\python.exe -m py_compile $_.FullName }
```

All required checks must pass. Optional hardware and local AI readiness can be warnings if the backend still starts and the affected feature fails gracefully.

## Stability Dashboard

Check the release lock from the assistant:

```text
backend health summary
release lock status
```

Check the JSON endpoint locally:

```text
GET /api/backend/stability
```

The endpoint returns full detail for localhost or authenticated admin requests. Remote unauthenticated requests receive a trimmed restricted payload.

## Security

- Confirm `.gitignore` covers auth secrets, tokens, credential files, local databases, logs, and runtime validation state.
- Do not include real files from `runtime/` or local credential/config directories.
- Dangerous commands must require confirmation and, where appropriate, authentication/admin mode.
- CORS must remain localhost-safe.

## Runtime Smoke

- Backend remains runnable through `python backend\desktop_backend_entry.py`.
- `GET /api/health` responds after startup.
- Startup smoke can enter text mode and exit cleanly.
- Missing Ollama, microphone, camera, OCR, or optional model files do not crash startup.

## Before Tagging

- Review `git status --short` and confirm every changed file belongs to the release.
- Re-run full backend validation after the final code change.
- Read `runtime\data\last_backend_validation.json` if the release-lock command reports stale or failed validation.
- Record known warnings in release notes.
