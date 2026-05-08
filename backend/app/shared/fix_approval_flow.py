from __future__ import annotations

import datetime
import os
import re
import subprocess
import uuid
from typing import Any

from fix_audit_log import append_fix_audit_event


_PENDING_FIX_APPROVALS: dict[str, dict[str, Any]] = {}

ACTION_TYPES = {"command_suggestion", "file_check", "documentation_note"}
BLOCKED_COMMAND_PATTERNS = (
    "pip install",
    "npm install",
    "stop-process",
    "taskkill",
    "git reset",
    "git push --force",
    "git push -f",
    "remove-item",
    "del ",
    "delete ",
    "move ",
    "ren ",
    "rename ",
)


def _utc_now() -> str:
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _has_placeholder(command: str) -> bool:
    return bool(re.search(r"<[^>]+>", command or ""))


def _contains_blocked_command(command: str) -> bool:
    lowered = f" {_compact_text(command).lower()} "
    return any(pattern in lowered for pattern in BLOCKED_COMMAND_PATTERNS)


def _command_payload(payload: dict[str, Any] | None) -> str:
    return _compact_text((payload or {}).get("command"))


def _validation(ok: bool, reason: str, *, runnable: bool = False, manual_only: bool = False) -> dict[str, Any]:
    return {
        "ok": ok,
        "reason": reason,
        "runnable": runnable,
        "manual_only": manual_only,
    }


def validate_fix_action(payload) -> dict[str, Any]:
    payload = payload or {}
    action_type = _compact_text(payload.get("action_type") or payload.get("type") or "command_suggestion")
    if action_type not in ACTION_TYPES:
        return _validation(False, "Unsupported fix action type.")
    if action_type in {"file_check", "documentation_note"}:
        return _validation(True, "This is a manual read-only note; no command will run.", runnable=False, manual_only=True)

    command = _command_payload(payload)
    if not command:
        return _validation(False, "No command was provided.")
    if _has_placeholder(command):
        return _validation(False, "The command contains placeholders. Ask the user to fill them before approval.")
    if _contains_blocked_command(command):
        return _validation(False, "This command is risky or destructive and cannot be run by the safe fix approval flow.")

    lowered = command.lower()
    if lowered == "git status":
        return _validation(True, "Read-only git status command is allowed after explicit approval.", runnable=True)
    if re.fullmatch(r"python\s+-m\s+pip\s+show\s+[A-Za-z0-9_.-]+", command, flags=re.IGNORECASE):
        return _validation(True, "Read-only pip package inspection is allowed after explicit approval.", runnable=True)
    if re.fullmatch(r"python\s+-m\s+py_compile\s+.+", command, flags=re.IGNORECASE):
        return _validation(True, "Read-only Python compile check is allowed after explicit approval.", runnable=True)
    if lowered.startswith("dir ") and len(command) > 4:
        return _validation(True, "Read-only directory listing is allowed after explicit approval.", runnable=True)
    if re.fullmatch(r"netstat\s+-ano\s+\|\s+findstr\s+:\d+", command, flags=re.IGNORECASE):
        return _validation(True, "Read-only port ownership inspection is allowed after explicit approval.", runnable=True)
    if re.fullmatch(r"get-process\s+-id\s+\d+", command, flags=re.IGNORECASE):
        return _validation(True, "Read-only process inspection is allowed after explicit approval.", runnable=True)
    if lowered == "whoami":
        return _validation(True, "Read-only account inspection is allowed after explicit approval.", runnable=True)
    return _validation(False, "This command is not on the safe read-only allow-list.")


def create_fix_approval(action_type, payload, reason, language: str = "auto") -> dict[str, Any]:
    payload = dict(payload or {})
    payload.setdefault("action_type", action_type)
    validation = validate_fix_action(payload)
    approval_id = _new_id()
    approval = {
        "id": approval_id,
        "type": "fix_approval",
        "action_type": _compact_text(action_type),
        "payload": payload,
        "reason": _compact_text(reason),
        "language": language or "auto",
        "validation": validation,
        "status": "pending",
        "created_at": _utc_now(),
        "executed_at": None,
        "result": None,
        "message": (
            f"Fix approval {approval_id}: {payload.get('command') or payload.get('description') or action_type}. "
            f"Reason: {_compact_text(reason)}. Say allow {approval_id} to run it, or dismiss {approval_id} to cancel."
        ),
    }
    _PENDING_FIX_APPROVALS[approval_id] = approval
    append_fix_audit_event("created", approval=approval, message=approval["message"])
    return approval


def list_pending_fix_approvals(limit=20) -> list[dict[str, Any]]:
    try:
        limit_value = max(1, int(limit))
    except Exception:
        limit_value = 20
    items = [item for item in _PENDING_FIX_APPROVALS.values() if item.get("status") == "pending"]
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)[:limit_value]


def get_fix_approval(approval_id):
    return _PENDING_FIX_APPROVALS.get(_compact_text(approval_id))


def dismiss_fix_approval(approval_id):
    approval = get_fix_approval(approval_id)
    if not approval:
        return False
    approval["status"] = "dismissed"
    approval["dismissed_at"] = _utc_now()
    _PENDING_FIX_APPROVALS.pop(approval["id"], None)
    append_fix_audit_event("dismissed", approval=approval, message="Fix approval dismissed.")
    return True


def mark_fix_approval_executed(approval_id, result):
    approval = get_fix_approval(approval_id)
    if not approval:
        return None
    approval["status"] = "executed"
    approval["executed_at"] = _utc_now()
    approval["result"] = result
    _PENDING_FIX_APPROVALS.pop(approval["id"], None)
    return approval


def _argv_for_command(command: str) -> list[str]:
    lowered = command.lower()
    if lowered == "git status":
        return ["git", "status"]
    if re.fullmatch(r"python\s+-m\s+pip\s+show\s+[A-Za-z0-9_.-]+", command, flags=re.IGNORECASE):
        return command.split()
    if re.fullmatch(r"python\s+-m\s+py_compile\s+.+", command, flags=re.IGNORECASE):
        return command.split()
    if lowered.startswith("dir "):
        path = command[4:].strip()
        return ["cmd.exe", "/c", "dir", path]
    if re.fullmatch(r"netstat\s+-ano\s+\|\s+findstr\s+:\d+", command, flags=re.IGNORECASE):
        port = re.search(r":\d+", command).group(0)
        return ["cmd.exe", "/c", "netstat", "-ano", "|", "findstr", port]
    if re.fullmatch(r"get-process\s+-id\s+\d+", command, flags=re.IGNORECASE):
        pid = re.search(r"\d+", command).group(0)
        return ["powershell.exe", "-NoProfile", "-Command", f"Get-Process -Id {pid}"]
    if lowered == "whoami":
        return ["whoami"]
    return []


def execute_fix_approval(approval_id, timeout_seconds: int = 10) -> dict[str, Any]:
    approval = get_fix_approval(approval_id)
    if not approval:
        return {"ok": False, "executed": False, "message": "Fix approval was not found or already handled."}
    validation = validate_fix_action(approval.get("payload"))
    if not validation.get("ok") or not validation.get("runnable"):
        result = {
            "ok": False,
            "executed": False,
            "message": validation.get("reason") or "This fix action is not runnable.",
            "validation": validation,
        }
        append_fix_audit_event("blocked", approval=approval, result=result, message=result["message"])
        return result
    command = _command_payload(approval.get("payload"))
    argv = _argv_for_command(command)
    if not argv:
        result = {"ok": False, "executed": False, "message": "This command could not be converted into a safe argument list."}
        append_fix_audit_event("blocked", approval=approval, result=result, message=result["message"])
        return result
    try:
        completed = subprocess.run(
            argv,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
            timeout=max(1, int(timeout_seconds)),
            shell=False,
        )
        result = {
            "ok": completed.returncode == 0,
            "executed": True,
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
            "no_destructive_action": True,
        }
    except subprocess.TimeoutExpired as error:
        result = {
            "ok": False,
            "executed": False,
            "command": command,
            "message": "Command timed out before completing.",
            "stdout": (error.stdout or "")[-4000:] if isinstance(error.stdout, str) else "",
            "stderr": (error.stderr or "")[-4000:] if isinstance(error.stderr, str) else "",
        }
        append_fix_audit_event("failed", approval=approval, result=result, message=result.get("message", "Fix command failed."))
        mark_fix_approval_executed(approval_id, result)
        return result
    except Exception as error:
        result = {
            "ok": False,
            "executed": False,
            "command": command,
            "message": _compact_text(error),
        }
        append_fix_audit_event("failed", approval=approval, result=result, message=result.get("message", "Fix command failed."))
        mark_fix_approval_executed(approval_id, result)
        return result
    append_fix_audit_event("executed", approval=approval, result=result, message="Fix approval command executed.")
    mark_fix_approval_executed(approval_id, result)
    return result


def clear_fix_approvals_for_tests() -> None:
    _PENDING_FIX_APPROVALS.clear()
