import os
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
for path in [APP_DIR, SHARED_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

import local_knowledge
from local_knowledge import answer_if_confident, lookup_local_knowledge


class LocalKnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.queue_patch = patch.object(
            local_knowledge,
            "REVIEW_QUEUE_PATH",
            os.path.join(self.temp_dir.name, "review_queue.jsonl"),
        )
        self.queue_patch.start()

    def tearDown(self) -> None:
        self.queue_patch.stop()
        self.temp_dir.cleanup()

    def test_water_formula_returns_h2o(self) -> None:
        result = lookup_local_knowledge("what is the formula of water")

        self.assertTrue(result["confident"])
        self.assertIn("H2O", result["answer"])

    def test_thirukkural_lookup_returns_kural(self) -> None:
        result = lookup_local_knowledge("tell me one thirukkural")

        self.assertTrue(result["confident"])
        self.assertIn("Thirukkural", result["answer"])
        self.assertIn("அகர", result["answer"])

    def test_time_now_returns_time_style_response(self) -> None:
        result = lookup_local_knowledge("what is time now")

        self.assertTrue(result["confident"])
        self.assertIn("It is", result["answer"])
        self.assertRegex(result["answer"], r"\d{2}:\d{2}\s(?:AM|PM)")

    def test_unknown_question_falls_back_cleanly(self) -> None:
        result = lookup_local_knowledge("who invented the blue banana engine")

        self.assertFalse(result["confident"])
        self.assertIn("offline knowledge pack", result["answer"])
        self.assertEqual(answer_if_confident("who invented the blue banana engine"), "")

    def test_no_exact_echo_response(self) -> None:
        question = "what is the formula of water"
        result = lookup_local_knowledge(question)

        self.assertNotEqual(result["answer"].strip().lower(), question)

    def test_tamil_question_gets_tamil_friendly_answer(self) -> None:
        result = lookup_local_knowledge("நீரின் வாய்பாடு என்ன")

        self.assertTrue(result["confident"])
        self.assertIn("H2O", result["answer"])
        self.assertIn("நீரின்", result["answer"])


if __name__ == "__main__":
    unittest.main()
