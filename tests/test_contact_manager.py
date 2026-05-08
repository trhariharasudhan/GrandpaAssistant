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

import call_control
import contact_manager
from api import web_api
from core import command_router


class ContactManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.contacts_path = os.path.join(self.temp_dir.name, "contacts.json")
        self.path_patches = [
            patch.object(contact_manager, "CONTACTS_PATH", self.contacts_path),
        ]
        for item in self.path_patches:
            item.start()
        self.web_patches = [
            patch.object(web_api, "_initialize_web_runtime", lambda: None),
            patch.object(web_api, "_shutdown_web_runtime", lambda: None),
            patch.object(web_api, "list_contacts", contact_manager.list_contacts),
            patch.object(web_api, "add_contact", contact_manager.add_contact),
            patch.object(web_api, "find_contact", contact_manager.find_contact),
            patch.object(web_api, "delete_contact", contact_manager.delete_contact),
            patch.object(command_router, "add_contact", contact_manager.add_contact),
            patch.object(command_router, "find_contact", contact_manager.find_contact),
            patch.object(command_router, "delete_contact", contact_manager.delete_contact),
            patch.object(command_router, "list_contacts", contact_manager.list_contacts),
        ]
        for item in self.web_patches:
            item.start()
        command_router.pending_confirmation = None
        self.client = TestClient(web_api.app)

    def tearDown(self) -> None:
        command_router.pending_confirmation = None
        for item in reversed(self.web_patches):
            item.stop()
        for item in reversed(self.path_patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_add_list_find_contact(self) -> None:
        added = contact_manager.add_contact("Riyaa", "9876543210", labels=["friend"])
        found = contact_manager.find_contact("riyaa")
        contacts = contact_manager.list_contacts()

        self.assertTrue(added["ok"])
        self.assertTrue(found["ok"])
        self.assertEqual(found["contact"]["phone"], "9876543210")
        self.assertEqual(contacts[0]["phone"], "******3210")

    def test_duplicate_name_handling(self) -> None:
        self.assertTrue(contact_manager.add_contact("Riyaa", "9876543210")["ok"])
        duplicate = contact_manager.add_contact("riyaa", "9876543211")

        self.assertFalse(duplicate["ok"])
        self.assertEqual(duplicate["status"], "duplicate")

    def test_phone_validation(self) -> None:
        self.assertFalse(contact_manager.validate_contact_phone("123")["ok"])
        self.assertTrue(contact_manager.validate_contact_phone("+919876543210")["ok"])

    def test_redacted_display(self) -> None:
        contact = {"name": "Riyaa", "phone": "9876543210", "labels": []}
        redacted = contact_manager.redact_contact_for_display(contact)

        self.assertEqual(redacted["phone"], "******3210")

    def test_call_control_resolves_local_contact(self) -> None:
        contact_manager.add_contact("Riyaa", "9876543210")
        resolved = call_control.resolve_call_target("riyaa")

        self.assertTrue(resolved["ok"])
        self.assertEqual(resolved["phone_number"], "9876543210")

    def test_clear_local_contact_call_does_not_ask_confirmation(self) -> None:
        spoken = []
        contact_manager.add_contact("Riyaa", "9876543210")
        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)), \
            patch.object(command_router, "initiate_call", return_value={"ok": True, "message": "Starting call flow for Riyaa."}) as initiate:
            command_router.process_command("call riyaa", {}, input_mode="text")

        initiate.assert_called_once()
        self.assertIsNone(command_router.pending_confirmation)
        self.assertIn("Starting call flow", spoken[-1])

    def test_ambiguous_contact_asks_clarification(self) -> None:
        contact_manager.add_contact("Riyaa Home", "9876543210")
        contact_manager.add_contact("Riyaa Work", "9876543211")
        result = contact_manager.find_contact("riyaa")

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "ambiguous")

    def test_delete_contact_requires_confirmation(self) -> None:
        spoken = []
        contact_manager.add_contact("Riyaa", "9876543210")
        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(message)):
            command_router.process_command("delete contact riyaa", {}, input_mode="text")

        self.assertIsNotNone(command_router.pending_confirmation)
        self.assertIn("Delete local contact", spoken[-1])
        self.assertTrue(contact_manager.find_contact("riyaa")["ok"])

    def test_api_protected(self) -> None:
        remote_client = TestClient(web_api.app, client=("203.0.113.170", 50000))

        response = remote_client.get("/api/contacts")

        self.assertEqual(response.status_code, 403)

    def test_localhost_api_contacts(self) -> None:
        response = self.client.post("/api/contacts", json={"name": "Riyaa", "phone": "9876543210"})
        self.assertEqual(response.status_code, 200)

        list_response = self.client.get("/api/contacts")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["items"][0]["phone"], "******3210")


if __name__ == "__main__":
    unittest.main()
