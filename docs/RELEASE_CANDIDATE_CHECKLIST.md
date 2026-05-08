# Release Candidate Checklist

Use this checklist before tagging or sharing a GrandpaAssistant backend release candidate.

## Required Validation

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\dev\generate_debug_docs.py
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

## Protected Local APIs

Verify these routes exist and remain protected for localhost or authenticated admin use:

```text
GET /api/backend/stability
GET /api/screen/summary
GET /api/window/context
GET /api/context/suggestions
POST /api/context/execute-suggestion
GET /api/debug/dashboard
GET /api/debug/docs-summary
```

Remote unauthenticated requests should be blocked or restricted according to each route's safety contract.

## Debug Assistant Docs

Regenerate and review the debug assistant guide before tagging:

```text
docs/DEBUG_ASSISTANT_GUIDE.md
```

The guide should describe debug reports, fix plans, approvals, audit logs, sessions, exports, timelines, search/reuse, learning summaries, preflight checks, the debug dashboard, and safety constraints.

## Security

- Confirm `.gitignore` covers auth secrets, tokens, credential files, local databases, logs, and runtime validation state.
- Confirm these private/runtime paths are ignored and not tracked:
  - `backend/data/audit/*.jsonl`
  - `backend/data/debug/*.jsonl`
  - `backend/data/debug/exports/`
  - `backend/data/knowledge/review_queue.jsonl`
  - `backend/data/app_auth_secret.txt`
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
