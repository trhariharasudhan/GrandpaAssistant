# Automation Safety Policy

## Dangerous Action Categories

- Shell execution and script running.
- File creation, editing, movement, deletion, or overwrite.
- Git mutation.
- System power/session controls.
- App/window launch, close, focus, or control.
- UI click/type/hotkey automation.
- Screen, camera, microphone, and OCR capture.
- Contact calls/messages/emails.
- Emergency alerts and location sharing.
- IoT device control.
- Security/auth/admin/config changes.
- Payment, credential, or account changes.

## Confirmation Requirements

- Confirm destructive, irreversible, external, private, financial, security-sensitive, or system-level actions.
- Confirmation should include action, target, and expected effect.
- Read-only status/help/list commands do not need confirmation.

## Shell Command Restrictions

- Inspect before execution.
- Avoid generated shell commands unless reviewed.
- Treat install, network, admin, and process-control commands as higher risk.
- Report command failures honestly.

## Filesystem Safety

- Verify paths before writes/deletes.
- Never recursively delete without explicit approval and path checks.
- Avoid editing runtime secrets and local data.
- Keep user changes intact.

## Destructive Operation Safeguards

- Prefer dry-run or read-only alternatives.
- Ask for confirmation.
- Log/audit the action when appropriate.
- Provide a rollback plan when feasible.

## External Website Caution

- Avoid entering credentials or personal data unless explicitly requested.
- Do not purchase, submit, send, publish, or sign without confirmation.
- Verify page state before acting.

## Credential, Payment, And Privacy Handling

- Do not expose tokens or credentials in responses.
- Do not store sensitive data in prompts.
- Avoid screenshots/capture unless necessary and permitted.
- Treat contacts, messages, location, and emergency flows as privacy-sensitive.

## Audit And Logging Principles

- Log action intent and result, not secrets.
- Keep safety decisions inspectable.
- Separate read-only summaries from action logs.

## Execution Verification

- Verify command results.
- Verify UI/app state where possible.
- Verify file changes with tests or diffs.
- State unverified outcomes plainly.
