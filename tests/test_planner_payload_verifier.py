import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "backend" / "app"
text = str(APP_DIR)
if text not in sys.path:
    sys.path.insert(0, text)


from core.planner_payload_verifier import summarize_planner_payload_safety, verify_planner_payload
from core.planner_prompt_payload import build_and_verify_planner_payload, build_planner_prompt_payload


class PlannerPayloadVerifierTests(unittest.TestCase):
    def test_valid_low_risk_payload_passes_for_llm(self) -> None:
        payload = build_planner_prompt_payload("architecture plan for docs")
        result = verify_planner_payload(payload)

        self.assertTrue(result["valid"])
        self.assertTrue(result["safe_to_use_for_llm"])
        self.assertFalse(result["safe_to_execute"])
        self.assertEqual("low", result["risk_level"])

    def test_safe_to_execute_always_false(self) -> None:
        payload = build_planner_prompt_payload("architecture plan")

        self.assertFalse(verify_planner_payload(payload)["safe_to_execute"])
        self.assertFalse(summarize_planner_payload_safety(payload)["safe_to_execute"])

    def test_high_risk_payload_requires_confirmation(self) -> None:
        payload = build_planner_prompt_payload("delete old files")
        result = verify_planner_payload(payload)

        self.assertTrue(result["valid"])
        self.assertEqual("high", result["risk_level"])
        self.assertTrue(result["requires_confirmation"])

    def test_high_risk_without_confirmation_fails(self) -> None:
        payload = build_planner_prompt_payload("delete old files")
        payload["requires_confirmation"] = False
        result = verify_planner_payload(payload)

        self.assertFalse(result["valid"])
        self.assertFalse(result["safe_to_use_for_llm"])
        self.assertIn("high risk payloads must require confirmation", result["errors"])

    def test_execution_allowed_true_fails(self) -> None:
        payload = build_planner_prompt_payload("architecture plan")
        payload["execution_allowed"] = True

        self.assertFalse(verify_planner_payload(payload)["valid"])

    def test_tools_allowed_true_fails(self) -> None:
        payload = build_planner_prompt_payload("architecture plan")
        payload["tools_allowed"] = True

        self.assertFalse(verify_planner_payload(payload)["valid"])

    def test_missing_system_prompt_fails(self) -> None:
        payload = build_planner_prompt_payload("architecture plan")
        payload["system_prompt"] = ""

        self.assertFalse(verify_planner_payload(payload)["valid"])

    def test_missing_required_fields_fails_safely(self) -> None:
        result = verify_planner_payload({"mode": "planning"})

        self.assertFalse(result["valid"])
        self.assertTrue(result["errors"])

    def test_malformed_payload_does_not_crash(self) -> None:
        result = verify_planner_payload(None)

        self.assertFalse(result["valid"])
        self.assertIn("payload must be a dict", result["errors"])

    def test_result_does_not_include_system_prompt_or_user_request_text(self) -> None:
        payload = build_planner_prompt_payload("unique request text for verifier")
        result_text = json.dumps(verify_planner_payload(payload))

        self.assertNotIn(payload["system_prompt"], result_text)
        self.assertNotIn("unique request text for verifier", result_text)

    def test_no_reference_folder_dependency(self) -> None:
        source = (APP_DIR / "core" / "planner_payload_verifier.py").read_text(encoding="utf-8")

        self.assertNotIn("system_prompts_leaks", source)
        self.assertNotIn("reference/", source.replace("\\", "/"))

    def test_build_and_verify_helper_works(self) -> None:
        result = build_and_verify_planner_payload("architecture plan")

        self.assertIn("payload", result)
        self.assertIn("verification", result)
        self.assertTrue(result["verification"]["valid"])


if __name__ == "__main__":
    unittest.main()
