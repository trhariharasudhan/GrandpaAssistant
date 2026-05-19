import os
import sys
import tempfile
import json
import datetime
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
from core.personal_assistant import executor, memory_manager
from core.personal_assistant.context import clear_personal_assistant_contexts_for_tests, get_conversation_context
from core.personal_assistant.context import AssistantActionPlan
from core.personal_assistant.intent_engine import detect_intent
from core.personal_assistant.planner import build_action_plan
from core.personal_assistant.service import handle_personal_assistant_message


class PersonalAssistantLongTermMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_personal_assistant_contexts_for_tests()
        chat_service.clear_all_chat_sessions_for_tests()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_memory_path = os.environ.get(memory_manager.MEMORY_PATH_ENV)
        os.environ[memory_manager.MEMORY_PATH_ENV] = str(Path(self.temp_dir.name) / "memory.json")

    def tearDown(self) -> None:
        clear_personal_assistant_contexts_for_tests()
        chat_service.clear_all_chat_sessions_for_tests()
        if self.previous_memory_path is None:
            os.environ.pop(memory_manager.MEMORY_PATH_ENV, None)
        else:
            os.environ[memory_manager.MEMORY_PATH_ENV] = self.previous_memory_path
        self.temp_dir.cleanup()

    def test_structured_memory_creation_retrieval_update_delete_and_persistence(self) -> None:
        created = memory_manager.store_memory(
            category="favorite_apps",
            key="preferred_code_editor",
            value="VS Code",
            source="test",
            confidence=0.9,
        )
        updated = memory_manager.store_memory(
            category="favorite_apps",
            key="preferred_code_editor",
            value="Visual Studio Code",
            source="user_explicit",
            confidence=0.95,
        )
        found = memory_manager.query_memories("code editor", category="favorite_apps")

        self.assertTrue(created["ok"])
        self.assertTrue(updated["ok"])
        self.assertEqual(1, len(found))
        self.assertEqual("favorite_apps", found[0]["category"])
        self.assertEqual("preferred_code_editor", found[0]["key"])
        self.assertEqual("Visual Studio Code", found[0]["value"])
        self.assertTrue(Path(os.environ[memory_manager.MEMORY_PATH_ENV]).exists())

        forgotten = memory_manager.forget_memory("visual studio code")
        self.assertTrue(forgotten["ok"])
        self.assertEqual([], memory_manager.query_memories("visual studio code", min_confidence=0.0))

    def test_confidence_filtering_and_sensitive_memory_blocking(self) -> None:
        low = memory_manager.store_memory(category="user_preferences", key="favorite_music", value="lo-fi", confidence=0.2)
        blocked = memory_manager.store_memory(category="user_preferences", key="api_key", value="secret token 123", confidence=1.0)

        self.assertTrue(low["ok"])
        self.assertFalse(blocked["ok"])
        self.assertTrue(blocked["blocked"])
        self.assertEqual([], memory_manager.query_memories("lo-fi"))
        self.assertEqual(1, len(memory_manager.query_memories("lo-fi", min_confidence=0.0)))

    def test_explicit_and_implicit_memory_chat_flow(self) -> None:
        explicit = handle_personal_assistant_message("remember that I usually use VS Code for coding", session_id="memory-flow")
        implicit = handle_personal_assistant_message("I prefer dark mode", session_id="memory-flow")
        recall = handle_personal_assistant_message("what do you remember about me?", session_id="memory-flow")

        self.assertTrue(explicit["executed"])
        self.assertEqual("remember_this", explicit["intent"])
        self.assertTrue(implicit["executed"])
        self.assertEqual("remember_this", implicit["intent"])
        self.assertEqual("list_memories", recall["intent"])
        self.assertIn("preferred code editor", recall["reply"])
        self.assertIn("dark mode", recall["reply"])

    def test_forget_memory_and_do_not_remember_control(self) -> None:
        handle_personal_assistant_message("remember that my favorite music is lo-fi", session_id="forget-flow")
        forgotten = handle_personal_assistant_message("forget favorite music memory", session_id="forget-flow")
        opt_out = handle_personal_assistant_message("don't remember this", session_id="forget-flow")
        recall = handle_personal_assistant_message("what do you remember about me?", session_id="forget-flow")

        self.assertEqual("forget_memory", forgotten["intent"])
        self.assertTrue(forgotten["executed"])
        self.assertEqual("memory_opt_out", opt_out["intent"])
        self.assertTrue(opt_out["executed"])
        self.assertNotIn("lo-fi", recall["reply"])

    def test_sensitive_memory_is_not_saved_through_chat(self) -> None:
        result = handle_personal_assistant_message("remember that my password is swordfish", session_id="sensitive")
        recall = handle_personal_assistant_message("what do you remember about me?", session_id="sensitive")

        self.assertEqual("remember_this", result["intent"])
        self.assertFalse(result["ok"])
        self.assertIn("sensitive", result["reply"].lower())
        self.assertNotIn("swordfish", recall["reply"])

    def test_memory_supports_planning_without_overriding_explicit_intent(self) -> None:
        memory_manager.store_memory(category="favorite_apps", key="preferred_code_editor", value="VS Code", confidence=0.95)

        editor_candidate = detect_intent("open my editor")
        editor_plan = build_action_plan(editor_candidate, get_conversation_context("editor"), "open my editor")
        notepad_candidate = detect_intent("open notepad")
        notepad_plan = build_action_plan(notepad_candidate, get_conversation_context("notepad"), "open notepad")

        self.assertIsNotNone(editor_plan)
        self.assertEqual("VS Code", editor_plan.target)
        self.assertIsNotNone(notepad_plan)
        self.assertEqual("notepad", notepad_plan.target)

    def test_memory_can_personalize_music_search(self) -> None:
        memory_manager.store_memory(category="user_preferences", key="favorite_music", value="lo-fi beats", confidence=0.95)
        calls = []

        def fake_action(payload):
            calls.append(payload)
            return {"ok": True, "message": "Opened URL.", "data": payload.get("params", {})}

        with patch.object(executor.local_action_executor, "execute_local_action", side_effect=fake_action):
            result = handle_personal_assistant_message("play music", session_id="music")

        self.assertTrue(result["executed"])
        self.assertEqual("play_media_search", result["intent"])
        self.assertTrue(calls)
        self.assertIn("lo-fi", calls[0]["params"]["url"])

    def test_debug_metadata_shows_memory_candidates_without_normal_leak(self) -> None:
        normal = chat_service.build_chat_reply("I work at Lenovo", session_id="memory-debug-normal", provider=lambda *_args, **_kwargs: "fallback")
        os.environ[chat_service.PERSONAL_ASSISTANT_DEBUG_ENV] = "1"
        try:
            debug = chat_service.build_chat_reply("I work at Lenovo", session_id="memory-debug-on", provider=lambda *_args, **_kwargs: "fallback")
        finally:
            os.environ.pop(chat_service.PERSONAL_ASSISTANT_DEBUG_ENV, None)

        self.assertNotIn("debug", normal)
        self.assertIn("debug", debug)
        self.assertIn("memory", debug["debug"])
        self.assertTrue(debug["debug"]["memory"]["extracted_candidates"])

    def test_duplicate_merge_and_conflict_detection(self) -> None:
        first = memory_manager.store_memory(category="favorite_apps", key="preferred_code_editor", value="VS Code", source="implicit_preference", confidence=0.82)
        duplicate = memory_manager.store_memory(category="favorite_apps", key="preferred_code_editor", value="VS Code", source="implicit_preference", confidence=0.84)
        conflict = memory_manager.store_memory(category="favorite_apps", key="preferred_code_editor", value="Cursor", source="implicit_preference", confidence=0.72)
        conflicts = memory_manager.memory_conflicts()

        self.assertTrue(first["ok"])
        self.assertTrue(duplicate["ok"])
        self.assertFalse(conflict["ok"])
        self.assertTrue(conflict["conflict"])
        self.assertEqual(1, len(conflicts["conflicts"]))
        self.assertEqual([], memory_manager.query_memories("editor", category="favorite_apps"))

    def test_explicit_update_overrides_older_memory(self) -> None:
        memory_manager.store_memory(category="favorite_apps", key="preferred_code_editor", value="VS Code", source="implicit_preference", confidence=0.82)

        updated = handle_personal_assistant_message("update my preferred editor to Cursor", session_id="update-memory")
        candidate = detect_intent("open my editor")
        plan = build_action_plan(candidate, get_conversation_context("update-memory-open"), "open my editor")

        self.assertEqual("update_memory", updated["intent"])
        self.assertTrue(updated["executed"])
        self.assertEqual("Cursor", memory_manager.query_memories("", category="favorite_apps", key="preferred_code_editor")[0]["value"])
        self.assertEqual("Cursor", plan.target)

    def test_uncertain_conflict_asks_confirmation_in_chat(self) -> None:
        handle_personal_assistant_message("remember that I usually use VS Code for coding", session_id="conflict-chat")
        result = handle_personal_assistant_message("I use Cursor for coding", session_id="conflict-chat")

        self.assertEqual("remember_this", result["intent"])
        self.assertFalse(result["ok"])
        self.assertIn("Should I update", result["reply"])
        self.assertEqual(1, len(memory_manager.memory_conflicts()["conflicts"]))

    def test_yes_resolves_pending_conflict_to_new_value(self) -> None:
        handle_personal_assistant_message("remember that I usually use VS Code for coding", session_id="yes-conflict")
        conflict = handle_personal_assistant_message("I use Cursor for coding", session_id="yes-conflict")
        resolved = handle_personal_assistant_message("yes update it", session_id="yes-conflict")
        candidate = detect_intent("open my editor")
        plan = build_action_plan(candidate, get_conversation_context("yes-conflict-open"), "open my editor")

        self.assertFalse(conflict["ok"])
        self.assertEqual("resolve_memory_conflict", resolved["intent"])
        self.assertTrue(resolved["executed"])
        self.assertIn("Cursor", resolved["reply"])
        self.assertEqual("Cursor", memory_manager.query_memories("", category="favorite_apps", key="preferred_code_editor")[0]["value"])
        self.assertEqual("Cursor", plan.target)

    def test_no_keeps_old_value_and_clears_conflict(self) -> None:
        handle_personal_assistant_message("remember that I usually use VS Code for coding", session_id="no-conflict")
        handle_personal_assistant_message("I use Cursor for coding", session_id="no-conflict")
        resolved = handle_personal_assistant_message("keep old one", session_id="no-conflict")

        self.assertEqual("resolve_memory_conflict", resolved["intent"])
        self.assertTrue(resolved["executed"])
        self.assertIn("still VS Code", resolved["reply"])
        self.assertEqual("VS Code", memory_manager.query_memories("", category="favorite_apps", key="preferred_code_editor")[0]["value"])
        self.assertEqual([], memory_manager.memory_conflicts()["conflicts"])

    def test_cancel_clears_pending_conflict_without_change(self) -> None:
        handle_personal_assistant_message("remember that I usually use VS Code for coding", session_id="cancel-conflict")
        handle_personal_assistant_message("I use Cursor for coding", session_id="cancel-conflict")
        resolved = handle_personal_assistant_message("cancel", session_id="cancel-conflict")
        context = get_conversation_context("cancel-conflict")

        self.assertEqual("resolve_memory_conflict", resolved["intent"])
        self.assertTrue(resolved["executed"])
        self.assertEqual({}, context.pending_memory_conflict)
        self.assertEqual("VS Code", memory_manager.query_memories("", category="favorite_apps", key="preferred_code_editor")[0]["value"])
        self.assertEqual([], memory_manager.memory_conflicts()["conflicts"])

    def test_stale_pending_conflict_is_cleared_safely(self) -> None:
        context = get_conversation_context("stale-conflict")
        context.pending_memory_conflict = {
            "memory_id": "missing-memory",
            "category": "favorite_apps",
            "key": "preferred_code_editor",
            "old_value": "VS Code",
            "pending_value": "Cursor",
            "created_at": "2020-01-01T00:00:00Z",
        }
        context.pending_question = "memory_conflict"

        result = handle_personal_assistant_message("yes", session_id="stale-conflict")

        self.assertEqual("resolve_memory_conflict", result["intent"])
        self.assertFalse(result["ok"])
        self.assertIn("no longer available", result["reply"])
        self.assertEqual({}, context.pending_memory_conflict)

    def test_yes_does_not_trigger_unrelated_pending_action_while_conflict_pending(self) -> None:
        handle_personal_assistant_message("remember that I usually use VS Code for coding", session_id="priority-conflict")
        handle_personal_assistant_message("I use Cursor for coding", session_id="priority-conflict")
        context = get_conversation_context("priority-conflict")
        context.pending_plan = AssistantActionPlan(
            intent="open_app",
            action="open_app",
            tool_name="open_app",
            target="calculator",
            params={"app": "calculator"},
            requires_confirmation=True,
        )

        with patch.object(executor.local_action_executor, "execute_local_action") as action:
            result = handle_personal_assistant_message("yes", session_id="priority-conflict")

        self.assertEqual("resolve_memory_conflict", result["intent"])
        self.assertTrue(result["executed"])
        action.assert_not_called()

    def test_unresolved_conflict_is_ignored_by_planner_until_resolved(self) -> None:
        handle_personal_assistant_message("remember that I usually use VS Code for coding", session_id="ignore-conflict")
        handle_personal_assistant_message("I use Cursor for coding", session_id="ignore-conflict")
        candidate = detect_intent("open my editor")
        before = build_action_plan(candidate, get_conversation_context("ignore-conflict-open-before"), "open my editor")
        handle_personal_assistant_message("use the new one", session_id="ignore-conflict")
        after = build_action_plan(candidate, get_conversation_context("ignore-conflict-open-after"), "open my editor")

        self.assertEqual("my editor", before.target)
        self.assertEqual("Cursor", after.target)

    def test_low_quality_memory_is_rejected(self) -> None:
        result = handle_personal_assistant_message("remember that I am eating now", session_id="low-quality")

        self.assertEqual("remember_this", result["intent"])
        self.assertFalse(result["ok"])
        self.assertIn("temporary", result["reply"])
        self.assertEqual([], memory_manager.list_memories(min_confidence=0.0))

    def test_stale_memory_flagged_and_ignored_by_planner(self) -> None:
        memory_manager.store_memory(category="favorite_apps", key="preferred_code_editor", value="VS Code", source="test", confidence=0.9)
        path = Path(os.environ[memory_manager.MEMORY_PATH_ENV])
        payload = json.loads(path.read_text(encoding="utf-8"))
        old = (datetime.datetime.utcnow() - datetime.timedelta(days=365)).replace(microsecond=0).isoformat() + "Z"
        payload["memories"][0]["updated_at"] = old
        path.write_text(json.dumps(payload), encoding="utf-8")

        cleanup = memory_manager.cleanup_memory_suggestions()
        candidate = detect_intent("open my editor")
        plan = build_action_plan(candidate, get_conversation_context("stale-open"), "open my editor")

        self.assertTrue(cleanup["suggestions"])
        self.assertEqual("my editor", plan.target)

    def test_review_cleanup_and_conflict_tools_respond(self) -> None:
        memory_manager.store_memory(category="favorite_apps", key="preferred_code_editor", value="VS Code", source="implicit_preference", confidence=0.82)
        memory_manager.store_memory(category="favorite_apps", key="preferred_code_editor", value="Cursor", source="implicit_preference", confidence=0.72)

        review = handle_personal_assistant_message("review my memories", session_id="review")
        cleanup = handle_personal_assistant_message("clean old memories", session_id="review")
        conflicts = handle_personal_assistant_message("do you have any memory conflicts?", session_id="review")

        self.assertEqual("review_memories", review["intent"])
        self.assertIn("Memory review", review["reply"])
        self.assertEqual("cleanup_memories", cleanup["intent"])
        self.assertIn("cleanup", cleanup["reply"].lower())
        self.assertEqual("memory_conflicts", conflicts["intent"])
        self.assertIn("conflict", conflicts["reply"].lower())

    def test_archived_memory_is_not_used(self) -> None:
        memory_manager.store_memory(category="favorite_apps", key="preferred_code_editor", value="VS Code", source="test", confidence=0.95)
        memory_manager.forget_memory("VS Code")
        candidate = detect_intent("open my editor")
        plan = build_action_plan(candidate, get_conversation_context("archived-open"), "open my editor")

        self.assertEqual("my editor", plan.target)


if __name__ == "__main__":
    unittest.main()
