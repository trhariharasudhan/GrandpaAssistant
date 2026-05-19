import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
for path in [APP_DIR, SHARED_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from core import chat_service
from core.personal_assistant.context import clear_personal_assistant_contexts_for_tests, get_conversation_context
from core.personal_assistant.intent_engine import IntentCandidate, detect_intent
from core.personal_assistant.planner import build_action_plan
from core.personal_assistant.service import handle_personal_assistant_message
from core.personal_assistant import executor
from core.personal_assistant.tool_registry import (
    LocalAssistantTool,
    execute_registered_tool,
    explain_missing_tool,
    list_available_tools,
    list_tools_by_intent,
    validate_tool_parameters,
)
from core.personal_assistant import tool_registry


class PersonalAssistantToolRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_personal_assistant_contexts_for_tests()
        chat_service.clear_all_chat_sessions_for_tests()
        self.previous_debug = os.environ.pop(chat_service.PERSONAL_ASSISTANT_DEBUG_ENV, None)

    def tearDown(self) -> None:
        clear_personal_assistant_contexts_for_tests()
        chat_service.clear_all_chat_sessions_for_tests()
        if self.previous_debug is None:
            os.environ.pop(chat_service.PERSONAL_ASSISTANT_DEBUG_ENV, None)
        else:
            os.environ[chat_service.PERSONAL_ASSISTANT_DEBUG_ENV] = self.previous_debug

    def test_registry_lists_current_action_tools(self) -> None:
        tools = {item["tool_name"]: item for item in list_available_tools()}

        for expected in {
            "volume_control",
            "open_app",
            "close_tracked_app",
            "system_diagnostics",
            "create_reminder",
            "list_reminders",
            "complete_reminder",
            "cancel_reminder",
            "check_due_reminders",
            "startup_status",
            "enable_startup",
            "disable_startup",
            "voice_runtime_status",
            "enable_voice_runtime",
            "disable_voice_runtime",
            "remember_this",
            "list_memories",
            "forget_memory",
            "memory_status",
            "memory_opt_out",
            "review_memories",
            "cleanup_memories",
            "update_memory",
            "memory_conflicts",
            "create_task",
            "active_window_context",
            "screen_read",
            "media_key_control",
            "open_website",
            "search_selected_google",
            "create_folder",
        }:
            self.assertIn(expected, tools)
            self.assertIn("risk_level", tools[expected])
            self.assertIn("permission_requirement", tools[expected])

    def test_registry_finds_tools_by_intent_and_capability(self) -> None:
        by_intent = list_tools_by_intent("adjust_volume")
        by_capability = list_tools_by_intent("audio")

        self.assertEqual("volume_control", by_intent[0]["tool_name"])
        self.assertTrue(any(item["tool_name"] == "volume_control" for item in by_capability))

    def test_planner_selects_registered_tool_for_generalized_volume_intents(self) -> None:
        for message in ["reduce volume", "sound kammi pannu", "increase volume"]:
            candidate = detect_intent(message)
            plan = build_action_plan(candidate, get_conversation_context(message), message)

            self.assertIsNotNone(plan)
            self.assertEqual("adjust_volume", plan.intent)
            self.assertEqual("volume_control", plan.tool_name)
            self.assertFalse(plan.missing_details)

    def test_missing_required_params_are_reported_by_registry(self) -> None:
        validation = validate_tool_parameters("open_app", {})
        result = execute_registered_tool("open_app", {})

        self.assertFalse(validation["ok"])
        self.assertEqual(["app"], validation["missing_parameters"])
        self.assertFalse(result["ok"])
        self.assertIn("needs: app", result["message"])

    def test_unavailable_tool_gives_clear_adapter_missing_response(self) -> None:
        original = tool_registry._TOOLS["volume_control"]
        tool_registry._TOOLS["volume_control"] = LocalAssistantTool(
            tool_name=original.tool_name,
            description=original.description,
            supported_intents=original.supported_intents,
            capabilities=original.capabilities,
            required_parameters=original.required_parameters,
            optional_parameters=original.optional_parameters,
            risk_level=original.risk_level,
            permission_requirement=original.permission_requirement,
            confirmation_required=original.confirmation_required,
            platform_support=original.platform_support,
            availability_check=lambda: False,
            executor=original.executor,
            safe_failure_message="Volume adapter is not available in this environment.",
        )
        try:
            result = execute_registered_tool("volume_control", {"operation": "decrease"})
        finally:
            tool_registry._TOOLS["volume_control"] = original

        self.assertFalse(result["ok"])
        self.assertIn("Volume adapter is not available", result["message"])
        self.assertEqual("volume_control", result["data"]["missing_adapter"])

    def test_unsafe_or_unsupported_action_is_blocked_through_registry_path(self) -> None:
        candidate = detect_intent("delete all my project files")
        plan = build_action_plan(candidate, get_conversation_context("unsafe"), "delete all my project files")
        result = executor.execute_plan(plan, get_conversation_context("unsafe"))  # type: ignore[arg-type]

        self.assertEqual("unsupported_action", candidate.intent)
        self.assertEqual("unsupported_action", plan.tool_name)  # type: ignore[union-attr]
        self.assertEqual("BLOCKED", plan.risk_level)  # type: ignore[union-attr]
        self.assertFalse(result["ok"])
        self.assertIn("safe registered adapter", result["reply"])

    def test_capability_discovery_uses_registry_not_provider_fallback(self) -> None:
        result = handle_personal_assistant_message("what can you do", session_id="capabilities")

        self.assertTrue(result["handled"])
        self.assertTrue(result["executed"])
        self.assertEqual("capability_discovery", result["intent"])
        self.assertIn("registered local tools", result["reply"])

    def test_debug_metadata_includes_selected_tool_and_executor_status(self) -> None:
        os.environ[chat_service.PERSONAL_ASSISTANT_DEBUG_ENV] = "1"
        with patch.object(
            executor.local_action_executor,
            "execute_local_action",
            return_value={"ok": True, "message": "Reduced the system volume.", "data": {"operation": "decrease"}},
        ):
            result = chat_service.build_chat_reply("lower sound", session_id="registry-debug", provider=lambda *_args, **_kwargs: "fallback")

        metadata = result["debug"]
        self.assertEqual("volume_control", metadata["selected_tool"])
        self.assertTrue(metadata["tool_availability"]["available"])
        self.assertEqual("volume_control", metadata["executor_result"]["tool"])

    def test_missing_tool_explanation_is_specific(self) -> None:
        explanation = explain_missing_tool("send WhatsApp message")

        self.assertIn("send WhatsApp message", explanation["message"])
        self.assertIn("safe registered adapter", explanation["message"])


if __name__ == "__main__":
    unittest.main()
