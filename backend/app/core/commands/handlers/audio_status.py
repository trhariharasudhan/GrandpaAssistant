from __future__ import annotations

from ..context import CommandContext
from ..result import CommandResult
from ..summaries import audio as audio_summaries


SOUND_STATUS_COMMANDS = {
    "sound status",
    "sounds status",
    "assistant sound status",
}
AUDIO_STATUS_COMMANDS = {
    "audio status",
    "assistant audio status",
    "audio summary",
}
CHIME_STATUS_COMMANDS = {
    "chime status",
    "voice chime status",
    "wake chime status",
    "desktop chime status",
}
NOTIFICATION_SOUND_COMMANDS = {
    "notification sound summary",
    "notification sound status",
    "notification sounds",
}
VOICE_AUDIO_READINESS_COMMANDS = {
    "voice audio readiness",
    "voice audio status",
    "microphone readiness",
    "mic readiness",
    "tts readiness",
}
DANGEROUS_PREFIXES = (
    "play ",
    "test ",
    "enable ",
    "disable ",
    "turn on ",
    "turn off ",
    "set ",
    "change ",
    "update ",
    "use ",
    "switch ",
    "start ",
    "stop ",
    "record ",
    "listen ",
    "capture ",
    "speak ",
    "say ",
)


def handle_audio_status_command(command: str, context: CommandContext) -> CommandResult:
    """Handle read-only sound/audio/chime status commands only."""
    normalized = " ".join(str(command or "").split()).strip().lower()
    if not normalized:
        return CommandResult.not_handled()
    if normalized.startswith(DANGEROUS_PREFIXES):
        return CommandResult.not_handled()
    if normalized in SOUND_STATUS_COMMANDS:
        return CommandResult(True, audio_summaries.sound_status_summary(), route="audio_status.sound")
    if normalized in AUDIO_STATUS_COMMANDS:
        return CommandResult(True, audio_summaries.audio_status_summary(), route="audio_status.audio")
    if normalized in CHIME_STATUS_COMMANDS:
        return CommandResult(True, audio_summaries.chime_status_summary(), route="audio_status.chime")
    if normalized in NOTIFICATION_SOUND_COMMANDS:
        return CommandResult(True, audio_summaries.notification_sound_summary(), route="audio_status.notification_sound")
    if normalized in VOICE_AUDIO_READINESS_COMMANDS:
        return CommandResult(True, audio_summaries.voice_audio_readiness_summary(), route="audio_status.voice_readiness")
    return CommandResult.not_handled()
