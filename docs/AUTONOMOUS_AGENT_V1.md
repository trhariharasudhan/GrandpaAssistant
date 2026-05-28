# Autonomous Desktop Agent v1

Autonomous Desktop Agent v1 is a safe local planning and guarded execution foundation for GrandpaAssistant. It is not full autonomy. It turns a user goal into a deterministic step plan, safety-reviews every step, stores the plan locally, and executes only allowed steps through existing safe backend paths.

The protected primary run path remains:

```powershell
python backend\desktop_backend_entry.py
```

## What It Can Do

The v1 agent supports a small Windows-first action set:

- Open an allowlisted local application through the local action executor.
- Open an HTTP/HTTPS URL through the local action executor.
- Take a screenshot through the local action executor.
- Read safe system status metadata.
- List safe directory metadata only: names, item types, and counts, not file contents.
- Create a reminder through the existing personal assistant reminder service.

`POST /api/agent/plan` is a dry run. It returns the legacy `ok`, `task`, `plan`, and `graph` fields plus v1 fields such as `plan_id`, `understood_goal`, `proposed_steps`, `safety_classification`, `confirmation_needed`, and `blocked_reasons`.

## What It Cannot Do

The v1 agent blocks destructive, external, financial, communication, account, and system-power actions. Blocked steps never execute, even if a caller sends confirmation.

Blocked examples:

- Delete files or folders.
- Format, wipe, or erase drives.
- Send messages, email, WhatsApp, SMS, or DMs.
- Make payments, purchases, orders, bookings, or checkouts.
- Change passwords, accounts, security settings, PINs, permissions, or admin mode.
- Shutdown, restart, reboot, sign out, or logout.
- Bypass safety, disable confirmation, or override permissions.

## Safety Model

Every step is classified as one of:

- `safe_read`: read-only metadata that can run without confirmation.
- `needs_confirmation`: local side-effect action that must be confirmed before execution.
- `blocked`: action is outside v1 and cannot run.

Open app, open URL, screenshot, and create reminder steps require confirmation. Real local actions go through `services.local_action_executor.execute_local_action`; reminder creation goes through the existing reminder service. Verifier failures return warning payloads instead of crashing the backend.

## Endpoint Examples

Dry-run plan:

```http
POST /api/agent/plan
Content-Type: application/json

{
  "goal": "open notepad"
}
```

Execute a reviewed plan:

```http
POST /api/agent/execute
Content-Type: application/json

{
  "plan_id": "agent-plan-abc123",
  "confirmed": true
}
```

The execute response includes `executed_steps`, `skipped_steps`, `blocked_steps`, and `verification_result`.

## Roadmap

Future phases can add richer plan repair, deeper verification, better natural-language slot extraction, and integration with browser or visual desktop systems. Those phases should keep the same rule: sensitive or irreversible actions require human-in-the-loop review, and blocked categories stay blocked until a dedicated confirmation-safe design exists.
