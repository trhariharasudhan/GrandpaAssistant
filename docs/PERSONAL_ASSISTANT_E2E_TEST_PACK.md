# Personal Assistant E2E Test Pack

This dev-only test pack verifies GrandpaAssistant's context-aware personal assistant behavior through the same `chat_service.build_chat_reply(...)` path used by terminal chat.

## Mock Mode

Default mode is safe. It does not change real volume, open or close real apps, capture the real screen, or call a real LLM provider.

```powershell
.venv\Scripts\python.exe scripts\dev\personal_assistant_e2e.py
```

JSON output:

```powershell
.venv\Scripts\python.exe scripts\dev\personal_assistant_e2e.py --json
.venv\Scripts\python.exe scripts\dev\personal_assistant_e2e.py --scheduler-once
```

## Optional Real Mode

Use these only when you intentionally want to exercise real local adapters:

```powershell
.venv\Scripts\python.exe scripts\dev\personal_assistant_e2e.py --real-volume
.venv\Scripts\python.exe scripts\dev\personal_assistant_e2e.py --real-apps
.venv\Scripts\python.exe scripts\dev\personal_assistant_e2e.py --real-screen
.venv\Scripts\python.exe scripts\dev\personal_assistant_e2e.py --enable-llm-planner
```

Flags can be combined, but start with one at a time. Real app mode can open and close allowlisted apps. Real screen mode can capture local screenshot/OCR context. Real LLM planner mode can call a configured local or cloud provider.

## Flows Covered

- Normal greeting: verifies no action intent is triggered.
- Normal chat fallback: verifies provider fallback still works.
- Volume decrease: verifies volume intent and tool execution in mock mode.
- Reminder completion: verifies missing details, structured reminder storage, pending reminder listing, simulated due notification without sleeping, mark-done, and cancellation.
- Scheduler one tick: optional `--scheduler-once` flow runs one mocked scheduler tick without enabling a background loop.
- Laptop diagnostics follow-up: verifies `check everything` resolves to diagnostics.
- Open calculator then close it: verifies confirmation and tracked close behavior.
- Screen read request: verifies explicit screen-read path with mocked OCR.
- Unsupported action: verifies missing adapter explanation.
- Dangerous action: verifies destructive requests are blocked.
- Windows startup opt-in: verifies startup status, explicit confirmation for enable, and disable using mocked Startup-folder actions.
- Voice wake command: verifies voice status, explicit confirmation for enable, wake-word transcript routing, mocked speech output, and disable without using a real microphone.
- Long-term memory: verifies explicit remember, uncertain conflict creation, natural conflict confirmation, planner use of the resolved preferred editor, implicit preference learning, memory review, cleanup suggestions, memory recall, and forget using an isolated local test memory file.
- Capability discovery: verifies `what can you do?` uses the registry.

## Assertions

The runner checks behavior categories rather than exact reply text:

- Detected intent or tool category.
- Missing parameters are requested.
- Confirmation is required where expected.
- Executor is called or safely mocked.
- Reminder due checks can be simulated with an injected time and mock notifier.
- Memory assertions use structured categories, conflict confirmation, update/review/cleanup behavior, and do not require exact reply text.
- Chat fallback still works.
- Debug metadata is not leaked in normal mode.

## Common Failures

- Volume flow fails: `adjust_volume` intent detection or registry mapping changed.
- Reminder flow fails: scheduler storage, reminder registry tools, or mock productivity-store patching changed.
- Startup flow fails: startup manager intent routing, registry tools, or mock startup manager patching changed.
- Voice flow fails: wake-word runtime routing, registry tools, or mock voice runtime patching changed.
- Memory flow fails: memory intent routing, local memory path isolation, structured extraction, conflict follow-up resolution, update/review/cleanup tools, or forget matching changed.
- Calculator flow fails: open/close confirmation context changed.
- Screen flow fails: screen adapter import path or mock wiring changed.
- Normal chat fails: personal assistant is intercepting provider fallback too broadly.
- Runtime becomes slow: a test may be calling real OCR, app, LLM, or diagnostics adapters without mocks.
