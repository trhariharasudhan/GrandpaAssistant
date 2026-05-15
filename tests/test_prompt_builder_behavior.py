import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
for path in [APP_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from core.prompts import PromptBuildRequest, build_prompt, build_terminal_prompt


class PromptBuilderBehaviorTests(unittest.TestCase):
    def test_tamil_prompt_includes_same_language_instruction(self) -> None:
        prompt = build_terminal_prompt("வணக்கம்", memories=[], recent_messages=[])

        self.assertIn("Reply in natural Tamil", prompt)

    def test_tanglish_prompt_includes_same_language_instruction(self) -> None:
        prompt = build_terminal_prompt("enna da plan", memories=[], recent_messages=[])

        self.assertIn("Reply in natural Tanglish", prompt)

    def test_english_prompt_includes_english_style(self) -> None:
        prompt = build_terminal_prompt("hello there", memories=[], recent_messages=[])

        self.assertIn("Reply in natural English", prompt)
        self.assertIn("Personality: friendly, casual, helpful, practical.", prompt)

    def test_saved_memory_is_included_when_passed(self) -> None:
        prompt = build_terminal_prompt("what is my goal?", memories=[{"fact": "User wants to learn Python"}], recent_messages=[])

        self.assertIn("Saved user memory:", prompt)
        self.assertIn("User wants to learn Python", prompt)

    def test_recent_history_is_included_when_passed(self) -> None:
        prompt = build_terminal_prompt(
            "continue",
            memories=[],
            recent_messages=[{"role": "user", "message": "I started a Flask app"}],
        )

        self.assertIn("Recent conversation context:", prompt)
        self.assertIn("User: I started a Flask app", prompt)

    def test_safety_rules_are_included(self) -> None:
        prompt = build_terminal_prompt("hello", memories=[], recent_messages=[])

        self.assertIn("Never expose secrets", prompt)
        self.assertIn("Politely refuse harmful or illegal requests", prompt)

    def test_code_full_code_instruction_is_preserved(self) -> None:
        prompt = build_terminal_prompt("write code", memories=[], recent_messages=[])

        self.assertIn("complete working code", prompt)

    def test_empty_context_does_not_crash(self) -> None:
        prompt = build_prompt(PromptBuildRequest(user_message=""))

        self.assertIn("Saved user memory:", prompt)
        self.assertIn("Recent conversation context:", prompt)


if __name__ == "__main__":
    unittest.main()
