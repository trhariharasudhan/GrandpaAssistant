from __future__ import annotations

from core.commands.context import CommandContext
from core.commands.result import CommandResult


DEVELOPER_MODE_COMMANDS = {
    "developer mode status",
    "what is developer mode",
    "developer help",
}

DEVELOPER_WORKSPACE_COMMANDS = {
    "developer summary",
    "workspace summary",
    "coding summary",
}

GIT_STATUS_COMMANDS = {
    "git status",
    "check git status",
    "developer git status",
}

GIT_BRANCH_COMMANDS = {
    "current git branch",
    "what branch am i on",
    "git branch",
}

GIT_REMOTE_COMMANDS = {
    "git remotes",
    "show git remotes",
    "github remotes",
}

GIT_RECENT_COMMITS_COMMANDS = {
    "recent commits",
    "git recent commits",
    "show recent commits",
}

GIT_REPO_SUMMARY_COMMANDS = {
    "github summary",
    "git summary",
    "repository summary",
}

DANGEROUS_DEVELOPER_PREFIXES = (
    "git add",
    "git commit",
    "git push",
    "git pull",
    "git reset",
    "git checkout",
    "git merge",
    "git rebase",
    "save ",
    "run ",
    "execute ",
    "open ",
    "start ",
    "launch ",
    "enable ",
    "disable ",
    "turn on ",
    "turn off ",
    "set ",
    "change ",
    "update ",
    "write ",
    "edit ",
    "delete ",
    "remove ",
)


def handle_developer_status_command(command: str, context: CommandContext) -> CommandResult:
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized or normalized.startswith(DANGEROUS_DEVELOPER_PREFIXES):
        return CommandResult.not_handled()

    if normalized in DEVELOPER_MODE_COMMANDS:
        return CommandResult(True, context.developer_mode_status_summary(), route="developer_status.mode")
    if normalized in DEVELOPER_WORKSPACE_COMMANDS:
        return CommandResult(True, context.developer_workspace_summary(), route="developer_status.workspace")
    if normalized in GIT_STATUS_COMMANDS:
        return CommandResult(True, context.git_status_summary(), route="developer_status.git_status")
    if normalized in GIT_BRANCH_COMMANDS:
        return CommandResult(True, context.git_branch_summary(), route="developer_status.git_branch")
    if normalized in GIT_REMOTE_COMMANDS:
        return CommandResult(True, context.git_remotes_summary(), route="developer_status.git_remotes")
    if normalized in GIT_RECENT_COMMITS_COMMANDS:
        return CommandResult(True, context.git_recent_commits_summary(), route="developer_status.git_recent_commits")
    if normalized in GIT_REPO_SUMMARY_COMMANDS:
        return CommandResult(True, context.git_repo_summary(), route="developer_status.git_repo")
    return CommandResult.not_handled()
