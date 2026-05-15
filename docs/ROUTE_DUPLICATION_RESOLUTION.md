# Route Duplication Resolution

Phase 1 backend routing cleanup audit. No route handlers were moved, deleted, or disabled.

## Runtime Finding

The active desktop backend run command is:

```text
python backend\desktop_backend_entry.py
```

That entrypoint imports and runs `backend/app/api/web_api.py` as `web_api.app`.

`backend/app/api/chat_api.py` is a separate FastAPI app imported by `backend/fastapi_chat.py`. Its duplicate routes are registered on `chat_api.app`, not on the active desktop `web_api.app`.

## Duplicate Route Decisions

| Route | File A | File B | Active Owner | Risk | Action Taken | Future Action |
| --- | --- | --- | --- | --- | --- | --- |
| `POST /api/automation/n8n/test` | `backend/app/api/web_api.py:2490` `api_n8n_test` | `backend/app/api/chat_api.py:813` `n8n_test` | `web_api.py` | Low active-runtime conflict risk because the handlers live on separate FastAPI app objects. Medium maintenance risk because behavior can drift. | Documentation and regression tests only. | Keep active desktop owner in `web_api.py`; decide later whether alternate chat API should expose this path. |
| `POST /chat` | `backend/app/api/web_api.py:3217` `chat_reply` | `backend/app/api/chat_api.py:1794` `chat` | `web_api.py` | Low active-runtime conflict risk. Medium behavior drift risk because both implement chat behavior separately. | Documentation and regression tests only. | Keep current behavior. Move/consolidate later only after chat API contract is written. |
| `GET /chat/history` | `backend/app/api/web_api.py:3112` `chat_history` | `backend/app/api/chat_api.py:1782` `get_chat_history` | `web_api.py` | Low active-runtime conflict risk. Medium schema/session drift risk. | Documentation and regression tests only. | Compare response schema and session model before any consolidation. |
| `POST /chat/reset` | `backend/app/api/web_api.py:3199` `chat_reset` | `backend/app/api/chat_api.py:1787` `reset_chat` | `web_api.py` | Low active-runtime conflict risk. Medium state-management drift risk. | Documentation and regression tests only. | Compare reset semantics before choosing a single owner. |
| `POST /chat/stream` | `backend/app/api/web_api.py:3383` `chat_stream` | `backend/app/api/chat_api.py:1920` `chat_stream` | `web_api.py` | Low active-runtime conflict risk. Medium stream format drift risk. | Documentation and regression tests only. | Keep active web stream behavior; later align event format if chat API becomes owner. |

## Decision

No duplicate route was disabled in Phase 1.

Reason: all five duplicate route declarations are split across two separate FastAPI app objects. The active desktop runtime registers the `web_api.py` handlers. Removing or disabling the `chat_api.py` declarations would be a compatibility change for the alternate chat API and is not needed to reduce active desktop runtime conflict risk.

## Phase 9 Status Endpoint Note

Provider/status/health routes were reviewed separately in `docs/STATUS_ENDPOINT_OWNERSHIP.md`.

No new active desktop duplicate conflict was introduced:

- `web_api.py` keeps active desktop status routes under `/api/*` and desktop chat settings under `/chat/settings`.
- `chat_api.py` keeps alternate runtime status routes such as `/health`, `/status`, and `/models`.
- Provider/model reporting is shared through `core.llm.status` wrappers rather than by moving route handlers.

## Regression Coverage Added

The regression test verifies:

- `desktop_backend_entry.py` uses `web_api.app` as the active runtime app.
- `web_api.app` has no exact duplicate method/path registrations for the active route table.
- Each duplicate source route is owned by the expected `web_api.py` endpoint on the active app.
- The duplicate declarations remain isolated on `chat_api.app`.
