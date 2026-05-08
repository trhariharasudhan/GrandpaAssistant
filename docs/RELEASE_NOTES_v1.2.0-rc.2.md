# GrandpaAssistant v1.2.0-rc.2 Release Notes

## Release Status

Release Candidate 2

## Highlights

- Backend-only stabilization remains the active project shape.
- Backend runtime remains runnable through `python backend\desktop_backend_entry.py`.
- Frontend and mobile workspaces remain untracked and outside the active release.
- Smart Offline Knowledge Pack answers simple local facts without requiring Wikipedia or Ollama for every common question.
- Knowledge review queue records safe local misses for later admin review.
- Screen awareness, window awareness, context suggestions, and safe context action execution are available through protected local/admin APIs.
- Guided debug assistant system now covers reports, fix plans, approvals, audit logs, debug sessions, exports, timeline, search, reuse, learning summaries, preflight checklist, and the debug health dashboard.
- Debug docs generator added at `scripts\dev\generate_debug_docs.py`.
- Generated debug guide available at `docs\DEBUG_ASSISTANT_GUIDE.md`.

## Protected API Surface Verified

- `GET /api/backend/stability`
- `GET /api/screen/summary`
- `GET /api/window/context`
- `GET /api/context/suggestions`
- `POST /api/context/execute-suggestion`
- `GET /api/debug/dashboard`
- `GET /api/debug/docs-summary`

These routes are designed for localhost or authenticated admin access. Remote unauthenticated access is blocked or restricted according to each route's safety contract.

## Runtime And Private Data

The release keeps runtime/private data out of git, including:

- `backend/data/audit/*.jsonl`
- `backend/data/debug/*.jsonl`
- `backend/data/debug/exports/`
- `backend/data/knowledge/review_queue.jsonl`
- `backend/data/app_auth_secret.txt`

## Validation

Validated on May 8, 2026:

- Debug docs generation: PASS
- Unit tests: PASS
- Full backend validation: PASS
- Startup smoke check: PASS
- Backend py_compile: PASS, 163 backend Python files

## Known Warnings

- Ollama is not responding at `http://localhost:11434/api/tags`.
- Required Ollama model checks are skipped when the Ollama API is unavailable.
- Custom settings paths are preserved by startup diagnostics.

These are optional dependency/readiness warnings and do not block the backend release lock.

## Suggested Tag

`v1.2.0-rc.2`
