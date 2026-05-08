# GrandpaAssistant v1.2.0 Release Notes

## Release Status

Final v1.2.0 backend release.

## Summary

GrandpaAssistant v1.2.0 is a Windows-first backend-only release focused on runtime stability, safe local assistant behavior, offline knowledge, context awareness, and a full guided debug assistant system.

The backend remains runnable through:

```bat
.venv\Scripts\python.exe backend\desktop_backend_entry.py
```

For a clear runtime PASS/FAIL check, use:

```bat
scripts\dev\runtime_backend_check.cmd
```

## Highlights

- Backend-only project shape stabilized.
- Frontend and mobile workspaces remain outside the active tracked release.
- Runtime backend check helper added for clear startup and endpoint verification.
- Smart Offline Knowledge Pack added for common local facts, Tamil/English-friendly responses, time/date answers, basic science/math facts, and sample Thirukkural lookup.
- Knowledge review queue added for safe local misses that can be reviewed later.
- Screen awareness and voice explanation mode added with protected local/admin API access.
- App/window context awareness added with safe active-window summaries.
- Context-aware action suggestions added without automatic execution.
- Safe context action executor added for read/explain/summarize actions only.
- Guided debug assistant added for error reports, likely causes, safe steps, and no-command-executed guarantees.
- Safe fix plan generator added for suggestion-only commands and file checks.
- Fix approval flow added with unique approval IDs and explicit `allow <id>` before safe read-only execution.
- Fix execution audit log added for local review.
- Debug session memory, export, timeline, search, knowledge reuse, learning summary, preflight checklist, health dashboard, and docs generator added.

## Protected API Surface Verified

- `GET /api/backend/stability`
- `GET /api/screen/summary`
- `GET /api/window/context`
- `GET /api/context/suggestions`
- `POST /api/context/execute-suggestion`
- `GET /api/debug/dashboard`
- `GET /api/debug/docs-summary`

These endpoints are designed for localhost or authenticated admin access. Remote unauthenticated access is blocked or restricted according to each route's safety contract.

## Runtime And Private Data

The release keeps runtime/private data ignored and untracked, including:

- `backend/data/audit/*.jsonl`
- `backend/data/debug/*.jsonl`
- `backend/data/debug/exports/`
- `backend/data/knowledge/review_queue.jsonl`
- `backend/data/app_auth_secret.txt`

## Documentation

- Runtime testing guide: `docs/RUNTIME_TESTING_GUIDE.md`
- Debug assistant guide: `docs/DEBUG_ASSISTANT_GUIDE.md`
- Release candidate checklist: `docs/RELEASE_CANDIDATE_CHECKLIST.md`

Regenerate debug assistant docs with:

```bat
.venv\Scripts\python.exe scripts\dev\generate_debug_docs.py
```

## Validation

Validated on May 8, 2026:

- Runtime backend check: PASS, detected port `8765`
- Debug docs generation: PASS
- Unit tests: PASS
- Full backend validation: PASS
- Startup smoke check: PASS
- Backend py_compile: PASS, 163 backend Python files

Runtime endpoint checks passed:

- `/api/health`: PASS, `200`
- `/api/backend/stability`: PASS, `200`
- `/api/debug/dashboard`: PASS, `200`
- `/api/debug/docs-summary`: PASS, `200`

## Known Warnings

- Ollama is not responding at `http://localhost:11434/api/tags`.
- Required Ollama model checks are skipped when the Ollama API is unavailable.
- Custom settings paths are preserved by startup diagnostics.

These are optional dependency/readiness warnings and do not block the v1.2.0 release.

## Suggested Tag

`v1.2.0`
