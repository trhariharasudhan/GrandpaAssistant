import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
SCRIPT = ROOT / "scripts" / "dev" / "project_chunk_summary.py"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from project_knowledge.project_chunks import build_project_chunk_summary


class ProjectChunkSummaryTests(unittest.TestCase):
    def test_project_summary_contains_no_chunk_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('private chunk body')\n", encoding="utf-8")
            summary = build_project_chunk_summary(root)

        encoded = json.dumps(summary)
        self.assertEqual(1, summary["total_files_considered"])
        self.assertEqual(1, summary["files_chunked"])
        self.assertEqual(1, summary["total_chunks"])
        self.assertNotIn("private chunk body", encoded)

    def test_redacted_and_truncated_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "secret.ini").write_text("token=abc123\n", encoding="utf-8")
            (root / "large.md").write_text("a" * 210_000, encoding="utf-8")
            summary = build_project_chunk_summary(root)

        self.assertEqual(2, summary["files_chunked"])
        self.assertEqual(1, summary["redacted_files"])
        self.assertEqual(1, summary["truncated_files"])

    def test_invalid_root_returns_safe_error(self) -> None:
        summary = build_project_chunk_summary("not-a-real-folder")

        self.assertEqual(0, summary["total_files_considered"])
        self.assertEqual("invalid_project_root", summary["errors"][0]["error"])

    def test_cli_output_contains_no_chunk_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("visible file text should stay hidden\n", encoding="utf-8")
            result = subprocess.run(
                [str(PYTHON), str(SCRIPT), "--root", str(root)],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(0, result.returncode, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(1, summary["files_chunked"])
        self.assertNotIn("visible file text should stay hidden", result.stdout)

    def test_cli_compact_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# ok\n", encoding="utf-8")
            result = subprocess.run(
                [str(PYTHON), str(SCRIPT), "--root", str(root), "--compact"],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIsInstance(json.loads(result.stdout), dict)
        self.assertNotIn("\n  ", result.stdout)

    def test_no_reference_dependency(self) -> None:
        source = (APP_DIR / "project_knowledge" / "project_chunks.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
