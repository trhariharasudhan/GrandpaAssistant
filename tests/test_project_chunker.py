import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from project_knowledge.config import DEFAULT_LIMITS
from project_knowledge.chunker import chunk_file, chunk_text


class ProjectChunkerTests(unittest.TestCase):
    def test_chunking_respects_max_size(self) -> None:
        chunks = chunk_text("abcdef", max_chars=3, overlap_chars=0)

        self.assertEqual(["abc", "def"], [chunk["text"] for chunk in chunks])
        self.assertTrue(all(len(chunk["text"]) <= 3 for chunk in chunks))

    def test_chunk_overlap_works(self) -> None:
        chunks = chunk_text("abcdef", max_chars=4, overlap_chars=2)

        self.assertEqual("abcd", chunks[0]["text"])
        self.assertEqual("cdef", chunks[1]["text"])

    def test_chunk_ids_deterministic_for_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "app.py"
            path.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")
            first = chunk_file(path, project_root=root)
            second = chunk_file(path, project_root=root)

        self.assertTrue(first["ok"])
        self.assertEqual(first["chunks"][0]["chunk_id"], second["chunks"][0]["chunk_id"])
        self.assertIn("app.py", first["chunks"][0]["chunk_id"])

    def test_line_ranges_exist(self) -> None:
        chunks = chunk_text("line 1\nline 2\nline 3\n", max_chars=8, overlap_chars=0)

        self.assertGreaterEqual(chunks[0]["line_start"], 1)
        self.assertGreaterEqual(chunks[0]["line_end"], chunks[0]["line_start"])

    def test_max_chunks_cap_works(self) -> None:
        text = "x" * (DEFAULT_LIMITS.max_chunk_chars * (DEFAULT_LIMITS.max_chunks_per_file + 5))
        chunks = chunk_text(text)

        self.assertEqual(DEFAULT_LIMITS.max_chunks_per_file, len(chunks))

    def test_chunk_file_rejects_unsupported_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "image.png"
            path.write_text("body", encoding="utf-8")
            result = chunk_file(path, project_root=root)

        self.assertFalse(result["ok"])
        self.assertEqual([], result["chunks"])

    def test_chunk_file_metadata_includes_path_and_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "README.md"
            path.write_text("# Title\nBody\n", encoding="utf-8")
            result = chunk_file(path, project_root=root)

        self.assertTrue(result["ok"])
        metadata = result["chunks"][0]["metadata"]
        self.assertEqual("README.md", metadata["relative_path"])
        self.assertEqual(".md", metadata["extension"])

    def test_no_reference_dependency(self) -> None:
        source = (APP_DIR / "project_knowledge" / "chunker.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
