# Agent Runtime Architecture

Grandpa Assistant now includes a modular multi-agent runtime layer on top of the existing feature modules.

## Runtime Components

- `backend/app/agents/base.py`
  Shared base class for every runtime agent.
- `backend/app/agents/message_bus.py`
  In-process message bus used for agent-to-agent events.
- `backend/app/agents/state_store.py`
  Centralized runtime state persisted to `runtime/data/agent_runtime_state.json`.
- `backend/app/agents/catalog.py`
  Default runtime agents wired to the existing assistant features.
- `backend/app/agents/runtime.py`
  Global runtime coordinator and background heartbeat loop.

## Registered Agents

- `brain-agent`
  Model routing, Ollama availability, fast/deep/adaptive thinking state.
- `voice-agent`
  STT, TTS, wake word, clap wake, and voice-mode configuration.
- `vision-agent`
  OCR, object detection, face-security readiness.
- `task-agent`
  Tasks, reminders, planner snapshot, automation highlights.
- `memory-agent`
  Semantic memory and mood-memory status.
- `emotion-agent`
  Text emotion analysis and mood tracking.
- `plugin-manager`
  Dynamic plugin discovery, enable/disable, reload metadata.
- `intelligence-agent`
  Self-improvement, insights, contextual recall, decision support, workflows, recovery, sync, and proactive idle suggestions.

## New API Endpoints

- `GET /runtime`
- `POST /runtime/thinking-mode`
- `POST /runtime/autonomous-mode`
- `GET /agents`
- `GET /agents/bus`
- `GET /goals`
- `POST /goals`
- `GET /plugins`
- `POST /plugins/reload`
- `POST /plugins/toggle`
- `GET /mood`
- `POST /mood/reset`
- `GET /intelligence/status`
- `GET /insights`
- `POST /feedback`
- `GET /memory/contextual-recall`
- `POST /decision`
- `GET /knowledge-graph`
- `GET /workflows`
- `POST /workflows`
- `POST /workflows/run`
- `GET /recovery`
- `GET /sync/status`
- `POST /sync/config`
- `GET /sync/export`
- `POST /sync/import`
- `GET /proactive/conversation`

## Integration Notes

- The root FastAPI backend starts the runtime automatically during startup.
- The web/dashboard API also bootstraps the runtime if it is accessed first.
- Chat, ask, and streaming chat flows now record:
  - emotion
  - mood history
  - runtime conversation context
  - assistant replies

## Plugin Management

Plugin metadata and enabled/disabled state are managed through:

- `backend/app/shared/plugin_system.py`
- `runtime/data/plugin_registry.json`

Plugins can expose:

- `name`
- `description`
- `version`
- `hooks`
- `config`
- `execute(...)`
