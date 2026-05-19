from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
for path in (str(ROOT), str(APP_DIR), str(SHARED_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from core import chat_service
from core.personal_assistant import executor, llm_planner, memory_manager, reminder_engine, reminder_scheduler, service, voice_runtime, windows_startup_manager
from core.personal_assistant.tool_registry import list_tools_by_intent


class FlowFailure(AssertionError):
    pass


def compact_text(value: Any, limit: int = 140) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


def screen_context(activity: str = "browsing") -> dict[str, Any]:
    return {
        "active_window": {
            "ok": True,
            "app_name": "Mock Browser",
            "title": "Mock page",
            "kind": "browser",
            "domain": "example.test",
            "activity": activity,
        },
        "screen_context": {"activity": activity, "source": "mock"},
        "screenshot": None,
    }


class PersonalAssistantE2ERunner:
    def __init__(
        self,
        *,
        real_volume: bool = False,
        real_apps: bool = False,
        real_screen: bool = False,
        enable_llm_planner: bool = False,
        scheduler_once: bool = False,
    ) -> None:
        self.real_volume = real_volume
        self.real_apps = real_apps
        self.real_screen = real_screen
        self.enable_llm_planner = enable_llm_planner
        self.scheduler_once = scheduler_once
        self.task_payload: dict[str, list[dict[str, Any]]] = {"tasks": [], "reminders": []}
        self.startup_enabled = False
        self.voice_enabled = False
        self.action_calls: list[dict[str, Any]] = []
        self.results: list[dict[str, Any]] = []

    def run(self) -> list[dict[str, Any]]:
        chat_service.clear_all_chat_sessions_for_tests()
        with ExitStack() as stack:
            self._install_safe_mocks(stack)
            for name, flow in self.flows():
                self._run_flow(name, flow)
            if self.scheduler_once:
                self._run_flow("scheduler one tick", self.flow_scheduler_once)
        return list(self.results)

    def flows(self) -> list[tuple[str, Callable[[], None]]]:
        return [
            ("normal greeting", self.flow_greeting),
            ("normal chat fallback", self.flow_normal_chat_fallback),
            ("volume decrease", self.flow_volume_decrease),
            ("reminder missing details then completion", self.flow_reminder_completion),
            ("laptop diagnostics follow-up", self.flow_diagnostics_follow_up),
            ("open calculator then close it", self.flow_open_close_calculator),
            ("screen read request", self.flow_screen_read),
            ("unsupported action explanation", self.flow_unsupported_action),
            ("dangerous action block", self.flow_dangerous_action),
            ("windows startup opt in", self.flow_windows_startup),
            ("voice wake command", self.flow_voice_wake_command),
            ("long-term memory", self.flow_long_term_memory),
            ("capability discovery", self.flow_capability_discovery),
        ]

    def _install_safe_mocks(self, stack: ExitStack) -> None:
        memory_dir = stack.enter_context(tempfile.TemporaryDirectory())
        stack.enter_context(patch.dict(os.environ, {memory_manager.MEMORY_PATH_ENV: str(Path(memory_dir) / "memory.json")}))
        stack.enter_context(patch.object(chat_service, "answer_if_confident", return_value=None))
        stack.enter_context(patch.object(executor, "load_task_payload", side_effect=lambda default_factory=None: self.task_payload))
        stack.enter_context(patch.object(executor, "save_task_payload", side_effect=self._save_task_payload))
        stack.enter_context(patch.object(reminder_engine, "load_task_payload", side_effect=lambda default_factory=None: self.task_payload))
        stack.enter_context(patch.object(reminder_engine, "save_task_payload", side_effect=self._save_task_payload))
        stack.enter_context(patch.object(windows_startup_manager, "startup_status", side_effect=self._fake_startup_status))
        stack.enter_context(patch.object(windows_startup_manager, "enable_startup", side_effect=self._fake_enable_startup))
        stack.enter_context(patch.object(windows_startup_manager, "disable_startup", side_effect=self._fake_disable_startup))
        stack.enter_context(patch.object(voice_runtime, "get_voice_runtime_status", side_effect=self._fake_voice_status))
        stack.enter_context(patch.object(voice_runtime, "enable_voice_runtime", side_effect=self._fake_enable_voice))
        stack.enter_context(patch.object(voice_runtime, "disable_voice_runtime", side_effect=self._fake_disable_voice))
        if not self.enable_llm_planner:
            stack.enter_context(patch.object(llm_planner, "generate_llm_plan_text", side_effect=RuntimeError("LLM planner disabled for e2e mock mode.")))
        if not self.real_screen:
            mock_screen = screen_context()
            stack.enter_context(patch.object(service, "get_screen_context", return_value=mock_screen))
            stack.enter_context(
                patch.object(
                    executor.screen_context_module,
                    "get_screen_context",
                    return_value={
                        **mock_screen,
                        "screenshot": {"ok": True, "summary": "Mock screen text: build failed with Error 500.", "line_count": 1, "error_like": True},
                    },
                )
            )
        if not (self.real_volume and self.real_apps):
            stack.enter_context(patch.object(executor.local_action_executor, "execute_local_action", side_effect=self._fake_local_action))

    def _fake_local_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        action = str((payload or {}).get("action") or "")
        params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
        self.action_calls.append({"action": action, "params": dict(params)})
        if action == "adjust_volume":
            return {"ok": True, "action": action, "message": "Reduced the system volume.", "data": {"operation": params.get("operation")}}
        if action == "open_app":
            return {"ok": True, "action": action, "message": f"Opened {params.get('app')}.", "data": {"app": params.get("app"), "pid": 4242}}
        if action == "close_app":
            return {"ok": True, "action": action, "message": f"Closed {params.get('app')}.", "data": {"app": params.get("app"), "pid": params.get("pid")}}
        if action == "media_key":
            return {"ok": True, "action": action, "message": "Paused or resumed media playback.", "data": {"operation": params.get("operation")}}
        if action == "open_url":
            return {"ok": True, "action": action, "message": "Opened URL.", "data": {"url": params.get("url")}}
        if action == "create_folder":
            return {"ok": True, "action": action, "message": "Folder is ready.", "data": {"path": params.get("path")}}
        return {"ok": False, "action": action, "message": f"Mock local action does not support {action}.", "data": {}}

    def _save_task_payload(self, payload: dict[str, Any], default_factory=None) -> None:
        self.task_payload = payload

    def _fake_startup_status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "enabled": self.startup_enabled,
            "startup_method": "windows_startup_folder_cmd",
            "startup_entry": "mock-startup.cmd",
            "entrypoint": "backend/main.py",
            "message": "GrandpaAssistant Windows startup is enabled." if self.startup_enabled else "GrandpaAssistant Windows startup is disabled.",
        }

    def _fake_enable_startup(self) -> dict[str, Any]:
        self.startup_enabled = True
        return {"ok": True, "enabled": True, "startup_entry": "mock-startup.cmd", "message": "GrandpaAssistant Windows startup enabled."}

    def _fake_disable_startup(self) -> dict[str, Any]:
        self.startup_enabled = False
        return {"ok": True, "enabled": False, "startup_entry": "mock-startup.cmd", "message": "GrandpaAssistant Windows startup disabled."}

    def _fake_voice_status(self) -> dict[str, Any]:
        return {
            "enabled": self.voice_enabled,
            "running": self.voice_enabled,
            "wake_word": "Grandpa",
            "stt_provider": {"available": True, "resolved_backend": "mock"},
            "last_transcript": "",
            "last_command": "",
        }

    def _fake_enable_voice(self) -> dict[str, Any]:
        self.voice_enabled = True
        return {"ok": True, "enabled": True, "running": True, "message": "Voice runtime enabled and listening for the wake word."}

    def _fake_disable_voice(self) -> dict[str, Any]:
        self.voice_enabled = False
        return {"ok": True, "enabled": False, "running": False, "message": "Voice runtime disabled."}

    def _run_flow(self, name: str, flow: Callable[[], None]) -> None:
        try:
            flow()
            self.results.append({"flow": name, "status": "PASS", "warning": ""})
        except Exception as error:
            self.results.append({"flow": name, "status": "FAIL", "warning": compact_text(error, 300)})

    def chat(self, message: str, *, session_id: str, provider: Callable[..., str] | None = None) -> dict[str, Any]:
        return chat_service.build_chat_reply(
            message,
            session_id=session_id,
            provider=provider or (lambda *_args, **_kwargs: "mock provider fallback"),
        )

    def expect(self, condition: bool, message: str) -> None:
        if not condition:
            raise FlowFailure(message)

    def record_turn(self, flow: str, response: dict[str, Any]) -> None:
        debug_tool = ((response.get("debug") or {}).get("selected_tool") if isinstance(response.get("debug"), dict) else "")
        registry_tools = list_tools_by_intent(str(response.get("intent") or ""))
        inferred_tool = registry_tools[0]["tool_name"] if registry_tools else ""
        self.results.append(
            {
                "flow": flow,
                "status": "INFO",
                "intent": response.get("intent", ""),
                "tool": debug_tool or inferred_tool,
                "reply": compact_text(response.get("reply")),
            }
        )

    def flow_greeting(self) -> None:
        response = self.chat("Hi", session_id="e2e-greeting", provider=lambda *_args, **_kwargs: "Hi da! Enna help venum?")
        self.expect(response.get("provider") != "personal-assistant", "Greeting should not trigger an action.")
        self.expect("debug" not in response, "Normal mode leaked debug metadata.")
        self.record_turn("normal greeting", response)

    def flow_normal_chat_fallback(self) -> None:
        response = self.chat("Tell me a joke", session_id="e2e-joke", provider=lambda *_args, **_kwargs: "Here is a short joke.")
        self.expect(response.get("provider") != "personal-assistant", "Joke should use chat fallback.")
        self.expect("debug" not in response, "Normal mode leaked debug metadata.")
        self.record_turn("normal chat fallback", response)

    def flow_volume_decrease(self) -> None:
        response = self.chat("Laptop sound kammi pannu", session_id="e2e-volume")
        self.expect(response.get("intent") == "adjust_volume", "Volume intent not detected.")
        self.expect(response.get("executed"), "Volume action did not execute in mock mode.")
        self.expect(any(call["action"] == "adjust_volume" for call in self.action_calls), "Volume adapter was not called.")
        self.record_turn("volume decrease", response)

    def flow_reminder_completion(self) -> None:
        first = self.chat("I have a meeting tomorrow morning", session_id="e2e-reminder")
        self.expect(first.get("intent") == "meeting_reminder", "Meeting intent not detected.")
        self.expect("meeting_time_topic" in first.get("missing_details", []), "Meeting missing details were not requested.")
        second = self.chat("10 AM project discussion", session_id="e2e-reminder")
        self.expect(second.get("executed"), "Meeting reminder was not completed.")
        self.expect(bool(self.task_payload.get("reminders")), "Structured reminder was not stored.")
        listed = self.chat("show pending reminders", session_id="e2e-reminder")
        self.expect(listed.get("intent") == "list_reminders", "Pending reminders were not listed.")
        self.expect("project discussion" in listed.get("reply", "").lower(), "Pending reminder list did not include stored meeting.")
        due_at = reminder_engine.parse_reminder_datetime(self.task_payload["reminders"][0].get("due_at"))
        self.expect(due_at is not None, "Stored reminder did not have a due time.")
        due = reminder_engine.check_due_reminders(
            now=due_at,
            notifier=lambda reminder: {"ok": True, "channel": "mock", "message": f"Reminder: {reminder.get('title')}."},
            load_payload=lambda default_factory=None: self.task_payload,
            save_payload=self._save_task_payload,
        )
        self.expect(due.get("notification_count") == 1, "Due reminder was not surfaced in mock mode.")
        done = self.chat("mark project discussion reminder done", session_id="e2e-reminder")
        self.expect(done.get("intent") == "complete_reminder", "Reminder completion intent not detected.")
        self.expect(any(item.get("status") == "done" for item in self.task_payload.get("reminders", [])), "Reminder was not marked done.")
        self.chat("remind me in 10 minutes to drink water", session_id="e2e-reminder-cancel")
        cancelled = self.chat("cancel drink water reminder", session_id="e2e-reminder-cancel")
        self.expect(cancelled.get("intent") == "cancel_reminder", "Reminder cancellation intent not detected.")
        self.expect(any(item.get("status") == "cancelled" for item in self.task_payload.get("reminders", [])), "Reminder was not cancelled.")
        self.record_turn("reminder missing details then completion", second)

    def flow_diagnostics_follow_up(self) -> None:
        first = self.chat("My laptop is slow", session_id="e2e-diagnostics")
        second = self.chat("Check everything", session_id="e2e-diagnostics")
        self.expect(first.get("intent") == "system_diagnostics", "Slow laptop did not map to diagnostics.")
        self.expect(second.get("intent") == "system_diagnostics", "Follow-up did not resolve to diagnostics.")
        self.expect("CPU usage" in second.get("reply", "") or "not available" in second.get("reply", ""), "Diagnostics summary missing metric category.")
        self.record_turn("laptop diagnostics follow-up", second)

    def flow_open_close_calculator(self) -> None:
        first = self.chat("Open calculator", session_id="e2e-calculator")
        self.expect(first.get("requires_confirmation"), "Opening calculator should request confirmation.")
        opened = self.chat("yes", session_id="e2e-calculator")
        self.expect(opened.get("executed"), "Calculator open did not execute.")
        confirm_close = self.chat("close it", session_id="e2e-calculator")
        if confirm_close.get("requires_confirmation"):
            closed = self.chat("yes", session_id="e2e-calculator")
        else:
            closed = confirm_close
        self.expect(closed.get("executed"), "Calculator close did not execute.")
        self.expect(any(call["action"] == "close_app" for call in self.action_calls), "Close adapter was not called.")
        self.record_turn("open calculator then close it", closed)

    def flow_screen_read(self) -> None:
        response = self.chat("read this error", session_id="e2e-screen")
        self.expect(response.get("intent") == "screen_read", "Screen read intent not detected.")
        self.expect(response.get("executed"), "Screen read did not execute in mock mode.")
        self.expect("Mock screen text" in response.get("reply", ""), "Mock OCR summary was not returned.")
        self.record_turn("screen read request", response)

    def flow_unsupported_action(self) -> None:
        response = self.chat("send WhatsApp message to Ravi", session_id="e2e-unsupported")
        self.expect(response.get("intent") == "unsupported_action", "Unsupported communication intent was not detected.")
        self.expect(not response.get("ok"), "Unsupported action should not be ok.")
        self.expect(response.get("missing_adapter"), "Missing adapter was not reported.")
        self.record_turn("unsupported action explanation", response)

    def flow_dangerous_action(self) -> None:
        response = self.chat("delete all project files", session_id="e2e-danger")
        self.expect(response.get("intent") == "unsupported_action", "Dangerous action was not routed to blocked/unsupported.")
        self.expect(not response.get("ok"), "Dangerous action should be blocked.")
        self.record_turn("dangerous action block", response)

    def flow_windows_startup(self) -> None:
        status = self.chat("check startup status", session_id="e2e-startup")
        self.expect(status.get("intent") == "startup_status", "Startup status intent not detected.")
        first = self.chat("enable startup", session_id="e2e-startup")
        self.expect(first.get("requires_confirmation"), "Startup enable should require explicit confirmation.")
        enabled = self.chat("yes", session_id="e2e-startup")
        self.expect(enabled.get("executed"), "Startup enable did not execute after confirmation.")
        self.expect(self.startup_enabled, "Mock startup was not enabled.")
        disabled = self.chat("stop opening on startup", session_id="e2e-startup")
        self.expect(disabled.get("executed"), "Startup disable did not execute.")
        self.expect(not self.startup_enabled, "Mock startup was not disabled.")
        self.record_turn("windows startup opt in", disabled)

    def flow_voice_wake_command(self) -> None:
        status = self.chat("is voice mode running?", session_id="e2e-voice")
        self.expect(status.get("intent") == "voice_runtime_status", "Voice status intent not detected.")
        first = self.chat("enable voice mode", session_id="e2e-voice")
        self.expect(first.get("requires_confirmation"), "Voice runtime enable should require confirmation.")
        enabled = self.chat("yes", session_id="e2e-voice")
        self.expect(enabled.get("executed"), "Voice runtime enable did not execute after confirmation.")
        self.expect(self.voice_enabled, "Mock voice runtime was not enabled.")
        spoken = []
        manager = voice_runtime.VoiceRuntimeManager(
            adapters=voice_runtime.VoiceRuntimeAdapters(
                listen_for_wake=lambda: "Hey Grandpa reduce volume",
                listen_for_command=lambda: "",
                speak=lambda text: spoken.append(text),
                handle_command=lambda command: self.chat(command, session_id="e2e-voice-command"),
                stt_status=lambda: {"available": True, "resolved_backend": "mock"},
            ),
            idle_sleep_seconds=0.01,
        )
        result = manager.run_once()
        self.expect(result.get("handled"), "Mock wake command was not handled.")
        self.expect(any(call["action"] == "adjust_volume" for call in self.action_calls), "Voice wake command did not reach assistant action path.")
        self.expect(bool(spoken), "Voice runtime did not send response to speech output adapter.")
        disabled = self.chat("disable voice mode", session_id="e2e-voice")
        self.expect(disabled.get("executed"), "Voice runtime disable did not execute.")
        self.record_turn("voice wake command", disabled)

    def flow_long_term_memory(self) -> None:
        remember = self.chat("remember that I usually use VS Code for coding", session_id="e2e-memory")
        self.expect(remember.get("intent") == "remember_this", "Explicit memory intent not detected.")
        self.expect(remember.get("executed"), "Explicit memory was not stored.")
        conflict = self.chat("I use Cursor for coding", session_id="e2e-memory")
        self.expect(conflict.get("intent") == "remember_this", "Uncertain memory conflict intent not detected.")
        self.expect(not conflict.get("ok"), "Uncertain memory conflict should ask for confirmation.")
        self.expect("Should I update" in conflict.get("reply", ""), "Memory conflict confirmation was not requested.")
        updated = self.chat("yes", session_id="e2e-memory")
        self.expect(updated.get("intent") == "resolve_memory_conflict", "Memory conflict follow-up was not routed to resolver.")
        self.expect(updated.get("executed"), "Pending memory conflict was not resolved.")
        editor = self.chat("open my editor", session_id="e2e-memory-editor")
        self.expect(editor.get("requires_confirmation") or editor.get("executed"), "Saved preferred editor was not used for planning.")
        self.expect("Cursor" in editor.get("reply", "") or editor.get("intent") == "open_app", "Open editor flow did not use updated preference.")
        implicit = self.chat("I prefer dark mode", session_id="e2e-memory")
        self.expect(implicit.get("intent") == "remember_this", "Implicit preference was not learned.")
        review = self.chat("review my memories", session_id="e2e-memory")
        self.expect(review.get("intent") == "review_memories", "Memory review intent not detected.")
        cleanup = self.chat("clean old memories", session_id="e2e-memory")
        self.expect(cleanup.get("intent") == "cleanup_memories", "Memory cleanup intent not detected.")
        listed = self.chat("what do you remember about me?", session_id="e2e-memory")
        self.expect(listed.get("intent") == "list_memories", "Memory recall intent not detected.")
        self.expect("Cursor" in listed.get("reply", "") or "preferred code editor" in listed.get("reply", ""), "Updated editor preference was not recalled.")
        forgotten = self.chat("forget preferred code editor memory", session_id="e2e-memory")
        self.expect(forgotten.get("intent") == "forget_memory", "Forget memory intent not detected.")
        self.expect(forgotten.get("executed"), "Memory was not forgotten.")
        after = self.chat("what do you remember about me?", session_id="e2e-memory")
        self.expect("Cursor" not in after.get("reply", ""), "Forgotten memory still appeared in recall.")
        self.record_turn("long-term memory", after)

    def flow_capability_discovery(self) -> None:
        response = self.chat("what can you do?", session_id="e2e-capabilities")
        self.expect(response.get("intent") == "capability_discovery", "Capability discovery intent not detected.")
        self.expect(response.get("executed"), "Capability discovery did not execute.")
        self.expect("registered local tools" in response.get("reply", ""), "Capability reply did not use registry summary.")
        self.record_turn("capability discovery", response)

    def flow_scheduler_once(self) -> None:
        scheduler = reminder_scheduler.ReminderScheduler(
            check_due=lambda: reminder_engine.check_due_reminders(
                load_payload=lambda default_factory=None: self.task_payload,
                save_payload=self._save_task_payload,
                notifier=lambda reminder: {"ok": True, "channel": "mock", "message": f"Reminder: {reminder.get('title')}."},
            ),
            interval_seconds=0.01,
        )
        result = scheduler.run_once()
        self.expect(isinstance(result, dict), "Scheduler one-tick result was not a dict.")
        self.record_turn("scheduler one tick", {"intent": "check_due_reminders", "reply": result.get("message", ""), "debug": {"selected_tool": "check_due_reminders"}})


def run_e2e(args: argparse.Namespace) -> tuple[int, list[dict[str, Any]]]:
    runner = PersonalAssistantE2ERunner(
        real_volume=args.real_volume,
        real_apps=args.real_apps,
        real_screen=args.real_screen,
        enable_llm_planner=args.enable_llm_planner,
        scheduler_once=args.scheduler_once,
    )
    results = runner.run()
    failures = [item for item in results if item["status"] == "FAIL"]
    return (1 if failures else 0), results


def print_report(results: list[dict[str, Any]], *, compact: bool = False) -> None:
    if compact:
        print(json.dumps(results, indent=2))
        return
    print("GrandpaAssistant Personal Assistant E2E")
    for item in results:
        if item["status"] == "INFO":
            print(f"  [INFO] {item['flow']} intent={item.get('intent','')} tool={item.get('tool','')} reply={item.get('reply','')}")
        else:
            suffix = f" - {item['warning']}" if item.get("warning") else ""
            print(f"  [{item['status']}] {item['flow']}{suffix}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run GrandpaAssistant personal-assistant e2e conversation flows.")
    parser.add_argument("--real-volume", action="store_true", help="Allow real system volume changes.")
    parser.add_argument("--real-apps", action="store_true", help="Allow real app open/close actions.")
    parser.add_argument("--real-screen", action="store_true", help="Allow real screenshot/OCR screen reading.")
    parser.add_argument("--enable-llm-planner", action="store_true", help="Allow real LLM planner provider calls.")
    parser.add_argument("--scheduler-once", action="store_true", help="Run one mocked reminder scheduler tick without waiting.")
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    code, results = run_e2e(args)
    print_report(results, compact=args.json)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
