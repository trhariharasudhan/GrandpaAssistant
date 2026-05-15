import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(ROOT, "backend")
APP_DIR = os.path.join(BACKEND_DIR, "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [BACKEND_DIR, APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

import desktop_backend_entry
from app.api import chat_api


web_api = desktop_backend_entry.web_api


TARGET_ROUTES = {
    ("POST", "/api/automation/n8n/test"): ("api_n8n_test", "n8n_test"),
    ("POST", "/chat"): ("chat_reply", "chat"),
    ("GET", "/chat/history"): ("chat_history", "get_chat_history"),
    ("POST", "/chat/reset"): ("chat_reset", "reset_chat"),
    ("POST", "/chat/stream"): ("chat_stream", "chat_stream"),
}


def _route_methods(app):
    items = []
    for route in app.routes:
        path = getattr(route, "path", "")
        name = getattr(route, "name", "")
        methods = getattr(route, "methods", set()) or set()
        for method in methods:
            items.append((method, path, name))
    return items


def _route_name(app, method, path):
    matches = [
        name
        for route_method, route_path, name in _route_methods(app)
        if route_method == method and route_path == path
    ]
    return matches


class RouteDuplicationResolutionTests(unittest.TestCase):
    def test_desktop_entrypoint_uses_web_api_app(self) -> None:
        self.assertIs(desktop_backend_entry.web_api.app, web_api.app)

    def test_active_web_api_has_no_exact_duplicate_method_path_routes(self) -> None:
        seen = {}
        duplicates = []
        for method, path, name in _route_methods(web_api.app):
            key = (method, path)
            if key in seen:
                duplicates.append((method, path, seen[key], name))
            else:
                seen[key] = name
        self.assertEqual([], duplicates)

    def test_duplicate_source_routes_are_owned_by_web_api_in_active_app(self) -> None:
        for (method, path), (web_name, _chat_name) in TARGET_ROUTES.items():
            with self.subTest(route=f"{method} {path}"):
                self.assertEqual([web_name], _route_name(web_api.app, method, path))

    def test_chat_api_duplicate_routes_are_isolated_to_chat_api_app(self) -> None:
        for (method, path), (_web_name, chat_name) in TARGET_ROUTES.items():
            with self.subTest(route=f"{method} {path}"):
                self.assertEqual([chat_name], _route_name(chat_api.app, method, path))


if __name__ == "__main__":
    unittest.main()
