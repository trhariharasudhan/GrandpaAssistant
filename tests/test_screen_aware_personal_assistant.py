import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
SHARED_DIR = APP_DIR / "shared"
for path in [APP_DIR, SHARED_DIR]:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


from core import chat_service
from core.personal_assistant import executor, service


def screen_context(activity="media", app_name="Google Chrome", title="YouTube - relaxing music", kind="browser", domain="youtube.com"):
    return {
        "active_window": {
            "ok": True,
            "app_name": app_name,
            "title": title,
            "kind": kind,
            "domain": domain,
            "activity": activity,
        },
        "screen_context": {"activity": activity, "source": "active_window"},
        "screenshot": None,
    }


class ScreenAwarePersonalAssistantTests(unittest.TestCase):
    def setUp(self) -> None:
        chat_service.clear_all_chat_sessions_for_tests()
        self.previous_debug = os.environ.pop(chat_service.PERSONAL_ASSISTANT_DEBUG_ENV, None)
        self.local_patch = patch.object(chat_service, "answer_if_confident", return_value=None)
        self.local_patch.start()

    def tearDown(self) -> None:
        self.local_patch.stop()
        chat_service.clear_all_chat_sessions_for_tests()
        if self.previous_debug is None:
            os.environ.pop(chat_service.PERSONAL_ASSISTANT_DEBUG_ENV, None)
        else:
            os.environ[chat_service.PERSONAL_ASSISTANT_DEBUG_ENV] = self.previous_debug

    def test_pause_it_uses_active_media_window_context(self) -> None:
        with patch.object(service, "get_screen_context", return_value=screen_context()), patch.object(
            executor.local_action_executor,
            "execute_local_action",
            return_value={"ok": True, "action": "media_key", "message": "Paused or resumed media playback.", "data": {"operation": "pause"}},
        ) as action:
            result = chat_service.build_chat_reply("pause it", session_id="pause-media", provider=lambda *_args, **_kwargs: "fallback")

        self.assertTrue(result["executed"])
        self.assertEqual("media_control", result["intent"])
        self.assertIn("media playback", result["reply"])
        self.assertEqual({"action": "media_key", "params": {"operation": "pause"}}, action.call_args.args[0])

    def test_pause_it_asks_when_no_media_context_exists(self) -> None:
        with patch.object(service, "get_screen_context", return_value=screen_context(activity="coding", app_name="Visual Studio Code", title="app.py", kind="editor", domain="")):
            result = chat_service.build_chat_reply("pause it", session_id="pause-missing", provider=lambda *_args, **_kwargs: "fallback")

        self.assertTrue(result["ok"])
        self.assertFalse(result["executed"])
        self.assertIn("do not see an active video or music window", result["reply"])
        self.assertIn("media_context", result["missing_details"])

    def test_close_current_app_uses_tracked_context_and_confirmation(self) -> None:
        def fake_action(payload):
            if payload["action"] == "open_app":
                return {"ok": True, "action": "open_app", "message": "Opened calculator.", "data": {"app": "calculator", "pid": 777}}
            return {"ok": True, "action": "close_app", "message": "Closed calculator.", "data": {"app": "calculator", "pid": 777}}

        with patch.object(service, "get_screen_context", return_value=screen_context(activity="general", app_name="Calculator", title="Calculator", kind="unknown", domain="")), patch.object(
            executor.local_action_executor,
            "execute_local_action",
            side_effect=fake_action,
        ):
            chat_service.build_chat_reply("open calculator", session_id="close-current", provider=lambda *_args, **_kwargs: "fallback")
            chat_service.build_chat_reply("yes", session_id="close-current", provider=lambda *_args, **_kwargs: "fallback")
            confirm = chat_service.build_chat_reply("close this", session_id="close-current", provider=lambda *_args, **_kwargs: "fallback")
            result = chat_service.build_chat_reply("yes", session_id="close-current", provider=lambda *_args, **_kwargs: "fallback")

        self.assertTrue(confirm["requires_confirmation"])
        self.assertTrue(result["executed"])
        self.assertIn("Closed calculator", result["reply"])

    def test_screenshot_ocr_flow_uses_explicit_screen_request(self) -> None:
        explicit_context = screen_context(activity="browsing")
        screenshot_context = {**explicit_context, "screenshot": {"ok": True, "summary": "I can read this on the screen: Error 500; retry failed", "line_count": 2, "error_like": True}}

        with patch.object(service, "get_screen_context", return_value=explicit_context), patch.object(
            executor.screen_context_module,
            "get_screen_context",
            return_value=screenshot_context,
        ):
            result = chat_service.build_chat_reply("read this error", session_id="screen-read", provider=lambda *_args, **_kwargs: "fallback")

        self.assertTrue(result["executed"])
        self.assertEqual("screen_read", result["intent"])
        self.assertIn("Error 500", result["reply"])

    def test_debug_metadata_includes_screen_context_only_when_enabled(self) -> None:
        with patch.object(service, "get_screen_context", return_value=screen_context(activity="media")):
            normal = chat_service.build_chat_reply("pause it", session_id="debug-screen-off", provider=lambda *_args, **_kwargs: "fallback")
        self.assertNotIn("debug", normal)

        os.environ[chat_service.PERSONAL_ASSISTANT_DEBUG_ENV] = "1"
        with patch.object(service, "get_screen_context", return_value=screen_context(activity="media")), patch.object(
            executor.local_action_executor,
            "execute_local_action",
            return_value={"ok": True, "action": "media_key", "message": "Paused or resumed media playback.", "data": {"operation": "pause"}},
        ):
            debug = chat_service.build_chat_reply("pause it", session_id="debug-screen-on", provider=lambda *_args, **_kwargs: "fallback")

        self.assertIn("debug", debug)
        self.assertEqual("media", debug["debug"]["active_window"]["activity"])
        self.assertEqual("screen_context", debug["debug"]["chosen_action_source"])

    def test_play_relaxing_music_opens_safe_youtube_search(self) -> None:
        with patch.object(service, "get_screen_context", return_value=screen_context(activity="browsing")), patch.object(
            executor.local_action_executor,
            "execute_local_action",
            return_value={"ok": True, "action": "open_url", "message": "Opened URL.", "data": {}},
        ) as action:
            result = chat_service.build_chat_reply("play relaxing music", session_id="music", provider=lambda *_args, **_kwargs: "fallback")

        self.assertTrue(result["executed"])
        payload = action.call_args.args[0]
        self.assertEqual("open_url", payload["action"])
        self.assertIn("youtube.com/results", payload["params"]["url"])

    def test_normal_chat_still_falls_back_without_screen_context(self) -> None:
        with patch.object(service, "get_screen_context", return_value=screen_context(activity="unknown", app_name="", title="", kind="unknown", domain="")):
            result = chat_service.build_chat_reply("tell me a joke", session_id="normal-screen", provider=lambda *_args, **_kwargs: "joke reply")

        self.assertEqual("joke reply", result["reply"])
        self.assertNotEqual("personal-assistant", result["provider"])


if __name__ == "__main__":
    unittest.main()
