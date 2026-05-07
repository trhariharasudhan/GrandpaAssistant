# API Router Split Plan

`backend/app/api/web_api.py` should keep its current behavior until route-level tests cover each group. The safe split target is:

- `auth_routes.py`: app auth bootstrap, login/logout/register, profile, users, audit log
- `chat_routes.py`: sessions, chat replies, streaming, upload/remove/export
- `command_routes.py`: `/api/command` and confirmation handling
- `companion_routes.py`: companion status, pairing, token auth, companion chat/voice/WebSocket
- `voice_routes.py`: voice status/start/stop and TTS/STT helpers
- `diagnostics_routes.py`: health, doctor, startup settings, hardware summaries
- `productivity_routes.py`: dashboard state, proactive refresh, planner/productivity endpoints

Migration rules:

1. Move one route group at a time.
2. Keep endpoint paths, request/response payloads, and status codes unchanged.
3. Move shared state only after all route groups that use it have tests.
4. Prefer dependency helpers for auth, current session, and assistant runtime state.
5. Run full backend validation after each group.
