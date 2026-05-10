# n8n AI Agent Architecture

This guide describes a safe architecture for advanced GrandpaAssistant + n8n workflows. It is intentionally documentation-only and does not change current runtime behavior.

## Recommended Architecture

```text
User
  -> GrandpaAssistant
  -> command_router
  -> n8n_client
  -> n8n workflow
  -> AI classifier / action router
  -> external tools or local actions
```

Responsibilities:

- `GrandpaAssistant`: accepts voice/text input, detects explicit automation intent, handles user-facing replies, and keeps local safety rules intact.
- `command_router`: decides whether the command is a normal assistant command, chat request, or explicit n8n automation request.
- `n8n_client`: posts a structured payload to the local n8n webhook and returns a structured success/failure result.
- `n8n workflow`: performs multi-step orchestration, classification, entity extraction, approvals, retries, and tool calls.
- `AI classifier / action router`: converts user intent into a safe workflow branch.
- `external tools or local actions`: Gmail, Calendar, GitHub, local backend APIs, or other allowed integrations.

## Workflow Stages

Every advanced workflow should follow these stages.

1. Intent detection

Identify the automation type from `message`, not from arbitrary hidden state. Example intents: `email_draft`, `calendar_reminder`, `github_issue`, `file_backup`, `screen_analysis`, `notification`.

2. Entity extraction

Extract only the fields needed for the selected intent. Examples: recipient, reminder time, repository, issue title, folder path, screen request type.

3. Confirmation step

Ask for confirmation before any action that sends, deletes, moves, installs, restarts, shuts down, edits files, or changes system state. Prefer drafts and previews before final actions.

4. Safe action execution

Execute only the selected allowlisted branch. Do not pass raw user text into shell commands, file paths, or external API targets without validation.

5. Result reporting

Return a short structured result to GrandpaAssistant, including `ok`, `summary`, `action_taken`, and `requires_followup`.

6. Audit logging

Record minimal local audit data: timestamp, intent, branch, status, confirmation id if used, and redacted target details. Avoid storing secrets or full private content unless the workflow is explicitly a local note/log workflow.

## Example Automation Pipelines

### Gmail Draft Generation

```text
Webhook
  -> AI classifier
  -> entity extraction: recipient, subject, draft body
  -> contact/recipient validation
  -> Gmail create draft
  -> report draft link/status
```

Safety model:

- Create drafts by default.
- Require confirmation before sending.
- Redact recipient details in logs.
- Do not let free text choose arbitrary credentials.

### Google Calendar Reminder

```text
Webhook
  -> AI classifier
  -> entity extraction: title, date, time, timezone
  -> date validation
  -> Google Calendar create event/reminder
  -> report event status
```

Safety model:

- Confirm ambiguous dates.
- Use the configured calendar only.
- Log event title and date, not private notes unless needed.

### GitHub Issue Creation

```text
Webhook
  -> AI classifier
  -> entity extraction: repo, title, body, labels
  -> repository allowlist check
  -> GitHub create issue
  -> report issue URL
```

Safety model:

- Use an allowlisted repository list.
- Never expose GitHub tokens in workflow output.
- Prefer issue creation over direct code modification.

### Local File Backup

```text
Webhook
  -> AI classifier
  -> entity extraction: backup profile
  -> confirmation step
  -> GrandpaAssistant local backend approval route
  -> safe backup/check action
  -> audit log
```

Safety model:

- Do not run arbitrary shell commands from n8n.
- Use named backup profiles, not raw paths from user text.
- Require confirmation before copying, moving, deleting, or overwriting.

Example n8n HTTP Request node for safe local actions:

```text
n8n webhook
  -> Switch node
  -> HTTP Request node
  -> POST http://localhost:8765/api/local-actions/execute
```

Example body:

```json
{
  "action": "create_folder",
  "params": {
    "path": "C:/Users/YourName/Documents/GrandpaBackups"
  }
}
```

The local executor accepts structured actions only. It rejects unknown actions, dangerous paths, and shell injection patterns. It writes a local audit entry to:

```text
runtime/logs/local_actions.jsonl
```

Supported initial action request examples:

```json
{"action": "open_app", "params": {"app": "notepad"}}
```

```json
{"action": "open_url", "params": {"url": "https://example.com"}}
```

```json
{"action": "take_screenshot", "params": {}}
```

```json
{"action": "copy_file", "params": {"source": "C:/Users/YourName/Documents/input.txt", "destination": "C:/Users/YourName/Documents/Backup/input.txt"}}
```

```json
{"action": "start_obs_recording", "params": {}}
```

### Screen Analysis Request

```text
Webhook
  -> AI classifier
  -> GrandpaAssistant local screen summary API
  -> optional AI explanation
  -> result summary
```

Safety model:

- Keep screenshots and OCR local.
- Do not send screenshots to external services unless explicitly approved.
- Prefer text summaries over raw image transfer.

### Voice-Triggered Workflows

```text
Voice command
  -> GrandpaAssistant command_router
  -> n8n webhook payload with channel="voice"
  -> AI classifier
  -> selected workflow branch
  -> concise voice-friendly response
```

Safety model:

- Keep voice commands explicit, such as `trigger n8n ...` or `run automation ...`.
- Require confirmation for high-risk actions.
- Return short summaries suitable for text-to-speech.

## Safe Local Actions

Local actions need stricter rules than cloud API actions.

- Use allowlisted commands only.
- Never execute arbitrary shell input from a user, AI node, or webhook field.
- Require confirmation for delete, move, rename, shutdown, restart, install, uninstall, sending messages, payments, and system setting changes.
- Sandbox risky operations where possible.
- Prefer read-only checks first.
- Prefer GrandpaAssistant backend approval routes over direct n8n shell execution.
- Validate file paths against known safe directories.
- Reject commands containing placeholders, force flags, destructive flags, or chained shell operators unless they are explicitly modeled and approved.

Recommended local action categories:

```text
safe_read_only:
  - status checks
  - file existence checks
  - validation scripts
  - log summaries

confirmation_required:
  - file copy
  - backup profile run
  - sending email/message
  - issue creation in external systems

blocked_by_default:
  - delete
  - format
  - reset hard
  - force push
  - shutdown/restart
  - arbitrary shell command
```

## JSON Payload Contracts

### GrandpaAssistant to n8n

```json
{
  "message": "create reminder to call doctor tomorrow at 10 am",
  "source": "GrandpaAssistant",
  "channel": "voice",
  "raw_command": "trigger n8n create reminder to call doctor tomorrow at 10 am",
  "request_id": "optional-uuid",
  "timestamp": "2026-05-10T10:30:00Z"
}
```

Required fields:

- `message`
- `source`

Recommended fields:

- `channel`
- `raw_command`
- `request_id`
- `timestamp`

### n8n to AI Nodes

```json
{
  "task": "create reminder to call doctor tomorrow at 10 am",
  "context": {
    "source": "GrandpaAssistant",
    "channel": "voice",
    "locale": "en-IN"
  },
  "classification_schema": {
    "intent": "email_draft | calendar_reminder | github_issue | file_backup | screen_analysis | unknown",
    "confidence": "0.0-1.0",
    "entities": {},
    "risk_level": "safe | confirmation_required | blocked"
  }
}
```

Expected AI output:

```json
{
  "intent": "calendar_reminder",
  "confidence": 0.91,
  "entities": {
    "title": "Call doctor",
    "date_text": "tomorrow",
    "time_text": "10 am"
  },
  "risk_level": "safe",
  "needs_confirmation": false,
  "summary": "Create a reminder to call doctor tomorrow at 10 am."
}
```

### n8n to Local Automation Services

```json
{
  "action_type": "backup_profile_run",
  "profile": "documents_backup",
  "dry_run": true,
  "requires_confirmation": true,
  "request_id": "optional-uuid",
  "source": "n8n",
  "reason": "User requested a local backup."
}
```

Local service response:

```json
{
  "ok": true,
  "status": "pending_confirmation",
  "confirmation_id": "abc123",
  "summary": "Backup profile documents_backup is ready for approval.",
  "audit_id": "audit-001"
}
```

## Suggested Future Workflow Nodes

- AI classifier: classify user task and risk level.
- Memory lookup: read safe local preferences or prior context.
- OCR/screen analysis: call GrandpaAssistant screen summary APIs.
- Email tools: create Gmail drafts and optionally send after confirmation.
- Calendar tools: create reminders and events.
- GitHub tools: create issues or summarize repository events.
- Notification system: send local/mobile notifications or voice-friendly summaries.
- Approval gate: pause high-risk workflows until user confirmation.
- Audit logger: append redacted local workflow activity.
- Error handler: normalize failures into friendly assistant replies.

## Production Hardening Recommendations

- Add auth tokens for GrandpaAssistant to n8n webhook calls.
- Validate a shared webhook secret in n8n before routing.
- Use localhost-only binding unless remote access is intentionally configured.
- Add rate limiting for webhook requests.
- Add workflow retries for transient external API failures.
- Add structured logging with request ids and redacted targets.
- Add monitoring for workflow failure counts and latency.
- Keep credentials in n8n credentials storage or ignored local env files.
- Rotate tokens periodically.
- Use separate workflows for safe, confirmation-required, and blocked actions.
- Return consistent machine-readable results to GrandpaAssistant.
- Keep destructive operations behind explicit approval and backend-side allowlists.

## Recommended Reply Contract Back To GrandpaAssistant

When n8n responds to GrandpaAssistant, prefer:

```json
{
  "ok": true,
  "intent": "calendar_reminder",
  "summary": "Reminder created for tomorrow at 10 am.",
  "action_taken": "calendar_event_created",
  "requires_followup": false,
  "audit_id": "optional-audit-id"
}
```

For failures:

```json
{
  "ok": false,
  "intent": "unknown",
  "summary": "I could not classify that automation safely.",
  "action_taken": "none",
  "requires_followup": true,
  "next_question": "Should this be an email, reminder, sheet entry, or GitHub issue?"
}
```
