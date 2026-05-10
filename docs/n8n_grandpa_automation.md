# n8n GrandpaAssistant Automation

GrandpaAssistant can forward explicit automation commands to a local n8n webhook. This keeps automation orchestration in n8n while GrandpaAssistant stays focused on voice/text command handling and safety.

## Current Integration

Local n8n webhook:

```text
http://localhost:5678/webhook/grandpa-message
```

GrandpaAssistant API test route:

```text
POST /api/automation/n8n/test
```

Assistant command examples:

```text
trigger n8n hello from voice
send to n8n save this note
run automation create reminder tomorrow at 9 am
automate add this to sheet
Grandpa automate create GitHub issue for login bug
```

Normal chat is not sent to n8n. Only explicit automation phrases should trigger the webhook.

## Payload Format

GrandpaAssistant sends JSON like this:

```json
{
  "message": "hello from voice",
  "source": "GrandpaAssistant",
  "channel": "voice",
  "raw_command": "trigger n8n hello from voice"
}
```

Fields:

- `message`: the useful task text after the trigger phrase.
- `source`: always `GrandpaAssistant`.
- `channel`: `voice`, `text`, or the available command channel.
- `raw_command`: the original command the user said or typed.

## Example Workflow Ideas

### Echo/Test Workflow

Use this first to confirm the webhook works.

Suggested nodes:

```text
Webhook -> Respond to Webhook
```

Webhook node:

```text
Method: POST
Path: grandpa-message
Respond: When Last Node Finishes
```

Response body can echo:

```json
{
  "received": "={{$json.body.message}}",
  "source": "={{$json.body.source}}",
  "channel": "={{$json.body.channel}}"
}
```

### Save Message To Google Sheet

Suggested nodes:

```text
Webhook -> Google Sheets Append Row -> Respond to Webhook
```

Suggested row columns:

```text
timestamp, message, source, channel, raw_command
```

Use this for commands like:

```text
send to n8n save grocery list to sheet
```

### Send Gmail Draft

Suggested nodes:

```text
Webhook -> Switch -> Gmail Create Draft -> Respond to Webhook
```

Keep email sending as a draft by default. Sending email should require a deliberate review step.

Example command:

```text
run automation email draft to Ravi saying I will call tomorrow
```

### Create Google Calendar Reminder

Suggested nodes:

```text
Webhook -> Switch -> Date/Time parsing -> Google Calendar Create Event -> Respond to Webhook
```

Example command:

```text
trigger n8n reminder call doctor tomorrow at 10 am
```

### GitHub Issue Creation

Suggested nodes:

```text
Webhook -> Switch -> GitHub Create Issue -> Respond to Webhook
```

Example command:

```text
Grandpa automate create GitHub issue for startup smoke check failure
```

Use a fixed repository or a reviewed allowlist. Avoid letting arbitrary user text choose sensitive repository targets.

### Local PC Backup Trigger

Recommended safe pattern:

```text
Webhook -> Switch -> GrandpaAssistant backend approval route -> Respond to Webhook
```

n8n should not run destructive shell commands directly. For local PC tasks, call a GrandpaAssistant backend route that enforces allowlists and confirmation.

Example command:

```text
run automation start safe backup check
```

## Recommended Switch Node Routing

Add a Switch node after the Webhook node and route based on `{{$json.body.message}}`.

Suggested conditions:

```text
if message contains "email" -> email branch
if message contains "reminder" -> calendar branch
if message contains "sheet" or "save" -> sheets branch
if message contains "github" or "issue" -> GitHub branch
otherwise -> default log/echo branch
```

Default branch:

```text
Log message -> Respond with "Automation received"
```

## Ready-To-Import Workflow Examples

Workflow JSON examples are available in:

```text
docs/n8n_workflows/
```

Files:

```text
grandpa_echo_test.json
grandpa_local_action_open_notepad.json
grandpa_take_screenshot.json
```

Import steps:

1. Open n8n at `http://localhost:5678`.
2. Select `Import from File`.
3. Choose one JSON file from `docs/n8n_workflows/`.
4. Save the workflow.
5. Activate the workflow before using the production webhook.

Activation:

```text
Workflow page -> Active toggle -> On
```

Test mode:

```text
Click Listen for test event / Execute workflow, then call /webhook-test/grandpa-message.
```

Production mode:

```text
Activate the workflow, then call /webhook/grandpa-message.
```

Docker networking note:

Because n8n runs inside Docker, n8n must call the Windows host backend through:

```text
http://host.docker.internal:8765/api/local-actions/execute
```

If the backend is running on port `8000`, use:

```text
http://host.docker.internal:8000/api/local-actions/execute
```

Do not use `localhost` inside the n8n HTTP Request node for GrandpaAssistant backend calls; inside Docker, `localhost` means the n8n container itself.

## Curl Tests

### Direct n8n Production Webhook

```powershell
curl.exe -X POST "http://localhost:5678/webhook/grandpa-message" ^
  -H "Content-Type: application/json" ^
  --data-raw "{\"message\":\"hello from direct n8n test\",\"source\":\"GrandpaAssistant\",\"channel\":\"text\",\"raw_command\":\"direct curl test\"}"
```

### Direct n8n Test Webhook

Use this only after clicking `Listen for test event` or `Execute workflow` in n8n:

```powershell
curl.exe -X POST "http://localhost:5678/webhook-test/grandpa-message" ^
  -H "Content-Type: application/json" ^
  --data-raw "{\"message\":\"hello from n8n test mode\",\"source\":\"GrandpaAssistant\",\"channel\":\"text\",\"raw_command\":\"test webhook\"}"
```

### GrandpaAssistant API Test

Desktop backend port:

```powershell
curl.exe -X POST "http://localhost:8765/api/automation/n8n/test" ^
  -H "Content-Type: application/json" ^
  --data-raw "{\"message\":\"hello from GrandpaAssistant API\"}"
```

Legacy/chat API port if running:

```powershell
curl.exe -X POST "http://localhost:8000/api/automation/n8n/test" ^
  -H "Content-Type: application/json" ^
  --data-raw "{\"message\":\"hello from GrandpaAssistant API\"}"
```

### Assistant Command Examples

Type or say:

```text
trigger n8n hello from voice
send to n8n save this note in sheet
run automation reminder take medicine at 8 pm
automate email draft to family saying I reached safely
Grandpa automate create GitHub issue for n8n webhook setup
trigger n8n open notepad
trigger n8n take screenshot
```

Expected assistant reply:

```text
Automation sent to n8n successfully.
```

If n8n is offline:

```text
n8n automation is not available right now.
```

## Safety Notes

- Keep n8n local on `localhost` unless you add authentication, TLS, and careful firewall rules.
- Do not expose the webhook publicly without auth.
- Use confirmation before destructive actions such as deleting files, moving files, shutdown, restart, installs, or external sends.
- Never run dangerous shell commands directly from n8n.
- Prefer allowlisted read-only commands and GrandpaAssistant backend approval routes for local PC actions.
- Keep secrets in n8n credentials or local ignored config files, not in workflow JSON.
- Use Gmail drafts before real sends.
- Use fixed/allowlisted targets for GitHub repos, folders, backup paths, and calendar accounts.
- Log only minimal automation status. Avoid logging private message contents unless the workflow is intentionally a local log workflow.

## Minimal Importable Workflow Shape

Use this as a starting point if you want to create a simple echo workflow manually in n8n:

```json
{
  "name": "Grandpa Message Webhook",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "grandpa-message",
        "responseMode": "lastNode",
        "options": {}
      },
      "name": "Grandpa Message Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2.1,
      "position": [260, 300],
      "webhookId": "grandpa-message"
    }
  ],
  "connections": {},
  "settings": {},
  "active": false
}
```

After importing, activate the workflow before using:

```text
http://localhost:5678/webhook/grandpa-message
```
