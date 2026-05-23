# Status Endpoint Ownership

Phase 9 backend-only ownership freeze for provider, model, health, and status routes. No routes were moved, deleted, or disabled.

## Ownership Rules

- `backend/app/api/web_api.py` remains the active desktop backend API owner.
- `backend/app/api/chat_api.py` remains the alternate chat/runtime API owner.
- Shared provider/model health data should come from `backend/app/core/llm/status.py` through compatibility wrappers.
- Route movement is deferred until API contracts and client usage are explicit.

## Status Route Inventory

| Route | Method | Module | Current Runtime | Owner Decision | Response Shape | Risk | Future Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/api/health` | GET | `web_api.py` | Active desktop API | WEB_API_PRIMARY | `ok`, `service`, `runtime`, `semantic_memory`, `doctor` | Low | Keep as active desktop readiness endpoint. |
| `/api/doctor` | GET | `web_api.py` | Active desktop API | WEB_API_PRIMARY | `ok`, `doctor` | Low | Keep; may later share diagnostic helper only. |
| `/api/backend/stability` | GET | `web_api.py` | Active desktop API | WEB_API_PRIMARY | backend stability payload | Low | Keep as active desktop/admin diagnostic route. |
| `/api/phone-link/status` | GET | `web_api.py` | Active desktop API | WEB_API_PRIMARY | Phone Link readiness payload | Low | Keep until phone/desktop integration ownership is split. |
| `/api/auth/bootstrap-status` | GET | `web_api.py` | Active desktop API | WEB_API_PRIMARY | `ok`, auth bootstrap fields | Low | Keep in web API until auth router extraction. |
| `/api/auth/status` | GET | `web_api.py` | Active desktop API | WEB_API_PRIMARY | `ok`, `auth`, `current` | Low | Keep in web API until auth router extraction. |
| `/api/memory/status` | GET | `web_api.py` | Active desktop API | WEB_API_PRIMARY | `ok`, `memory` | Low | Keep as active desktop memory status route. |
| `/api/personal-assistant/status` | GET | `web_api.py` | Active desktop API | WEB_API_PRIMARY | safe read-only personal assistant metadata | Low | Keep as localhost/admin diagnostics; no memory values, transcripts, screenshots, or LLM calls. |
| `/api/voice/status` | GET | `web_api.py` | Active desktop API | WEB_API_PRIMARY | `ok`, `voice` | Low | Keep as active desktop voice status route. |
| `/api/settings/startup` | GET | `web_api.py` | Active desktop API | WEB_API_PRIMARY | `ok`, `startup` | Low | Keep; later move to settings router if routers are introduced. |
| `/api/mobile/status` | GET | `web_api.py` | Active desktop API compatibility | DEPRECATED_COMPAT_KEEP | `ok`, `mobile` | Medium | Keep compatibility route; no active mobile workspace is restored. |
| `/mobile/status` | GET | `web_api.py` | Active desktop API compatibility | DEPRECATED_COMPAT_KEEP | `ok`, `device`, `mobile`, `status` | Medium | Keep until mobile companion backend contract is formally deprecated or retained. |
| `/chat/settings` | GET | `web_api.py` | Active desktop API | WEB_API_PRIMARY | `ok`, `settings`, nested `llm_status` | Medium | Keep desktop chat settings owner; provider status stays behind `llm_client.get_llm_status()`. |
| `/chat/settings` | POST | `web_api.py` | Active desktop API | WEB_API_PRIMARY | `ok`, `settings`, nested `llm_status` | Medium | Keep desktop chat settings owner; no schema change. |
| `/health` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, `service`, `offline_assistant`, hardware/runtime/doctor fields | Low | Keep as alternate runtime readiness endpoint. |
| `/doctor` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, `doctor` | Low | Keep; diagnostic helper can remain shared. |
| `/models` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, `models` or 503 detail | Medium | Keep alternate Ollama model list route; status source remains unified. |
| `/settings/validation` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, `validation` | Low | Keep until settings router extraction. |
| `/voice/piper/status` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, `piper`, `message` | Low | Keep alternate voice setup status route. |
| `/voice/custom/status` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, `custom_voice`, `message` | Low | Keep alternate voice setup status route. |
| `/iot/status` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, `iot` | Low | Keep alternate IoT status route. |
| `/iot/validate` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, `validation` | Low | Keep alternate IoT validation route. |
| `/iot/mock/status` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, `updated_at`, `devices` | Low | Keep as alternate IoT mock status route. |
| `/status` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, `assistant` | Medium | Keep alternate aggregate status endpoint; do not merge with `/api/health` yet. |
| `/security/status` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, `security` | Low | Keep until security router extraction. |
| `/intelligence/status` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, intelligence payload | Low | Keep alternate cognition status route. |
| `/learning/status` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, learning payload | Low | Keep alternate learning status route. |
| `/sync/status` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | sync status payload | Low | Keep alternate sync status route. |
| `/memory/status` | GET | `chat_api.py` | Alternate chat runtime | CHAT_API_ALT_RUNTIME | `ok`, `memory` | Low | Keep alternate memory status route. |
| `core.llm.status` | N/A | shared helper | Shared backend library | SHARED_STATUS_HELPER | provider/model health dictionaries | Low | Keep as canonical provider/model status source. |

## Decisions

- Active desktop health/status ownership stays with `web_api.py`.
- Alternate runtime health/status ownership stays with `chat_api.py`.
- Provider/model reporting is helper-owned by `core.llm.status`, surfaced through existing wrappers.
- No status route currently needs to move to reduce active desktop duplicate risk.

## Known Risks

- `/chat/settings` in `web_api.py` is the only active desktop route exposing provider/model settings today; it should not be silently replaced by `chat_api.py /models`.
- `chat_api.py /health`, `/status`, and `/models` are valid alternate runtime routes, not active desktop route conflicts.
- Mobile companion status routes in `web_api.py` are compatibility backend routes. They should not be confused with restoring a mobile app workspace.
