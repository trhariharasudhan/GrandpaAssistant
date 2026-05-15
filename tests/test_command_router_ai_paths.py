import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
APP_DIR = BACKEND_DIR / "app"
SHARED_DIR = APP_DIR / "shared"
FEATURES_DIR = APP_DIR / "features"
for path in [BACKEND_DIR, APP_DIR, SHARED_DIR, FEATURES_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from core import command_router
from core.llm.base import LLMResponse


class CommandRouterAIPathTests(unittest.TestCase):
    def test_general_ai_path_returns_natural_response_when_provider_fails(self) -> None:
        spoken = []

        def capture_speak(message, *args, **kwargs):
            spoken.append(str(message))

        manager = Mock()
        manager.generate.return_value = LLMResponse(False, "", "ollama", "phi3", "offline")

        with patch.object(command_router, "speak", side_effect=capture_speak), \
            patch.object(command_router, "play_sound"), \
            patch("brain.ai_engine.get_default_provider_manager", return_value=manager), \
            patch("brain.ai_engine.answer_if_confident", return_value=""), \
            patch("brain.ai_engine.get_setting", side_effect=lambda _name, default=None: default), \
            patch("brain.ai_engine._build_prompt", return_value="prompt"), \
            patch("brain.ai_engine._provider_fallback_reply", return_value=""):
            command_router.process_command("banana cloud sentence", {}, input_mode="voice")

        self.assertTrue(spoken)
        self.assertNotIn("Something went wrong", spoken[-1])
        self.assertTrue(any(word in spoken[-1].lower() for word in ("got it", "tell me", "help", "what", "local ai")))

    def test_ai_provider_failure_does_not_crash_command_router(self) -> None:
        spoken = []

        with patch.object(command_router, "speak", side_effect=lambda message, *args, **kwargs: spoken.append(str(message))), \
            patch.object(command_router, "play_sound"), \
            patch("builtins.print"), \
            patch.object(command_router, "ask_ollama", side_effect=RuntimeError("provider down")):
            command_router.process_command("what should I learn today", {}, input_mode="voice")

        self.assertTrue(spoken)
        self.assertEqual("Something went wrong", spoken[-1])


if __name__ == "__main__":
    unittest.main()
