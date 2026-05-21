# GrandpaAssistant — 100% Completion Roadmap

This plan turns **partial** and **not built** features into production-ready behavior without breaking the active runtime.

**Active runtime (do not break):**

```bat
python backend\desktop_backend_entry.py
```

**Validation after every phase:**

```bat
python -m unittest discover -s tests -v
python scripts\dev\startup_smoke_check.py
python scripts\dev\repo_structure_audit.py
```

---

## Reality check

| Bucket | Item count (approx.) | Effort |
| --- | --- | --- |
| Partial foundations | ~25 areas | Weeks–months |
| Not built (real-world / messaging / mobile / IoT hardware) | ~30 areas | Months; some need external APIs |
| Structural cleanup | Ongoing | Days (safe passes already started) |

**Rule:** One phase at a time. No big-bang merge of `web_api.py` + `chat_api.py` or all memory stores in a single PR.

---

## Phase A — Structure and duplicates (START HERE)

**Goal:** Clean tree, no shadow packages, documented ownership.

| Task | Status | Notes |
| --- | --- | --- |
| Remove `backend/app/brain/` pycache-only tree | Done | Shadows `shared/brain/` |
| Remove `core/knowledge_engine`, `math_engine`, `security` pycache orphans | Done | Real security: `app/security/` |
| `scripts/dev/repo_structure_audit.py` | Done | Run before/after cleanup |
| `scripts/dev/cleanup_orphan_artifacts.py` | Done | Safe delete helper |
| `docs/FOLDER_STRUCTURE.md` | Done | Canonical layout |
| Route ownership (`docs/STATUS_ENDPOINT_OWNERSHIP.md`) | Done | Do not merge APIs yet |
| `features/modules/` shims | Keep | 28 aliases; migrate imports later |

**Do not delete yet:** `web_api.py`, `chat_api.py`, terminal providers, `features/modules/` (compatibility).

---

## Phase B — Wire partial brains into main chat (2–3 weeks)

**Goal:** Partial features become **default-on** for desktop chat, not side paths.

| # | Feature | Status | Work |
| --- | --- | --- | --- |
| B1 | Unified chat memory hook | **Done** | `core/chat_context.py` → semantic memory in `chat_service` |
| B2 | Runtime prompts default | **Done** | `GRANDPA_CHAT_ENHANCED=1` (default) enables runtime prompts |
| B3 | Project context | **Done** | Auto for coding prompts when enhanced; explicit `GRANDPA_USE_PROJECT_CONTEXT` |
| B4 | Multi-model routing | **Done** | `resolve_chat_llm_model()` + `default_chat_provider` for Ollama |
| B5 | Planning prompt mode | **Done** | `plan my day`, agendas → `planning` mode when `GRANDPA_CHAT_PLANNING_MODE` on (default with enhanced) |

**Exit:** Same reply quality as today + memory/context visible in debug metadata; tests for `chat_service` paths.

**Env flags:** see `.env.example` (`GRANDPA_CHAT_ENHANCED`, `GRANDPA_CHAT_SEMANTIC_MEMORY`, `GRANDPA_CHAT_OLLAMA_ROUTING`).

---

## Phase C — Voice and vision to “daily usable” (3–4 weeks)

| # | Feature | Status | Work |
| --- | --- | --- | --- |
| C1 | Voice readiness matrix | **Done** | `shared/voice_readiness.py`, `GET /api/voice/readiness`, `scripts/dev/voice_readiness_check.py` |
| C2 | Wake word + continuous listen | Harden `voice_runtime.py`; env defaults for desktop |
| C3 | Real-time voice chat | Unify mobile voice endpoints with desktop session id |
| C4 | OCR path | Tesseract check in startup diagnostics; clear user message if missing |
| C5 | UI execute API | Optional `POST /api/ui/execute` behind confirmation token (mirror command_router) |
| C6 | Browser automation | Playwright optional extra; keep pyautogui fallback |

**Exit:** `runtime_backend_check.cmd` PASS for voice + screen on a configured machine.

---

## Phase D — Automation and integrations (4–6 weeks)

| # | Feature | Work |
| --- | --- | --- |
| D1 | WhatsApp reliability | Test matrix for `messaging_automation_module` + intent_router handlers |
| D2 | Telegram / Discord / Slack | New integration modules (start with read-only status + open URL) |
| D3 | IoT | Expand `iot_control.py` device profiles; document MQTT setup |
| D4 | n8n inbound webhook | `POST /api/automation/n8n/inbound` (auth token) |
| D5 | Workflow engine | Connect `workflow_engine.py` to PA tool registry for safe chains |
| D6 | Habit learning | Promote `proactive_suggestion_engine` from snapshots to scheduled suggestions |

**Exit:** Documented setup per integration; no payment/booking without explicit new approval flow.

---

## Phase E — Memory and personality (3–4 weeks)

| # | Feature | Work |
| --- | --- | --- |
| E1 | Memory ownership doc | One table: which SQLite/JSON owns what (see `CLEANUP_PLAN.md` Phase 6) |
| E2 | Session bridge | Optional export/import between terminal DB and web session (migration tests) |
| E3 | Long-term semantic memory | Always-on retrieval in chat when embeddings available |
| E4 | Personality / emotion | Deepen `personality_engine.py` + voice tone; user toggles in settings |

**Exit:** `memory status` and chat behavior agree; no duplicate conflicting stores without migration.

---

## Phase F — Not built (external / high risk)

Build only after Phases A–E are stable. Each needs **confirmation + audit** design.

| Area | Blocker |
| --- | --- |
| Food / cab / flight / shopping / payments | Legal, ToS, payment PCI — currently **blocked in code** |
| Full WhatsApp bot API | Meta Business API, ban risk |
| Android remote / SMS | Companion app + permissions |
| CCTV / Raspberry Pi | Hardware drivers |
| Full Excel/PPT automation | COM/Office licensing on Windows |
| AI avatar / AR / VR / drone | Separate products |

---

## Suggested order (your list → phases)

```text
Now        → Phase A (structure) ✅ started
Next       → Phase B (wire partial AI to chat)
Then       → Phase C (voice/vision daily use)
Then       → Phase D (integrations)
Then       → Phase E (memory/personality)
Later      → Phase F (real-world booking, etc.)
```

---

## Tracking

Update this file when a phase completes. Link PRs or commits in a short changelog section below.

### Changelog

- **2026-05-19:** Phase A started — orphan `brain/` cleanup, audit scripts, `FOLDER_STRUCTURE.md`.
- **2026-05-19:** Phase B (B1–B4) — `chat_context.py`, semantic memory + runtime prompts + project context + Ollama routing in `chat_service`.
- **2026-05-19:** Phase B5 + Phase C1 — planning prompt mode; voice readiness API + CLI.
