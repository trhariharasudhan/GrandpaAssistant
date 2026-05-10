import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(ROOT, "backend")
APP_DIR = os.path.join(BACKEND_DIR, "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [BACKEND_DIR, APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

from app.api import web_api
from app.services import local_action_executor


class LocalActionExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_path = os.path.join(self.temp_dir.name, "local_actions.jsonl")
        self.patches = [
            patch.object(local_action_executor, "SAFE_ROOTS", [self.temp_dir.name]),
            patch.object(local_action_executor, "AUDIT_LOG_PATH", self.audit_path),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_valid_create_folder_action(self) -> None:
        target = os.path.join(self.temp_dir.name, "new-folder")

        result = local_action_executor.execute_local_action(
            {"action": "create_folder", "params": {"path": target}}
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "create_folder")
        self.assertTrue(os.path.isdir(target))
        self.assertTrue(os.path.exists(self.audit_path))

    def test_invalid_action_is_rejected(self) -> None:
        result = local_action_executor.execute_local_action(
            {"action": "run_shell", "params": {"command": "dir"}}
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["action"], "run_shell")
        self.assertIn("Unsupported", result["message"])

    def test_dangerous_input_is_blocked(self) -> None:
        result = local_action_executor.execute_local_action(
            {"action": "create_folder", "params": {"path": os.path.join(self.temp_dir.name, "safe;del")}}
        )

        self.assertFalse(result["ok"])
        self.assertIn("unsafe", result["message"].lower())

    def test_missing_params_returns_safe_failure(self) -> None:
        result = local_action_executor.execute_local_action({"action": "copy_file"})

        self.assertFalse(result["ok"])
        self.assertEqual(result["action"], "copy_file")
        self.assertIn("Path is required", result["message"])

    def test_copy_file_action_stays_inside_safe_roots(self) -> None:
        source = os.path.join(self.temp_dir.name, "source.txt")
        destination = os.path.join(self.temp_dir.name, "nested", "destination.txt")
        with open(source, "w", encoding="utf-8") as file:
            file.write("hello")

        result = local_action_executor.execute_local_action(
            {"action": "copy_file", "params": {"source": source, "destination": destination}}
        )

        self.assertTrue(result["ok"])
        self.assertTrue(os.path.exists(destination))


class LocalActionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(web_api.app)

    def test_local_action_route_calls_executor(self) -> None:
        expected = {"ok": True, "action": "start_obs_recording", "message": "ok", "data": {}}
        with patch.object(web_api, "execute_local_action", return_value=expected) as mocked:
            response = self.client.post(
                "/api/local-actions/execute",
                json={"action": "start_obs_recording", "params": {}},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        mocked.assert_called_once_with({"action": "start_obs_recording", "params": {}})

    def test_local_action_route_blocks_remote_unauthenticated(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.30", 50000))

        response = remote_client.post(
            "/api/local-actions/execute",
            json={"action": "start_obs_recording", "params": {}},
        )

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
