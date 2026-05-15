from __future__ import annotations

import re

from ..context import CommandContext
from ..result import CommandResult


LOCAL_CONTACT_LIST_COMMANDS = {
    "show contact",
    "show contacts",
    "list contacts",
    "my contacts",
}
GOOGLE_CONTACT_LIST_COMMANDS = {
    "list google contacts",
    "show google contacts",
    "show synced contacts",
}
GOOGLE_CONTACT_CHANGES_COMMANDS = {
    "show google contact changes",
    "google contact changes",
    "recent contact changes",
}
FAVORITE_CONTACTS_COMMANDS = {
    "list favorite contacts",
    "show favorite contacts",
}
CONTACT_ALIASES_COMMANDS = {
    "list contact aliases",
    "show contact aliases",
}
DANGEROUS_PREFIXES = (
    "call ",
    "message ",
    "mail ",
    "email ",
    "send ",
    "add ",
    "edit ",
    "update ",
    "delete ",
    "remove ",
    "sync ",
    "refresh ",
    "authorize ",
    "merge ",
    "import ",
    "favorite ",
    "pin ",
    "unfavorite ",
    "unpin ",
    "set ",
    "save ",
    "remember ",
    "copy ",
)


def handle_contacts_command(command: str, context: CommandContext) -> CommandResult:
    """Handle read-only local/Google contact lookup and summary commands only."""
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()
    if normalized in LOCAL_CONTACT_LIST_COMMANDS:
        return CommandResult(True, context.local_contacts_summary(), route="contacts.local_list")
    find_match = re.match(r"^(?:find|search) contact\s+(.+)$", normalized)
    if find_match:
        return CommandResult(True, context.local_contact_lookup_summary(find_match.group(1).strip()), route="contacts.local_find")
    if normalized in GOOGLE_CONTACT_LIST_COMMANDS:
        return CommandResult(True, context.google_contacts_summary(), route="contacts.google_list")
    if normalized in GOOGLE_CONTACT_CHANGES_COMMANDS:
        return CommandResult(True, context.google_contact_changes_summary(), route="contacts.google_changes")
    if normalized in FAVORITE_CONTACTS_COMMANDS:
        return CommandResult(True, context.favorite_contacts_summary(), route="contacts.favorites")
    if normalized in CONTACT_ALIASES_COMMANDS:
        return CommandResult(True, context.contact_aliases_summary(), route="contacts.aliases")
    return CommandResult.not_handled()
