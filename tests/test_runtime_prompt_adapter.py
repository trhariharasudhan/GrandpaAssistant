import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from core.runtime_prompt_adapter import (
    RUNTIME_PROMPT_ENV,
    SAFE_MINIMAL_SYSTEM_PROMPT,
    get_runtime_system_prompt,
    get_runtime_system_prompt_with_metadata,
)


class RuntimePromptAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_env = os.environ.pop(RUNTIME_PROMPT_ENV, None)

    def tearDown(self) -> None:
        if self.previous_env is None:
            os.environ.pop(RUNTIME_PROMPT_ENV, None)
        else:
            os.environ[RUNTIME_PROMPT_ENV] = self.previous_env

    def test_old_behavior_remains_default(self) -> None:
        prompt = get_runtime_system_prompt(fallback_prompt="legacy prompt")

        self.assertEqual("legacy prompt", prompt)

    def test_default_without_fallback_uses_safe_minimal_prompt(self) -> None:
        prompt = get_runtime_system_prompt()

        self.assertEqual(SAFE_MINIMAL_SYSTEM_PROMPT, prompt)

    def test_runtime_prompt_used_when_flag_argument_enabled(self) -> None:
        prompt = get_runtime_system_prompt("coding", use_runtime_prompts=True, fallback_prompt="legacy prompt")

        self.assertIn("GrandpaAssistant", prompt)
        self.assertIn("Coding mode:", prompt)
        self.assertNotEqual("legacy prompt", prompt)

    def test_env_var_enables_runtime_prompt(self) -> None:
        os.environ[RUNTIME_PROMPT_ENV] = "yes"

        prompt = get_runtime_system_prompt("voice", fallback_prompt="legacy prompt")

        self.assertIn("Voice mode:", prompt)

    def test_invalid_mode_falls_back_safely(self) -> None:
        prompt = get_runtime_system_prompt("bad-mode", use_runtime_prompts=True, fallback_prompt="legacy prompt")

        self.assertEqual("legacy prompt", prompt)

    def test_builder_failure_returns_fallback_prompt(self) -> None:
        with patch("core.runtime_prompt_adapter.build_system_prompt", side_effect=RuntimeError("boom")):
            prompt = get_runtime_system_prompt("default", use_runtime_prompts=True, fallback_prompt="legacy prompt")

        self.assertEqual("legacy prompt", prompt)

    def test_metadata_flag_off_returns_legacy_source(self) -> None:
        prompt, metadata = get_runtime_system_prompt_with_metadata(fallback_prompt="legacy prompt")

        self.assertEqual("legacy prompt", prompt)
        self.assertEqual("legacy", metadata["source"])
        self.assertFalse(metadata["runtime_enabled"])
        self.assertTrue(metadata["fallback_used"])

    def test_metadata_flag_on_returns_runtime_source(self) -> None:
        prompt, metadata = get_runtime_system_prompt_with_metadata(
            "coding",
            use_runtime_prompts=True,
            fallback_prompt="legacy prompt",
        )

        self.assertIn("Coding mode:", prompt)
        self.assertEqual("runtime", metadata["source"])
        self.assertTrue(metadata["runtime_enabled"])
        self.assertFalse(metadata["fallback_used"])
        self.assertFalse(metadata["memory_context_included"])
        self.assertEqual(len(prompt), metadata["prompt_length"])

    def test_memory_context_metadata_boolean_has_no_memory_text(self) -> None:
        prompt, metadata = get_runtime_system_prompt_with_metadata(
            "default",
            use_runtime_prompts=True,
            fallback_prompt="legacy prompt",
            memory_context="User likes private memory.",
        )

        self.assertIn("Memory context:", prompt)
        self.assertTrue(metadata["memory_context_included"])
        self.assertNotIn("private memory", str(metadata))

    def test_metadata_fallback_path_marks_fallback_used(self) -> None:
        with patch("core.runtime_prompt_adapter.build_system_prompt", side_effect=RuntimeError("boom")):
            prompt, metadata = get_runtime_system_prompt_with_metadata(
                "default",
                use_runtime_prompts=True,
                fallback_prompt="legacy prompt",
            )

        self.assertEqual("legacy prompt", prompt)
        self.assertEqual("legacy", metadata["source"])
        self.assertTrue(metadata["fallback_used"])
        self.assertEqual("runtime_prompt_build_failed", metadata["reason"])

    def test_metadata_excludes_prompt_body(self) -> None:
        prompt, metadata = get_runtime_system_prompt_with_metadata(
            "default",
            use_runtime_prompts=True,
            fallback_prompt="legacy prompt",
        )

        self.assertNotIn(prompt, str(metadata))
        self.assertIn("prompt_length", metadata)

    def test_no_reference_prompt_path_is_used(self) -> None:
        adapter_path = ROOT / "backend" / "app" / "core" / "runtime_prompt_adapter.py"
        source = adapter_path.read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))

    def test_optional_export_from_core_prompts(self) -> None:
        from core import prompts

        self.assertTrue(callable(prompts.get_runtime_system_prompt))


if __name__ == "__main__":
    unittest.main()
