import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHARED_DIR = os.path.join(ROOT, "backend", "app", "shared")
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

from voice_readiness import collect_voice_readiness


class VoiceReadinessTests(unittest.TestCase):
    def test_collect_voice_readiness_returns_components(self) -> None:
        with patch("voice_readiness._module_is_available", return_value=True):
            report = collect_voice_readiness()

        self.assertIn("components", report)
        self.assertGreaterEqual(len(report["components"]), 4)
        ids = {item["id"] for item in report["components"]}
        self.assertIn("voice_input", ids)
        self.assertIn("piper_tts", ids)
        self.assertIn("voice_runtime", ids)


if __name__ == "__main__":
    unittest.main()
