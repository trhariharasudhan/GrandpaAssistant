import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHARED_DIR = os.path.join(ROOT, "backend", "app", "shared")
if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

import api_cors


class ApiCorsTests(unittest.TestCase):
    def test_defaults_are_localhost_only(self) -> None:
        origins = api_cors.localhost_cors_origins()
        self.assertIn("http://localhost:8765", origins)
        self.assertNotIn("*", origins)

    def test_env_wildcard_is_ignored_with_credentials(self) -> None:
        with patch.dict(os.environ, {"GRANDPA_ASSISTANT_CORS_ORIGINS": "*, https://example.com"}, clear=False):
            origins = api_cors.localhost_cors_origins()

        self.assertEqual(origins, list(api_cors.DEFAULT_LOCAL_CORS_ORIGINS))

    def test_env_keeps_only_local_origins(self) -> None:
        with patch.dict(
            os.environ,
            {"GRANDPA_ASSISTANT_CORS_ORIGINS": "http://localhost:3000, https://example.com, http://127.0.0.1:8765"},
            clear=False,
        ):
            origins = api_cors.localhost_cors_origins()

        self.assertEqual(origins, ["http://localhost:3000", "http://127.0.0.1:8765"])


if __name__ == "__main__":
    unittest.main()
