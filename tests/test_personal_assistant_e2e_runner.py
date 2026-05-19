import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts" / "dev"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


import personal_assistant_e2e


class PersonalAssistantE2ERunnerTests(unittest.TestCase):
    def test_mock_mode_runner_passes_without_real_actions(self) -> None:
        code, results = personal_assistant_e2e.run_e2e(
            personal_assistant_e2e.build_parser().parse_args([])
        )

        self.assertEqual(0, code)
        flow_status = {item["flow"]: item["status"] for item in results if item["status"] != "INFO"}
        self.assertEqual("PASS", flow_status["volume decrease"])
        self.assertEqual("PASS", flow_status["open calculator then close it"])
        self.assertEqual("PASS", flow_status["screen read request"])
        self.assertTrue(all(item["status"] != "FAIL" for item in results))

    def test_json_mode_main_returns_success(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, personal_assistant_e2e.main(["--json"]))
        self.assertIn("capability discovery", output.getvalue())


if __name__ == "__main__":
    unittest.main()
