import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from project_knowledge.tokenizer import normalize_text, tokenize_query, tokenize_text


class ProjectTokenizerTests(unittest.TestCase):
    def test_handles_snake_case_camel_case_and_kebab_case(self) -> None:
        tokens = tokenize_text("prompt_builder chatService runtime-prompt")

        self.assertIn("prompt", tokens)
        self.assertIn("builder", tokens)
        self.assertIn("chat", tokens)
        self.assertIn("service", tokens)
        self.assertIn("runtime", tokens)

    def test_handles_file_paths(self) -> None:
        tokens = tokenize_text("backend/app/core/prompt_builder.py")

        self.assertIn("backend", tokens)
        self.assertIn("app", tokens)
        self.assertIn("core", tokens)
        self.assertIn("prompt", tokens)
        self.assertIn("builder", tokens)
        self.assertIn("py", tokens)

    def test_stop_words_and_min_token_behavior(self) -> None:
        tokens = tokenize_text("a an the to py x prompt")

        self.assertNotIn("a", tokens)
        self.assertNotIn("the", tokens)
        self.assertNotIn("x", tokens)
        self.assertIn("py", tokens)
        self.assertIn("prompt", tokens)

    def test_query_tokens_are_deduplicated(self) -> None:
        self.assertEqual(["prompt"], tokenize_query("prompt prompt"))

    def test_normalize_handles_malformed_input(self) -> None:
        self.assertEqual("", normalize_text(None))
        self.assertEqual([], tokenize_text(None))
        self.assertEqual([], tokenize_query(None))


if __name__ == "__main__":
    unittest.main()
