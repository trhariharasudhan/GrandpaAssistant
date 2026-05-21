# Local Action Orchestrator

The local action orchestrator is a safe, plan-only routing layer across GrandpaAssistant's newer local action systems.

It does not replace `command_router.py`, and it does not execute risky actions silently.

## Modules

- `backend/app/local_action_orchestrator/models.py`
- `backend/app/local_action_orchestrator/intent_mapper.py`
- `backend/app/local_action_orchestrator/orchestrator.py`
- `backend/app/api/local_action_orchestrator_api.py`

## API

Prefix:

```text
/api/local-actions
```

Endpoints:

```text
POST /api/local-actions/classify
POST /api/local-actions/plan
```

Request:

```json
{
  "command": "open browser and search laptops"
}
```

Plan response shape:

```json
{
  "command": "open browser and search laptops",
  "detected_domain": "browser",
  "confidence": 0.61,
  "plan_steps": [],
  "requires_confirmation": false,
  "risk_level": "safe_local_action",
  "next_action": "safe_to_execute_after_user_review",
  "reason": "Command mentions browser, web search, website, or browser-owned task."
}
```

## Domains

- `browser`
- `chat`
- `visual_desktop`
- `autonomous_agent`
- `general`

## Example Routing

| Command | Domain | Confirmation |
| --- | --- | --- |
| `open browser and search laptops` | `browser` | No |
| `send message to Riya that I will call later` | `chat` | Yes |
| `screen la enna iruku paaru` | `visual_desktop` | No |
| `book train ticket tomorrow` | `autonomous_agent` | Yes |
| `hi da` | `general` | No |

## Safety Boundaries

- No real WhatsApp, Telegram, Discord, or Slack calls are made.
- No browser order, payment, booking, apply, submit, or send action is executed.
- No screen click is performed by this orchestrator.
- Risky actions return confirmation requirements and next-step guidance.
- This is not wired into `command_router.py`.

## API Examples

PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/local-actions/plan -ContentType "application/json" -Body '{"command":"open browser and search laptops"}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/local-actions/plan -ContentType "application/json" -Body '{"command":"send message to Riya that I will call later"}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/local-actions/plan -ContentType "application/json" -Body '{"command":"screen la enna iruku paaru"}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/local-actions/plan -ContentType "application/json" -Body '{"command":"book train ticket tomorrow"}'
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/local-actions/plan -ContentType "application/json" -Body '{"command":"hi da"}'
```

## Validation

```powershell
.venv\Scripts\python.exe -m unittest tests.test_local_action_orchestrator -v
.venv\Scripts\python.exe -m py_compile backend/app/local_action_orchestrator/*.py backend/app/api/local_action_orchestrator_api.py tests/test_local_action_orchestrator.py
```

