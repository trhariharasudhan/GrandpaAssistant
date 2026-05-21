# GrandpaAssistant — Canonical Folder Structure

Backend-only active project. Use this map when adding code or cleaning duplicates.

## Top level

```text
GrandpaAssistant/
├── backend/           # All runtime Python code
├── docs/              # Architecture, roadmaps, release notes
├── plugins/           # Optional local plugins
├── scripts/           # dev/ diagnostics, windows/ launchers
├── tests/             # unittest suite
├── runtime/           # Local logs, DBs, cache (gitignored)
├── main.py            # Thin launcher → backend/main.py
└── README.md
```

## Backend (`backend/`)

```text
backend/
├── desktop_backend_entry.py   # PRIMARY entry — starts web_api + uvicorn
├── fastapi_chat.py            # Alternate chat-only entry
├── main.py
├── requirements.txt
├── app/
│   ├── api/                   # FastAPI apps
│   │   ├── web_api.py         # PRIMARY desktop API (91 routes)
│   │   └── chat_api.py        # Alternate / legacy-compatible API
│   ├── core/                  # Assistant brain, routing, chat
│   │   ├── assistant.py       # Desktop assistant loop
│   │   ├── chat_service.py    # Shared chat reply builder
│   │   ├── command_router.py  # Large command dispatcher
│   │   ├── commands/          # Extracted read-only handlers
│   │   ├── personal_assistant/  # Intent → plan → tools
│   │   ├── chatbot/           # Terminal CLI engine + providers
│   │   ├── llm/               # Unified provider layer
│   │   └── prompts/           # Shared prompt building
│   ├── features/              # Domain implementations (PUT NEW CODE HERE)
│   │   ├── productivity/
│   │   ├── system/
│   │   ├── automation/
│   │   ├── intelligence/
│   │   ├── voice/
│   │   ├── vision/
│   │   ├── ui_analysis/
│   │   ├── integrations/
│   │   ├── security/          # Feature-level security helpers
│   │   └── modules/           # ⚠️ COMPAT SHIMS ONLY — no new logic
│   ├── shared/                # Cross-cutting libraries
│   │   ├── brain/             # ✅ CANONICAL memory / semantic / ai_engine
│   │   ├── cognition/
│   │   └── utils/
│   ├── security/              # ✅ CANONICAL auth, permissions, threat
│   ├── services/              # local_action_executor (+ thin __init__)
│   ├── project_knowledge/     # Local lexical RAG
│   ├── integrations/          # n8n_client, etc.
│   ├── agents/                # Agent runtime (partial use)
│   └── prompts/               # File-backed prompt text assets
├── assets/
└── data/                      # Local secrets/DB (mostly gitignored)
```

## Import paths (important)

Runtime adds these to `sys.path` (see `desktop_backend_entry.py`):

| Path on disk | Import style |
| --- | --- |
| `backend/app/shared/` | `from brain.semantic_memory import ...` → **`shared/brain/`** |
| `backend/app/features/` | Feature modules |
| `backend/app/` | `from app.api import web_api` |

### Do not recreate

| Wrong location | Why |
| --- | --- |
| `backend/app/brain/` | Removed — was pycache-only and shadowed `shared/brain/` |
| `backend/app/core/security/` | Removed — pycache orphan; use `app/security/` |
| `backend/app/core/knowledge_engine/` | Removed — pycache orphan |
| `backend/app/core/math_engine/` | Removed — pycache orphan |

## Where to add new features

| Type | Location |
| --- | --- |
| New capability (tasks, browser, IoT) | `backend/app/features/<domain>/` |
| New slash/command | `command_router.py` or `core/commands/handlers/` |
| New HTTP route (desktop) | `api/web_api.py` first |
| New tool for PA | `core/personal_assistant/tool_registry.py` |
| New LLM provider | `core/llm/providers/` + registry |
| Tests | `tests/test_<area>.py` |

## Duplicate areas (intentional for now)

| Duplicate | Owner | Future |
| --- | --- | --- |
| `web_api` vs `chat_api` | **web_api** = desktop primary | Consolidate after contract tests |
| Terminal providers vs `llm_client` | Both active | Terminal → unified `core/llm` only |
| Memory stores (3+ SQLite/JSON) | Documented per store | Phase E migration |
| `features/modules/*.py` | Shim re-exports | Remove when imports migrated |

## Maintenance scripts

```bat
python scripts\dev\repo_structure_audit.py
python scripts\dev\cleanup_orphan_artifacts.py --dry-run
python scripts\dev\inventory_backend.py
```

See also: `docs/COMPLETION_ROADMAP.md`, `docs/CLEANUP_PLAN.md`, `docs/inventory/DUPLICATION_RISKS.md`.
