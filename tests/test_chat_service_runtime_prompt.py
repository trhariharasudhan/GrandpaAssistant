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
from core.runtime_prompt_adapter import RUNTIME_PROMPT_ENV


class ChatServiceRuntimePromptTests(unittest.TestCase):
    def setUp(self) -> None:
        chat_service.clear_all_chat_sessions_for_tests()
        self.previous_env = os.environ.pop(RUNTIME_PROMPT_ENV, None)
        self.local_patch = patch.object(chat_service, "answer_if_confident", return_value=None)
        self.local_patch.start()

    def tearDown(self) -> None:
        self.local_patch.stop()
        chat_service.clear_all_chat_sessions_for_tests()
        if self.previous_env is None:
            os.environ.pop(RUNTIME_PROMPT_ENV, None)
        else:
            os.environ[RUNTIME_PROMPT_ENV] = self.previous_env

    def test_legacy_prompt_used_when_flag_unset(self) -> None:
        legacy_prompt = chat_service._build_legacy_system_prompt()

        self.assertEqual(legacy_prompt, chat_service._build_system_prompt())

    def test_legacy_prompt_used_when_flag_off(self) -> None:
        os.environ[RUNTIME_PROMPT_ENV] = "0"
        legacy_prompt = chat_service._build_legacy_system_prompt()

        self.assertEqual(legacy_prompt, chat_service._build_system_prompt())

    def test_flag_off_keeps_legacy_prompt_for_coding_like_message(self) -> None:
        legacy_prompt = chat_service._build_legacy_system_prompt()

        self.assertEqual(legacy_prompt, chat_service._build_system_prompt("fix this python code"))

    def test_flag_off_keeps_legacy_prompt_with_memory_context(self) -> None:
        legacy_prompt = chat_service._build_legacy_system_prompt()

        self.assertEqual(
            legacy_prompt,
            chat_service._build_system_prompt("hi", memory_context="User likes private memory."),
        )

    def test_runtime_prompt_used_when_env_enabled(self) -> None:
        os.environ[RUNTIME_PROMPT_ENV] = "1"

        prompt = chat_service._build_system_prompt()

        self.assertIn("Default mode:", prompt)
        self.assertIn("Tool usage rules:", prompt)
        self.assertNotEqual(chat_service._build_legacy_system_prompt(), prompt)

    def test_prompt_metadata_flag_off_reports_legacy(self) -> None:
        prompt, metadata = chat_service._build_system_prompt_with_metadata("hi")

        self.assertEqual(chat_service._build_legacy_system_prompt(), prompt)
        self.assertEqual("legacy", metadata["source"])
        self.assertFalse(metadata["runtime_enabled"])

    def test_prompt_metadata_flag_on_reports_runtime_mode(self) -> None:
        os.environ[RUNTIME_PROMPT_ENV] = "1"

        prompt, metadata = chat_service._build_system_prompt_with_metadata("fix this python code")

        self.assertIn("Coding mode:", prompt)
        self.assertEqual("runtime", metadata["source"])
        self.assertEqual("coding", metadata["selected_mode"])
        self.assertEqual(len(prompt), metadata["prompt_length"])

    def test_prompt_metadata_fallback_does_not_expose_prompt_body(self) -> None:
        os.environ[RUNTIME_PROMPT_ENV] = "1"

        prompt, metadata = chat_service._build_system_prompt_with_metadata("hi")

        self.assertNotIn(prompt, str(metadata))
        self.assertIn("prompt_length", metadata)

    def test_runtime_prompt_can_include_sanitized_memory_context(self) -> None:
        os.environ[RUNTIME_PROMPT_ENV] = "1"

        prompt, metadata = chat_service._build_system_prompt_with_metadata(
            "hi",
            memory_context={"preference": "concise answers", "token": "do-not-include"},
        )

        self.assertIn("Memory context hints", prompt)
        self.assertIn("concise answers", prompt)
        self.assertNotIn("do-not-include", prompt)
        self.assertTrue(metadata["memory_context_included"])
        self.assertNotIn("concise answers", str(metadata))

    def test_provider_receives_legacy_prompt_by_default(self) -> None:
        seen_prompts = []

        def provider(_history, _message, **kwargs):
            seen_prompts.append(kwargs.get("system_prompt"))
            return "hello"

        chat_service.build_chat_reply("hi", session_id="runtime-default", provider=provider)

        self.assertEqual([chat_service._build_legacy_system_prompt()], seen_prompts)

    def test_provider_receives_runtime_prompt_when_enabled(self) -> None:
        os.environ[RUNTIME_PROMPT_ENV] = "yes"
        seen_prompts = []

        def provider(_history, _message, **kwargs):
            seen_prompts.append(kwargs.get("system_prompt"))
            return "hello"

        chat_service.build_chat_reply("hi", session_id="runtime-enabled", provider=provider)

        self.assertEqual(1, len(seen_prompts))
        self.assertIn("GrandpaAssistant", seen_prompts[0])
        self.assertIn("Default mode:", seen_prompts[0])

    def test_runtime_prompt_uses_coding_mode_for_coding_message(self) -> None:
        os.environ[RUNTIME_PROMPT_ENV] = "1"
        seen_prompts = []

        def provider(_history, _message, **kwargs):
            seen_prompts.append(kwargs.get("system_prompt"))
            return "fixed"

        chat_service.build_chat_reply("fix this python code", session_id="runtime-coding", provider=provider)

        self.assertEqual(1, len(seen_prompts))
        self.assertIn("Coding mode:", seen_prompts[0])
        self.assertNotIn("Default mode:", seen_prompts[0])

    def test_runtime_prompt_uses_default_mode_for_normal_message(self) -> None:
        os.environ[RUNTIME_PROMPT_ENV] = "1"
        seen_prompts = []

        def provider(_history, _message, **kwargs):
            seen_prompts.append(kwargs.get("system_prompt"))
            return "hello"

        chat_service.build_chat_reply("hi da how are you", session_id="runtime-normal", provider=provider)

        self.assertEqual(1, len(seen_prompts))
        self.assertIn("Default mode:", seen_prompts[0])
        self.assertNotIn("Coding mode:", seen_prompts[0])

    def test_runtime_prompt_does_not_use_planning_mode_for_planning_like_message(self) -> None:
        os.environ[RUNTIME_PROMPT_ENV] = "1"
        seen_prompts = []

        def provider(_history, _message, **kwargs):
            seen_prompts.append(kwargs.get("system_prompt"))
            return "plan noted"

        chat_service.build_chat_reply("make a plan for my day", session_id="runtime-planning-dormant", provider=provider)

        self.assertEqual(1, len(seen_prompts))
        self.assertIn("Default mode:", seen_prompts[0])
        self.assertNotIn("Planning mode:", seen_prompts[0])

    def test_adapter_failure_path_returns_legacy_prompt(self) -> None:
        os.environ[RUNTIME_PROMPT_ENV] = "on"
        legacy_prompt = chat_service._build_legacy_system_prompt()

        with patch("core.runtime_prompt_adapter.build_system_prompt", side_effect=RuntimeError("boom")):
            self.assertEqual(legacy_prompt, chat_service._build_system_prompt())

    def test_resolver_failure_falls_back_to_default_mode(self) -> None:
        os.environ[RUNTIME_PROMPT_ENV] = "1"

        with patch.object(chat_service, "resolve_prompt_mode", side_effect=RuntimeError("boom")):
            prompt = chat_service._build_system_prompt("fix this python code")

        self.assertIn("Default mode:", prompt)
        self.assertNotIn("Coding mode:", prompt)

    def test_command_router_behavior_not_changed_by_prompt_flag(self) -> None:
        os.environ[RUNTIME_PROMPT_ENV] = "1"

        result = chat_service.detect_explicit_chat_route("open notepad")

        self.assertEqual({"route": "chat"}, result)

    def test_no_reference_prompt_dependency(self) -> None:
        source = (APP_DIR / "core" / "chat_service.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
