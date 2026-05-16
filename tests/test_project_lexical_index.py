import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from project_knowledge.chunker import chunk_file
from project_knowledge.config import DEFAULT_LIMITS
from project_knowledge.lexical_index import build_lexical_index, index_chunks, search_lexical_index


class ProjectLexicalIndexTests(unittest.TestCase):
    def test_index_builds_from_chunks(self) -> None:
        chunks = [
            {
                "chunk_id": "a:0",
                "chunk_index": 0,
                "text": "prompt builder runtime",
                "line_start": 1,
                "line_end": 1,
                "metadata": {"relative_path": "backend/prompt_builder.py", "extension": ".py"},
            }
        ]
        index = index_chunks(chunks)

        self.assertEqual(1, index["stats"]["document_count"])
        self.assertIn("prompt", index["inverted_index"])

    def test_search_finds_expected_terms(self) -> None:
        chunks = [
            {
                "chunk_id": "a:0",
                "chunk_index": 0,
                "text": "runtime prompt builder",
                "line_start": 1,
                "line_end": 1,
                "metadata": {"relative_path": "backend/prompt_builder.py", "extension": ".py"},
            }
        ]
        results = search_lexical_index(index_chunks(chunks), "prompt builder")

        self.assertEqual(1, len(results))
        self.assertEqual("backend/prompt_builder.py", results[0]["relative_path"])
        self.assertIn("prompt", results[0]["matched_terms"])

    def test_path_boost_ranks_path_match_first(self) -> None:
        chunks = [
            {
                "chunk_id": "body:0",
                "chunk_index": 0,
                "text": "prompt prompt prompt",
                "line_start": 1,
                "line_end": 1,
                "metadata": {"relative_path": "backend/body.py", "extension": ".py"},
            },
            {
                "chunk_id": "path:0",
                "chunk_index": 0,
                "text": "prompt",
                "line_start": 1,
                "line_end": 1,
                "metadata": {"relative_path": "backend/prompt_builder.py", "extension": ".py"},
            },
        ]
        results = search_lexical_index(index_chunks(chunks), "prompt")

        self.assertEqual("backend/prompt_builder.py", results[0]["relative_path"])

    def test_deterministic_ordering(self) -> None:
        chunks = [
            {
                "chunk_id": "b:0",
                "chunk_index": 0,
                "text": "same",
                "line_start": 1,
                "line_end": 1,
                "metadata": {"relative_path": "b.py", "extension": ".py"},
            },
            {
                "chunk_id": "a:0",
                "chunk_index": 0,
                "text": "same",
                "line_start": 1,
                "line_end": 1,
                "metadata": {"relative_path": "a.py", "extension": ".py"},
            },
        ]
        index = index_chunks(chunks)

        self.assertEqual(search_lexical_index(index, "same"), search_lexical_index(index, "same"))
        self.assertEqual("a.py", search_lexical_index(index, "same")[0]["relative_path"])

    def test_snippets_capped_and_redacted(self) -> None:
        chunks = [
            {
                "chunk_id": "secret:0",
                "chunk_index": 0,
                "text": "token=abc123\n" + "x" * (DEFAULT_LIMITS.max_result_snippet_chars + 100),
                "line_start": 1,
                "line_end": 2,
                "metadata": {"relative_path": "settings.ini", "extension": ".ini"},
            }
        ]
        results = search_lexical_index(index_chunks(chunks), "token")

        self.assertLessEqual(len(results[0]["snippet"]), DEFAULT_LIMITS.max_result_snippet_chars)
        self.assertIn("[REDACTED]", results[0]["snippet"])
        self.assertNotIn("abc123", results[0]["snippet"])

    def test_ignored_reference_files_not_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ignored = root / "reference" / "system_prompts_leaks"
            ignored.mkdir(parents=True)
            (ignored / "leak.md").write_text("prompt builder leak", encoding="utf-8")
            (root / "safe.md").write_text("prompt builder safe", encoding="utf-8")
            index = build_lexical_index(root)

        encoded = json.dumps(index)
        self.assertIn("safe.md", encoded)
        self.assertNotIn("leak.md", encoded)
        self.assertNotIn("prompt builder leak", encoded)

    def test_chunk_file_can_feed_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "README.md"
            path.write_text("project search helper", encoding="utf-8")
            chunk_result = chunk_file(path, project_root=root)
            index = index_chunks(chunk_result["chunks"])
            results = search_lexical_index(index, "search helper")

        self.assertEqual(1, len(results))

    def test_malformed_query_does_not_crash(self) -> None:
        self.assertEqual([], search_lexical_index(index_chunks([]), None))

    def test_no_reference_dependency(self) -> None:
        source = (APP_DIR / "project_knowledge" / "lexical_index.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
