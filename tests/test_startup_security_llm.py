import os
import sys
import unittest
from unittest.mock import Mock, patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
SECURITY_DIR = os.path.join(APP_DIR, "security")
for path in [APP_DIR, SHARED_DIR, SECURITY_DIR]:
    if path not in sys.path:
        sys.path.insert(0, path)

import llm_client
import startup_diagnostics
from security import permission_engine


class StartupSecurityLlmTests(unittest.TestCase):
    def test_startup_diagnostics_reports_missing_voice_backends_as_warning(self) -> None:
        def fake_available(module_name: str) -> bool:
            return module_name == "speech_recognition"

        with patch.object(startup_diagnostics, "_module_is_available", side_effect=fake_available):
            status = startup_diagnostics._voice_input_status()

        self.assertEqual(status["status"], "warning")
        self.assertTrue(status["speech_recognition"])
        self.assertFalse(status["sounddevice"])
        self.assertFalse(status["pyaudio"])

    def test_startup_diagnostics_reports_missing_vision_dependencies_as_warning(self) -> None:
        with patch.object(startup_diagnostics, "_module_is_available", return_value=False):
            status = startup_diagnostics._camera_vision_status()

        self.assertEqual(status["status"], "warning")
        self.assertFalse(status["opencv"])
        self.assertFalse(status["numpy"])

    def test_dangerous_file_command_requires_confirmation_and_authentication(self) -> None:
        decision = permission_engine.classify_command("delete the files in downloads")

        self.assertEqual(decision["level"], "HIGH")
        self.assertTrue(decision["requires_confirmation"])
        self.assertTrue(decision["requires_authentication"])

    def test_general_question_is_not_classified_as_command_confirmation(self) -> None:
        decision = permission_engine.classify_command("what is python")

        self.assertEqual(decision["level"], "LOW")
        self.assertFalse(decision["requires_confirmation"])
        self.assertFalse(decision["requires_authentication"])

    def test_ollama_timeout_uses_environment_override(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"response": "hello"}

        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "OLLAMA_REQUEST_TIMEOUT_SECONDS": "1.5"}, clear=False), \
            patch.object(llm_client.requests, "post", return_value=response) as post:
            reply = llm_client.generate_chat_reply([], "hi")

        self.assertEqual(reply, "hello")
        self.assertEqual(post.call_args.kwargs["timeout"], 1.5)


if __name__ == "__main__":
    unittest.main()
