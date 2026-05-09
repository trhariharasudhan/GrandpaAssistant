import os
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for path in [APP_DIR, SHARED_DIR, FEATURES_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

import contact_manager
from core import command_router
from security.permission_engine import classify_command


class ContactCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.contacts_path = os.path.join(self.temp_dir.name, "contacts.json")
        self.patches = [
            patch.object(contact_manager, "CONTACTS_PATH", self.contacts_path),
            patch.object(command_router, "add_contact", contact_manager.add_contact),
            patch.object(command_router, "find_contact", contact_manager.find_contact),
            patch.object(command_router, "delete_contact", contact_manager.delete_contact),
            patch.object(command_router, "list_contacts", contact_manager.list_contacts),
        ]
        for item in self.patches:
            item.start()
        command_router.pending_confirmation = None
        command_router.pending_confirmations.clear()
        self.spoken = []
        self.speak_patch = patch.object(
            command_router,
            "speak",
            side_effect=lambda message, *args, **kwargs: self.spoken.append(message),
        )
        self.speak_patch.start()

    def tearDown(self) -> None:
        self.speak_patch.stop()
        for item in reversed(self.patches):
            item.stop()
        command_router.pending_confirmation = None
        command_router.pending_confirmations.clear()
        self.temp_dir.cleanup()

    def test_show_contact_does_not_create_pending_confirmation(self) -> None:
        command_router.process_command("show contact", {}, input_mode="text")

        self.assertIsNone(command_router.pending_confirmation)
        self.assertIn("No contacts saved yet", self.spoken[-1])

    def test_show_contacts_lists_redacted_contacts(self) -> None:
        contact_manager.add_contact("Riyaa", "9876543210")

        command_router.process_command("show contacts", {}, input_mode="text")

        self.assertIn("Riyaa", self.spoken[-1])
        self.assertIn("******3210", self.spoken[-1])
        self.assertNotIn("9876543210", self.spoken[-1])

    def test_list_contacts_works(self) -> None:
        contact_manager.add_contact("Riyaa", "9876543210")

        command_router.process_command("list contacts", {}, input_mode="text")

        self.assertIn("Riyaa", self.spoken[-1])

    def test_no_contacts_message_is_friendly(self) -> None:
        command_router.process_command("my contacts", {}, input_mode="text")

        self.assertEqual(self.spoken[-1], "No contacts saved yet. Say add contact <name> <phone>.")

    def test_find_contact_works_with_redacted_phone(self) -> None:
        contact_manager.add_contact("Riyaa", "9876543210")

        command_router.process_command("find contact riyaa", {}, input_mode="text")

        self.assertIn("Found Riyaa", self.spoken[-1])
        self.assertIn("******3210", self.spoken[-1])

    def test_search_contact_works(self) -> None:
        contact_manager.add_contact("Riyaa", "9876543210")

        command_router.process_command("search contact riyaa", {}, input_mode="text")

        self.assertIn("Found Riyaa", self.spoken[-1])

    def test_delete_contact_creates_confirmation(self) -> None:
        contact_manager.add_contact("Riyaa", "9876543210")

        command_router.process_command("delete contact riyaa", {}, input_mode="text")

        self.assertIsNotNone(command_router.pending_confirmation)
        self.assertIn("Delete local contact", self.spoken[-1])

    def test_yes_approves_latest_pending_confirmation(self) -> None:
        contact_manager.add_contact("Riyaa", "9876543210")
        command_router.process_command("delete contact riyaa", {}, input_mode="text")

        command_router.process_command("yes", {}, input_mode="text")

        self.assertIsNone(command_router.pending_confirmation)
        self.assertFalse(contact_manager.find_contact("riyaa")["ok"])
        self.assertIn("Deleted local contact", self.spoken[-1])

    def test_no_dismisses_latest_pending_confirmation(self) -> None:
        contact_manager.add_contact("Riyaa", "9876543210")
        command_router.process_command("delete contact riyaa", {}, input_mode="text")

        command_router.process_command("no", {}, input_mode="text")

        self.assertIsNone(command_router.pending_confirmation)
        self.assertTrue(contact_manager.find_contact("riyaa")["ok"])
        self.assertEqual(self.spoken[-1], "Cancelled.")

    def test_risky_actions_still_require_confirmation(self) -> None:
        decision = classify_command("shutdown system")

        self.assertTrue(decision["requires_confirmation"])
        self.assertTrue(decision["requires_authentication"])


if __name__ == "__main__":
    unittest.main()
