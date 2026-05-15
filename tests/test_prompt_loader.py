import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from core.prompt_loader import list_available_prompts, load_prompt, prompt_exists
from core.prompt_modes import is_supported_mode, list_supported_modes, validate_mode


class PromptLoaderTests(unittest.TestCase):
    def test_prompt_loading_works(self) -> None:
        prompt = load_prompt("base/core.txt")

        self.assertIn("GrandpaAssistant", prompt)
        self.assertIn("local-first", prompt)

    def test_missing_prompt_is_safe(self) -> None:
        prompt = load_prompt("missing/nope.txt")

        self.assertEqual("", prompt)

    def test_path_escape_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            load_prompt("../prompt_research/README.md")

    def test_prompt_exists(self) -> None:
        self.assertTrue(prompt_exists("modes/coding.txt"))
        self.assertTrue(prompt_exists("modes/planning.txt"))
        self.assertFalse(prompt_exists("modes/not-real.txt"))

    def test_list_available_prompts(self) -> None:
        prompts = list_available_prompts()

        self.assertIn("base/core.txt", prompts)
        self.assertIn("tools/tool_rules.txt", prompts)
        self.assertIn("modes/planning.txt", prompts)

    def test_supported_modes_validate(self) -> None:
        self.assertTrue(is_supported_mode("coding"))
        self.assertTrue(is_supported_mode("automation"))
        self.assertTrue(is_supported_mode("planning"))
        self.assertFalse(is_supported_mode("unknown"))
        self.assertEqual("default", validate_mode(None))
        self.assertIn("voice", list_supported_modes())

    def test_invalid_mode_raises(self) -> None:
        with self.assertRaises(ValueError):
            validate_mode("not-a-mode")


if __name__ == "__main__":
    unittest.main()
