# Backend Stability Guide

GrandpaAssistant is currently a backend-only Windows-first assistant. The release lock is a lightweight stability gate: it should pass before merging backend changes, packaging a release, or doing hardware-facing testing.

## Run Validation

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\dev\full_backend_validation.py
```

Useful individual checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\dev\startup_smoke_check.py
```

The full validation script writes the last-known result to:

```text
runtime\data\last_backend_validation.json
```

That file is runtime state and is ignored by git.

## Stability Dashboard Command

In the assistant command router, use one of:

```text
backend health summary
backend stability dashboard
release lock status
```

The command reports API health, voice dependencies, Ollama, OCR, camera/vision, runtime data paths, command confirmation state, and the last full validation result when available.

## What Each Check Means

`unittest discover` runs backend regression tests. These cover chat behavior, command confirmation IDs, CORS safety, optional dependency guards, startup diagnostics, security classification, IoT control, and productivity storage.

`startup_smoke_check` launches the backend through the normal startup path, waits for `/api/health`, switches into text mode, exits, and confirms the process shuts down cleanly.

`backend py_compile` compiles every backend Python file. This catches syntax errors before runtime.

`core backend import check` imports key backend modules including API entrypoints, command routing, voice, vision, security, memory, and LLM clients. This catches missing imports and startup-time crashes.

`optional dependency readiness summary` uses startup diagnostics. Missing microphone, camera, OCR, Piper, Ollama, and model dependencies are warnings unless they prevent core backend startup.

## Debug Common Failures

If unit tests fail, start with the first failing test. Most tests are targeted and name the behavior being protected.

If startup smoke fails because the API is already running, stop the existing backend server and rerun validation.

If startup smoke fails during launch, run:

```powershell
.\.venv\Scripts\python.exe backend\desktop_backend_entry.py
```

Then check whether `/api/health` becomes reachable on `http://127.0.0.1:8765/api/health`.

If py_compile fails, fix the syntax error before investigating runtime behavior.

If import checks fail, inspect the reported module. Import failures are often caused by adding an optional dependency at module import time instead of guarding it with a safe fallback.

If optional hardware warnings appear, verify the relevant feature only when that hardware is expected. Missing camera, microphone, OCR, or Ollama should not block general backend validation.

## Safe Feature Rules

Add regression tests before changing shared behavior.

Keep optional dependencies behind guarded imports and return warning payloads or friendly fallback messages when hardware is missing.

Do not treat natural questions as system commands unless the command intent is explicit.

Use confirmation IDs for dangerous actions. Allowing or dismissing one pending action must not affect another pending action.

Keep CORS local by default. Do not add wildcard origins with credentials.

Prefer small changes in existing modules until `web_api.py` is split according to `docs/API_ROUTER_SPLIT_PLAN.md`.
