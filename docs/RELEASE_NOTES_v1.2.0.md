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
- Windows controls audit added for app/window, browser/navigation, keyboard/mouse, system, communication, productivity, debug assistant, and voice/chat capabilities.
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
- Local Contact Manager added for private local contact storage and reliable `call <name>` routing.
- Phone Link/default `tel:` handler readiness checker added.
- Direct clear call intents such as `call mom`, `call 9876543210`, and `riyaa ku call pannu` start the call flow without an extra confirmation.
- Missing or ambiguous call targets ask for clarification, and emergency numbers remain blocked from automatic calling.
- Contact deletion, outgoing messages/emails, file changes, system power actions, installs, and non-read-only commands remain confirmation-protected.

## Protected API Surface Verified

- `GET /api/backend/stability`
- `GET /api/screen/summary`
- `GET /api/window/context`
- `GET /api/context/suggestions`
- `POST /api/context/execute-suggestion`
- `GET /api/debug/dashboard`
- `GET /api/debug/docs-summary`
- `GET /api/windows/controls/audit`
- `GET /api/contacts`
- `POST /api/contacts`
- `GET /api/contacts/search?q=...`
- `DELETE /api/contacts/{name}`
- `GET /api/phone-link/status`

These endpoints are designed for localhost or authenticated admin access. Remote unauthenticated access is blocked or restricted according to each route's safety contract.

## Runtime And Private Data

The release keeps runtime/private data ignored and untracked, including:

- `backend/data/audit/*.jsonl`
- `backend/data/debug/*.jsonl`
- `backend/data/debug/exports/`
- `backend/data/knowledge/review_queue.jsonl`
- `backend/data/contacts/*.json`
- `backend/data/app_auth_secret.txt`

## Documentation

- Runtime testing guide: `docs/RUNTIME_TESTING_GUIDE.md`
- Debug assistant guide: `docs/DEBUG_ASSISTANT_GUIDE.md`
- Windows controls audit guide: `docs/WINDOWS_CONTROL_AUDIT.md`
- Contacts and calling guide: `docs/CONTACTS_AND_CALLING.md`
- Release candidate checklist: `docs/RELEASE_CANDIDATE_CHECKLIST.md`

Regenerate debug assistant docs with:

```bat
.venv\Scripts\python.exe scripts\dev\generate_debug_docs.py
```

## Validation

Validated on May 9, 2026:

- Windows controls audit: PASS, `30/30` implemented, `0` warnings
- Runtime backend check: PASS, detected port `8765`
- Debug docs generation: PASS
- Unit tests: PASS
- Full backend validation: PASS
- Startup smoke check: PASS
- Backend py_compile: PASS, 167 backend Python files
- Contact APIs: localhost PASS, remote unauthenticated blocked with `403`
- Phone Link status API: localhost PASS, remote unauthenticated blocked with `403`

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
