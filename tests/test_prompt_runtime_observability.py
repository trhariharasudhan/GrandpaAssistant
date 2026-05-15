import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from core.prompt_runtime_observability import MAX_REASON_LENGTH, build_prompt_runtime_metadata


class PromptRuntimeObservabilityTests(unittest.TestCase):
    def test_metadata_contains_expected_keys(self) -> None:
        metadata = build_prompt_runtime_metadata(
            runtime_enabled=True,
            selected_mode="coding",
            source="runtime",
            fallback_used=False,
            prompt_length=123,
            reason=None,
        )

        self.assertEqual(
            {
                "runtime_enabled",
                "selected_mode",
                "source",
                "fallback_used",
                "prompt_length",
                "reason",
                "memory_context_included",
            },
            set(metadata),
        )

    def test_metadata_does_not_contain_prompt_text(self) -> None:
        prompt_body = "secret system prompt body"
        metadata = build_prompt_runtime_metadata(
            runtime_enabled=True,
            selected_mode="default",
            source="runtime",
            fallback_used=False,
            prompt_length=len(prompt_body),
            reason="ok",
        )

        self.assertNotIn(prompt_body, json.dumps(metadata))
        self.assertEqual(len(prompt_body), metadata["prompt_length"])
        self.assertFalse(metadata["memory_context_included"])

    def test_reason_is_sanitized_and_truncated(self) -> None:
        reason = "  BUILD\nFAILED\t" + ("x" * 200)
        metadata = build_prompt_runtime_metadata(
            runtime_enabled=True,
            selected_mode="default",
            source="runtime",
            fallback_used=True,
            prompt_length=10,
            reason=reason,
        )

        self.assertLessEqual(len(metadata["reason"] or ""), MAX_REASON_LENGTH)
        self.assertNotIn("\n", metadata["reason"] or "")
        self.assertTrue((metadata["reason"] or "").startswith("build failed"))

    def test_source_is_normalized(self) -> None:
        metadata = build_prompt_runtime_metadata(
            runtime_enabled=False,
            selected_mode="DEFAULT",
            source="Runtime",
            fallback_used=False,
        )

        self.assertEqual("runtime", metadata["source"])
        self.assertEqual("default", metadata["selected_mode"])

    def test_invalid_source_defaults_to_legacy(self) -> None:
        metadata = build_prompt_runtime_metadata(
            runtime_enabled=False,
            selected_mode="default",
            source="prompt-body",
            fallback_used=True,
        )

        self.assertEqual("legacy", metadata["source"])

    def test_metadata_is_json_safe(self) -> None:
        metadata = build_prompt_runtime_metadata(
            runtime_enabled=True,
            selected_mode="coding",
            source="runtime",
            fallback_used=False,
            prompt_length=12,
            reason="selected",
            memory_context_included=True,
        )

        self.assertIsInstance(json.dumps(metadata), str)
        self.assertTrue(metadata["memory_context_included"])


if __name__ == "__main__":
    unittest.main()
