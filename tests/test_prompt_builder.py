import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from core.prompt_builder import build_mode_prompt, build_system_prompt, normalize_prompt_sections


class PromptBuilderTests(unittest.TestCase):
    def test_build_system_prompt_includes_required_sections(self) -> None:
        prompt = build_system_prompt("coding")

        self.assertIn("GrandpaAssistant", prompt)
        self.assertIn("Coding mode:", prompt)
        self.assertIn("Automation safety rules:", prompt)
        self.assertIn("Tool usage rules:", prompt)

    def test_mode_sections_are_included(self) -> None:
        self.assertIn("Voice mode:", build_system_prompt("voice"))
        self.assertIn("Vision mode:", build_system_prompt("vision"))
        self.assertIn("Research mode:", build_system_prompt("research"))
        self.assertIn("Planning mode:", build_system_prompt("planning"))

    def test_build_mode_prompt(self) -> None:
        prompt = build_mode_prompt("default")

        self.assertIn("Default mode:", prompt)

    def test_build_planning_mode_prompt(self) -> None:
        prompt = build_mode_prompt("planning")

        self.assertIn("Planning mode:", prompt)
        self.assertIn("Do not claim actions were executed.", prompt)

    def test_duplicate_sections_are_avoided(self) -> None:
        sections = normalize_prompt_sections(["alpha", " beta ", "alpha", "", None, "beta"])

        self.assertEqual(["alpha", "beta"], sections)

    def test_automation_mode_does_not_duplicate_safety(self) -> None:
        prompt = build_system_prompt("automation")

        self.assertEqual(1, prompt.count("Automation safety rules:"))

    def test_extra_context_is_included(self) -> None:
        prompt = build_system_prompt(
            "default",
            memory_context="User prefers concise answers.",
            extra_context="Current task: prompt runtime foundation.",
        )

        self.assertIn("Memory context:", prompt)
        self.assertIn("User prefers concise answers.", prompt)
        self.assertIn("Additional context:", prompt)
        self.assertIn("Current task: prompt runtime foundation.", prompt)

    def test_empty_context_does_not_add_empty_headers(self) -> None:
        prompt = build_system_prompt("default", memory_context="", extra_context=None)

        self.assertNotIn("Memory context:", prompt)
        self.assertNotIn("Additional context:", prompt)


if __name__ == "__main__":
    unittest.main()
