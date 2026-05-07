import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

import local_knowledge
from api import web_api


class KnowledgeReviewQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.queue_path = os.path.join(self.temp_dir.name, "review_queue.jsonl")
        self.science_path = os.path.join(self.temp_dir.name, "basic_science.json")
        self.patches = [
            patch.object(local_knowledge, "REVIEW_QUEUE_PATH", self.queue_path),
            patch.object(web_api, "_initialize_web_runtime", lambda: None),
            patch.object(web_api, "_shutdown_web_runtime", lambda: None),
        ]
        for item in self.patches:
            item.start()
        self.client = TestClient(web_api.app)

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_unknown_simple_question_is_queued(self) -> None:
        result = local_knowledge.lookup_local_knowledge("what is a lunar sundial?")

        self.assertFalse(result["confident"])
        self.assertTrue(result["queued_for_review"])
        items = local_knowledge.list_knowledge_review_queue()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source"], "local_knowledge_miss")

    def test_duplicate_question_is_not_repeatedly_queued(self) -> None:
        local_knowledge.lookup_local_knowledge("what is a lunar sundial?")
        local_knowledge.lookup_local_knowledge("what is a lunar sundial?")

        self.assertEqual(len(local_knowledge.list_knowledge_review_queue()), 1)

    def test_private_looking_text_is_not_queued(self) -> None:
        result = local_knowledge.lookup_local_knowledge("what is my password token abc123?")

        self.assertFalse(result["confident"])
        self.assertFalse(result.get("queued_for_review", False))
        self.assertEqual(local_knowledge.list_knowledge_review_queue(), [])

    def test_queue_listing_and_clear_work(self) -> None:
        local_knowledge.lookup_local_knowledge("what is a lunar sundial?")
        item = local_knowledge.list_knowledge_review_queue()[0]

        self.assertTrue(local_knowledge.clear_review_queue_item(item["id"]))
        self.assertEqual(local_knowledge.list_knowledge_review_queue(), [])

    def test_existing_known_answers_still_work(self) -> None:
        result = local_knowledge.lookup_local_knowledge("what is the formula of water")

        self.assertTrue(result["confident"])
        self.assertIn("H2O", result["answer"])
        self.assertEqual(local_knowledge.list_knowledge_review_queue(), [])

    def test_add_local_knowledge_entry_works(self) -> None:
        with patch.object(local_knowledge, "SCIENCE_PATH", self.science_path):
            entry = local_knowledge.add_local_knowledge_entry(
                "science",
                "formula of salt|chemical formula of salt",
                "The chemical formula of salt is NaCl.",
            )

            self.assertTrue(entry["id"].startswith("custom_"))
            result = local_knowledge.lookup_local_knowledge("what is the formula of salt")
        self.assertTrue(result["confident"])
        self.assertIn("NaCl", result["answer"])

    def test_review_queue_route_allows_localhost(self) -> None:
        local_knowledge.lookup_local_knowledge("what is a lunar sundial?")

        response = self.client.get("/api/knowledge/review-queue")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["items"]), 1)

    def test_review_queue_route_blocks_remote_unauthenticated(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.25", 50000))

        response = remote_client.get("/api/knowledge/review-queue")

        self.assertEqual(response.status_code, 403)

    def test_review_queue_route_allows_remote_admin(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.25", 50000))
        admin_context = {"user": {"id": 1, "username": "admin", "role": "admin"}}
        local_knowledge.lookup_local_knowledge("what is a lunar sundial?")

        with patch.object(web_api, "authenticate_app_token", return_value=admin_context):
            response = remote_client.get(
                "/api/knowledge/review-queue",
                headers={"Authorization": "Bearer admin-token"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["items"]), 1)


if __name__ == "__main__":
    unittest.main()
