import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from core.prompt_memory_context import (
    MAX_MEMORY_CONTEXT_CHARS,
    MEMORY_CONTEXT_HEADER,
    build_safe_memory_context,
    normalize_memory_context,
    should_include_memory_context,
)


class PromptMemoryContextTests(unittest.TestCase):
    def test_none_returns_empty_and_false(self) -> None:
        self.assertEqual("", normalize_memory_context(None))
        self.assertFalse(should_include_memory_context(None))

    def test_string_memory_is_normalized(self) -> None:
        result = normalize_memory_context("  User likes concise answers.  ")

        self.assertIn(MEMORY_CONTEXT_HEADER, result)
        self.assertIn("- User likes concise answers.", result)

    def test_list_memory_is_normalized(self) -> None:
        result = normalize_memory_context(["User uses Windows.", "Prefers local AI."])

        self.assertIn("- User uses Windows.", result)
        self.assertIn("- Prefers local AI.", result)

    def test_dict_memory_is_normalized(self) -> None:
        result = normalize_memory_context({"name": "Da", "preference": "short replies"})

        self.assertIn("- name: Da", result)
        self.assertIn("- preference: short replies", result)

    def test_long_memory_is_truncated(self) -> None:
        result = normalize_memory_context("x" * (MAX_MEMORY_CONTEXT_CHARS + 100))

        self.assertLessEqual(len(result), MAX_MEMORY_CONTEXT_CHARS + len("\n- [truncated]"))
        self.assertIn("[truncated]", result)

    def test_obvious_sensitive_keys_are_excluded(self) -> None:
        result = normalize_memory_context(
            {
                "api_key": "do-not-include",
                "password": "do-not-include",
                "preference": "include this",
            }
        )

        self.assertIn("include this", result)
        self.assertNotIn("do-not-include", result)
        self.assertNotIn("api_key", result)
        self.assertNotIn("password", result)

    def test_sensitive_string_lines_are_excluded(self) -> None:
        result = normalize_memory_context("token: hidden\nUser likes tests")

        self.assertIn("User likes tests", result)
        self.assertNotIn("hidden", result)

    def test_malformed_values_do_not_crash(self) -> None:
        class BadValue:
            def __str__(self):
                raise RuntimeError("bad")

        self.assertEqual("", normalize_memory_context(BadValue()))

    def test_output_labels_memory_as_contextual_hints(self) -> None:
        result = build_safe_memory_context("User prefers Python")

        self.assertTrue(result.startswith(MEMORY_CONTEXT_HEADER))
        self.assertIn("not guaranteed facts", result)

    def test_no_prompt_or_reference_dependency(self) -> None:
        source = (APP_DIR / "core" / "prompt_memory_context.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
