from __future__ import annotations

import contextlib
import io
import re
from dataclasses import asdict
from typing import Any

import core.command_router as legacy_command_router
from cognition.recovery_engine import record_system_error
from core.module_contracts import CommandModule, ModuleRequest, ModuleResult, compact_text
from integrations.weather_module import get_weather_report
import system.media_module as media_module
from system.windows_voice_control_module import DEFAULT_APP_COMMANDS, open_default_windows_app
import voice.speak as voice_speak_module


_DIRECT_ACTION_PREFIXES = (
    "open ",
    "close ",
    "start ",
    "stop ",
    "add ",
    "set ",
    "enable ",
    "disable ",
    "show ",
    "list ",
    "delete ",
    "remove ",
    "create ",
    "plan ",
    "run ",
    "scan ",
    "detect ",
    "watch ",
    "sync ",
    "use ",
    "verify ",
    "trust ",
    "unlock ",
    "save ",
    "rename ",
    "reschedule ",
    "call ",
    "message ",
    "mail ",
    "send ",
    "wifi ",
    "wi-fi ",
    "wireless ",
    "bluetooth ",
    "blue tooth ",
    "blutooth ",
    "airplane ",
    "flight mode ",
    "energy saver ",
    "battery saver ",
    "power saver ",
    "night light ",
    "night mode ",
    "mobile hotspot ",
    "hotspot ",
    "nearby sharing ",
    "nearby share ",
    "live captions ",
    "live caption ",
    "accessibility ",
    "cast ",
    "project screen ",
    "second screen ",
    "projection mode ",
    "focus assist ",
    "do not disturb ",
    "camera ",
    "microphone ",
    "mic ",
    "voice status",
    "voice diagnostics",
    "weather",
    "forecast",
    "play ",
    "pause",
    "next ",
    "previous ",
    "tell ",
    "what ",
    "is ",
)

_ACTION_SPLIT_PATTERN = re.compile(
    r"\s*(?:,?\s+and then\s+|,?\s+then\s+|;\s*|,?\s+and\s+(?=(?:open|close|start|stop|play|pause|next|previous|add|set|show|list|tell|run|scan|detect|weather|forecast)\b))",
    re.IGNORECASE,
)


def looks_like_command_input(text: str) -> bool:
    cleaned = compact_text(text)
    lowered = cleaned.lower()
    if not cleaned:
        return False
    if len(cleaned) > 140:
        return False
    if lowered.endswith("?"):
        return False
    if lowered.startswith(("can you ", "could you ", "would you ", "how ", "why ", "explain ")):
        return False
    return lowered.startswith(_DIRECT_ACTION_PREFIXES)


def split_multi_step_command(command: str) -> list[str]:
    cleaned = compact_text(command)
    if not cleaned:
        return []
    parts = [compact_text(part) for part in _ACTION_SPLIT_PATTERN.split(cleaned) if compact_text(part)]
    if len(parts) <= 1:
        return [cleaned]
    if not all(looks_like_command_input(part) for part in parts):
        return [cleaned]
    return parts


def _capture_spoken_action(action, *, speaker_targets: list[tuple[Any, str]] | None = None) -> list[str]:
    spoken_messages: list[str] = []
    buffer = io.StringIO()
    speaker_targets = list(speaker_targets or [])
    speaker_targets.extend(
        [
            (legacy_command_router, "speak"),
            (voice_speak_module, "speak"),
        ]
    )
    originals: list[tuple[Any, str, Any]] = []

    def capture_speak(text, *args, **kwargs):
        cleaned = compact_text(text)
        if cleaned:
            spoken_messages.append(cleaned)

    for module, attribute in speaker_targets:
        try:
            originals.append((module, attribute, getattr(module, attribute)))
            setattr(module, attribute, capture_speak)
        except Exception:
            continue
    try:
        with contextlib.redirect_stdout(buffer):
            action()
    finally:
        for module, attribute, original in originals:
            setattr(module, attribute, original)

    if spoken_messages:
        return spoken_messages

    output = compact_text(buffer.getvalue())
    if output:
        return [output]

    return []


class WeatherCommandModule:
    name = "weather-module"

    def can_handle(self, request: ModuleRequest) -> bool:
        command = request.normalized_command
        if "weather popup" in command:
            return False
        return command.startswith(("weather", "forecast", "today weather", "weather today", "tell today weather", "tell the weather"))

    def handle(self, request: ModuleRequest) -> ModuleResult:
        reply = compact_text(get_weather_report(request.normalized_command)) or "I could not fetch weather right now."
        return ModuleResult(
            handled=True,
            ok=True,
            module=self.name,
            intent="weather",
            messages=[reply],
        )


class MediaCommandModule:
    name = "media-module"

    def can_handle(self, request: ModuleRequest) -> bool:
        command = request.normalized_command
        return command.startswith(("play", "pause", "next", "previous"))

    def handle(self, request: ModuleRequest) -> ModuleResult:
        messages = _capture_spoken_action(
            lambda: media_module.media_control(request.normalized_command),
            speaker_targets=[(media_module, "speak")],
        )
        if not messages:
            messages = ["Media command completed."]
        return ModuleResult(
            handled=True,
            ok=True,
            module=self.name,
            intent="media-control",
            messages=messages,
        )


class OpenAppCommandModule:
    name = "app-launch-module"

    def can_handle(self, request: ModuleRequest) -> bool:
        command = request.normalized_command
        if not command.startswith(("open ", "start ", "launch ")):
            return False
        for prefix in ("open ", "start ", "launch "):
            if command.startswith(prefix):
                target = compact_text(command.replace(prefix, "", 1)).lower()
                return target in DEFAULT_APP_COMMANDS
        return False

    def handle(self, request: ModuleRequest) -> ModuleResult:
        reply = compact_text(open_default_windows_app(request.normalized_command)) or "I could not open that app right now."
        return ModuleResult(
            handled=True,
            ok="could not" not in reply.lower(),
            module=self.name,
            intent="app-launch",
            messages=[reply],
        )


class LegacyCommandModule:
    name = "legacy-command-router"

    def can_handle(self, request: ModuleRequest) -> bool:
        return True

    def handle(self, request: ModuleRequest) -> ModuleResult:
        messages = _capture_spoken_action(
            lambda: legacy_command_router.process_command(
                request.normalized_command,
                request.installed_apps or {},
                input_mode=request.input_mode,
            )
        )
        if not messages:
            messages = ["Command completed."]
        return ModuleResult(
            handled=True,
            ok=True,
            module=self.name,
            intent="legacy-fallback",
            messages=messages,
        )


class UnifiedCommandRouter:
    def __init__(self, modules: list[CommandModule] | None = None):
        self.modules = modules or [
            WeatherCommandModule(),
            OpenAppCommandModule(),
            MediaCommandModule(),
            LegacyCommandModule(),
        ]

    def route(self, request: ModuleRequest) -> ModuleResult:
        for module in self.modules:
            try:
                if not module.can_handle(request):
                    continue
                result = module.handle(request)
                if result.handled:
                    return result
            except Exception as error:
                record_system_error(
                    "unified-command-router",
                    str(error),
                    metadata={
                        "module": getattr(module, "name", "unknown-module"),
                        "command": request.command,
                        "source": request.source,
                    },
                )
                return ModuleResult(
                    handled=True,
                    ok=False,
                    module=getattr(module, "name", "unknown-module"),
                    intent="error",
                    messages=[f"I hit a problem while handling that command: {error}"],
                    metadata={"error": str(error)},
                )
        return ModuleResult(
            handled=False,
            ok=False,
            module="unified-command-router",
            intent="unhandled",
            messages=["I could not find a handler for that command."],
        )

    def execute(self, command: str, *, installed_apps: dict[str, Any] | None = None, input_mode: str = "text", source: str = "command") -> ModuleResult:
        steps = split_multi_step_command(command)
        if len(steps) <= 1:
            return self.route(
                ModuleRequest(
                    command=command,
                    installed_apps=installed_apps,
                    input_mode=input_mode,
                    source=source,
                )
            )

        combined_messages: list[str] = []
        step_results: list[dict[str, Any]] = []
        overall_ok = True
        for step in steps:
            result = self.route(
                ModuleRequest(
                    command=step,
                    installed_apps=installed_apps,
                    input_mode=input_mode,
                    source=source,
                    metadata={"multi_step": True},
                )
            )
            overall_ok = overall_ok and result.ok
            combined_messages.extend(result.messages)
            step_results.append(asdict(result))
            if not result.ok:
                break
        return ModuleResult(
            handled=True,
            ok=overall_ok,
            module="unified-command-router",
            intent="multi-step",
            messages=combined_messages or ["Command completed."],
            metadata={"steps": step_results},
        )


ROUTER = UnifiedCommandRouter()


def execute_command(command: str, *, installed_apps: dict[str, Any] | None = None, input_mode: str = "text", source: str = "command") -> ModuleResult:
    return ROUTER.execute(
        command,
        installed_apps=installed_apps,
        input_mode=input_mode,
        source=source,
    )
