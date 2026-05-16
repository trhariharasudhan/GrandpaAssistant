import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
SCRIPT = ROOT / "scripts" / "dev" / "project_snapshot.py"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from project_knowledge.project_snapshot import build_project_snapshot


class ProjectSnapshotTests(unittest.TestCase):
    def test_snapshot_json_safe_and_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('private body')\n", encoding="utf-8")
            snapshot = build_project_snapshot(root)

        encoded = json.dumps(snapshot)
        self.assertIsInstance(snapshot, dict)
        self.assertNotIn("private body", encoded)
        self.assertEqual(1, snapshot["total_files"])

    def test_snapshot_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# title\n", encoding="utf-8")
            snapshot = build_project_snapshot(root)

        self.assertIn("project_root", snapshot)
        self.assertIn("total_files", snapshot)
        self.assertIn("indexed_extensions", snapshot)
        self.assertIn("largest_files", snapshot)
        self.assertIn("recent_files", snapshot)
        self.assertIn("discovered_files", snapshot)

    def test_cli_outputs_json_without_file_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("print('private body')\n", encoding="utf-8")
            result = subprocess.run(
                [str(PYTHON), str(SCRIPT), "--root", str(root)],
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(0, result.returncode, result.stderr)
        snapshot = json.loads(result.stdout)
        self.assertEqual(1, snapshot["total_files"])
        self.assertNotIn("private body", result.stdout)

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
        source = (APP_DIR / "project_knowledge" / "project_snapshot.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
