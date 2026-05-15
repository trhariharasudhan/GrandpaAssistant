import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from core.planner_prompt_payload import build_and_verify_planner_payload, build_planner_prompt_payload, classify_planning_risk


class PlannerPromptPayloadTests(unittest.TestCase):
    def test_payload_is_json_safe_dict(self) -> None:
        payload = build_planner_prompt_payload("architecture plan for prompt runtime")

        self.assertIsInstance(payload, dict)
        self.assertIsInstance(json.dumps(payload), str)

    def test_payload_core_fields(self) -> None:
        payload = build_planner_prompt_payload("make an architecture plan")

        self.assertEqual("planning", payload["mode"])
        self.assertFalse(payload["execution_allowed"])
        self.assertFalse(payload["tools_allowed"])
        self.assertIn("system_prompt", payload)
        self.assertIn("Planning mode:", payload["system_prompt"])

    def test_low_risk_architecture_plan(self) -> None:
        risk_level, risks, requires_confirmation = classify_planning_risk("architecture plan for docs cleanup")

        self.assertEqual("low", risk_level)
        self.assertEqual([], risks)
        self.assertFalse(requires_confirmation)

    def test_high_risk_examples(self) -> None:
        examples = [
            "delete all old files",
            "format the drive",
            "make a payment transfer",
            "use this password in the plan",
        ]

        for message in examples:
            with self.subTest(message=message):
                risk_level, risks, requires_confirmation = classify_planning_risk(message)
                self.assertEqual("high", risk_level)
                self.assertTrue(risks)
                self.assertTrue(requires_confirmation)

    def test_medium_risk_examples(self) -> None:
        examples = [
            "install these tools",
            "send message after browser automation",
            "network scanning plan",
            "UI click automation steps",
        ]

        for message in examples:
            with self.subTest(message=message):
                risk_level, risks, requires_confirmation = classify_planning_risk(message)
                self.assertIn(risk_level, {"medium", "high"})
                self.assertTrue(risks)
                self.assertTrue(requires_confirmation)

    def test_request_is_truncated(self) -> None:
        payload = build_planner_prompt_payload("x" * 200, max_request_chars=50)

        self.assertLessEqual(len(payload["user_request"]), 50)
        self.assertTrue(payload["metadata"]["request_truncated"])

    def test_sensitive_lines_are_removed(self) -> None:
        payload = build_planner_prompt_payload("normal plan\npassword: hidden\napi_key: hidden")

        self.assertIn("normal plan", payload["user_request"])
        self.assertNotIn("hidden", payload["user_request"])
        self.assertTrue(payload["metadata"]["sensitive_content_removed"])

    def test_memory_context_included_bool(self) -> None:
        payload = build_planner_prompt_payload("make a plan", memory_context={"preference": "short"})

        self.assertTrue(payload["memory_context_included"])

    def test_no_reference_folder_usage(self) -> None:
        source = (APP_DIR / "core" / "planner_prompt_payload.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))

    def test_no_command_router_dependency(self) -> None:
        source = (APP_DIR / "core" / "planner_prompt_payload.py").read_text(encoding="utf-8")

        self.assertNotIn("command_router", source)

    def test_build_and_verify_helper_returns_payload_and_verification(self) -> None:
        result = build_and_verify_planner_payload("architecture plan")

        self.assertIn("payload", result)
        self.assertIn("verification", result)
        self.assertFalse(result["verification"]["safe_to_execute"])


if __name__ == "__main__":
    unittest.main()
