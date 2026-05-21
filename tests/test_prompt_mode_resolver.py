import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from core.prompt_mode_resolver import detect_planning_intent, resolve_prompt_mode


class PromptModeResolverTests(unittest.TestCase):
    def test_clear_coding_messages_return_coding(self) -> None:
        examples = [
            "fix this code please",
            "debug this stack trace",
            "python -m unittest tests.test_prompt_mode_resolver",
            "pytest is failing",
            "FastAPI endpoint error",
            "npm run build failed",
            "import error in app.py",
            "write a function for this",
            "git status summary",
            "styles.css not loading",
        ]

        for message in examples:
            with self.subTest(message=message):
                self.assertEqual("coding", resolve_prompt_mode(message))

    def test_normal_chat_returns_default(self) -> None:
        examples = [
            "hi da how are you",
            "what is the weather like",
            "tell me a joke",
            "plan my day",
            "what is a class in school",
            "function hall booking help",
            "git me a coffee",
        ]

        for message in examples:
            with self.subTest(message=message):
                self.assertEqual("default", resolve_prompt_mode(message))

    def test_empty_or_none_returns_default(self) -> None:
        self.assertEqual("default", resolve_prompt_mode(""))
        self.assertEqual("default", resolve_prompt_mode(None))

    def test_tamil_tanglish_normal_chat_returns_default(self) -> None:
        self.assertEqual("default", resolve_prompt_mode("enna da saptiya"))
        self.assertEqual("default", resolve_prompt_mode("நாளைக்கு என்ன plan"))

    def test_tamil_tanglish_with_coding_terms_returns_coding(self) -> None:
        self.assertEqual("coding", resolve_prompt_mode("intha python bug fix pannu"))
        self.assertEqual("coding", resolve_prompt_mode("code la error varudhu da"))

    def test_custom_default_is_preserved_for_non_coding(self) -> None:
        self.assertEqual("voice", resolve_prompt_mode("hello", default="voice"))

    def test_planning_intent_detected_by_helper(self) -> None:
        self.assertTrue(detect_planning_intent("make a plan for this cleanup"))
        self.assertTrue(detect_planning_intent("break this into steps"))
        self.assertTrue(detect_planning_intent("implementation plan for prompt runtime"))

    def test_resolver_does_not_return_planning_by_default(self) -> None:
        self.assertEqual("default", resolve_prompt_mode("make a plan for this cleanup"))

    def test_resolver_returns_planning_only_when_allowed(self) -> None:
        self.assertEqual("planning", resolve_prompt_mode("make a plan for this cleanup", allow_planning=True))
        self.assertEqual("planning", resolve_prompt_mode("plan my day", allow_planning=True))
        self.assertEqual("planning", resolve_prompt_mode("what should I do now", allow_planning=True))


if __name__ == "__main__":
    unittest.main()
