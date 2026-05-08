# Windows Control Audit

GrandpaAssistant includes a backend-only Windows control audit that reports which local control features are implemented, how they are routed, and what safety level applies.

Run the audit from the repository root:

```bat
.venv\Scripts\python.exe scripts\dev\windows_controls_audit.py
```

The audit is read-only. It does not call anyone, click buttons, change settings, stop processes, delete files, or run destructive actions.

## API

Localhost/admin only:

```text
GET /api/windows/controls/audit
```

Remote unauthenticated requests receive `403`.

## Assistant Commands

- `windows controls audit`
- `full control check`
- `enna enna control panna mudiyum`
- `control list`

## Supported Categories

### App And Window Controls

Examples:

- `open notepad`
- `close notepad`
- `active window`
- `minimize window`
- `maximize window`
- `switch to chrome`

Closing apps and other disruptive actions can require confirmation depending on the command.

### Browser And System Navigation

Examples:

- `open google.com`
- `search web for weather`
- `open downloads`

### Keyboard And Mouse Controls

Examples:

- `type hello`
- `paste that`
- `open run box`
- `scroll down`
- `click start button`

Typing and click-like actions should be treated carefully because they affect the active app.

### System Controls

Examples:

- `volume up`
- `set volume to 40`
- `brightness up`
- `take screenshot`
- `lock system`
- `shutdown system`
- `restart system`

Shutdown, restart, sign out, security changes, and other risky actions require confirmation and security handling.

### Communication

Examples:

- `call mom`
- `call 9876543210`
- `riyaa ku call pannu`
- `cll pannu riyaa`
- `open phone link`
- `whatsapp call riyaa`

Direct call behavior:

- Clear non-emergency phone numbers or contact names start the local call flow directly through the Windows `tel:` handler.
- Missing targets ask a clarification question.
- Ambiguous contacts ask the user to choose or provide an exact name.
- Emergency numbers are not called automatically.
- If Windows cannot handle `tel:` links, GrandpaAssistant returns: `Phone Link or default tel: handler is not configured.`

Sending messages, email, payments, or other outgoing content remains confirmation-protected.

### Productivity

Examples:

- `add note buy milk`
- `remind me to call mom`
- `help me with files`

File deletion, moves, renames, and write operations remain confirmation-protected or blocked by safer debug/fix approval paths.

### Debug Assistant

Examples:

- `debug this`
- `give fix plan`
- `apply fix`
- `fix audit`
- `start debug session`
- `debug dashboard`

Debug fix execution is approval-based. Only allow-listed read-only commands can run after explicit `allow <id>`.

### Voice And Chat

Examples:

- text chat through backend APIs
- voice input readiness
- TTS readiness
- wake/direct commands

Optional microphone, TTS, Ollama, camera, and OCR dependencies should report warnings instead of crashing startup.

## What Requires Confirmation

- Delete, move, rename, or modify files
- Shutdown, restart, sign out, or security-sensitive system actions
- Install or uninstall software
- Send messages, email, payment, or other outgoing content
- Run non-read-only commands
- Modify system/security settings

## Runtime Verification

Use the runtime helper for backend startup and endpoint checks:

```bat
scripts\dev\runtime_backend_check.cmd
```
