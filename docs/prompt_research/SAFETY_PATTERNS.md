# Safety Patterns

This document captures reusable safety architecture patterns for GrandpaAssistant. It does not quote reference prompts.

## Risky Action Categories

- File mutation: create, edit, delete, move, overwrite, format, or bulk rewrite files.
- Shell execution: install packages, start services, run scripts, execute generated commands.
- Git mutation: add, commit, push, pull, reset, checkout, merge, rebase, tag.
- System control: shutdown, restart, sleep, lock, unlock, app launch/close, window control.
- Desktop automation: click, type, hotkey, screen capture, OCR capture, object detection execution.
- External communication: call, message, email, send alert, share location.
- IoT/home automation: turn devices on/off, pair devices, validate live connectivity, change config.
- Security/auth: authenticate, enroll, trust, emergency mode, admin escalation, key/config writes.
- Memory mutation: save, forget, delete, clear profile or preferences.

## Confirmation Rules

- Read-only status and summaries can run without confirmation.
- Reversible local actions may run if the user clearly requested them.
- Destructive, external, or privacy-sensitive actions need explicit confirmation.
- Confirmation should name the concrete action, target, and likely effect.
- Emergency flows should still distinguish status/help from actual triggering.

## Shell Command Safety

- Prefer read-only commands during investigation.
- Explain commands that mutate files, install packages, alter git state, or affect processes.
- Do not run generated shell commands blindly.
- Validate command output before reporting success.
- Treat network, dependency install, and admin commands as higher risk.

## File Operation Safety

- Read files before editing.
- Use narrow patches.
- Do not delete or revert unrelated user changes.
- Avoid broad recursive operations unless the target path is verified.
- Keep runtime data, tokens, credentials, and local reference folders ignored.

## Browser/Research Safety

- Use browsing when facts may have changed or the user asks for latest/current information.
- Prefer primary sources for technical or high-stakes claims.
- Keep source-derived text brief and paraphrased.
- Do not turn search results into claims without opening/checking sources when precision matters.

## Screen/Automation Safety

- Treat screen/camera/OCR capture as privacy-sensitive.
- Separate "describe what is visible" from "act on the UI."
- Require confirmation before click/type/execute flows.
- Avoid repeating actions if the current screen state is uncertain.

## Failure Handling

- State when a tool failed, timed out, or was unavailable.
- Keep partial results separate from verified results.
- Offer a safe next step instead of pretending success.
- Preserve backend runtime stability over aggressive cleanup.
