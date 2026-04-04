import os
import sys

from fastapi.testclient import TestClient


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for _path in (APP_DIR, SHARED_DIR, FEATURES_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import api.web_api as web_api  # noqa: E402


def run_check(command_text="open notepad"):
    client = TestClient(web_api.app)
    print(f"[INFO] looks_like_direct_action_input={web_api._looks_like_direct_action_input(command_text)}")

    command_response = client.post("/api/command", json={"command": command_text})
    command_payload = command_response.json() if command_response.status_code == 200 else {}
    command_messages = command_payload.get("messages") or []
    command_preview = " | ".join(command_messages[:2]) if command_messages else ""
    command_ok = command_response.status_code == 200 and any(
        keyword in command_preview.lower() for keyword in ["open", "opened", "notepad", "opening"]
    )
    print(f"[INFO] api_command_status={command_response.status_code}")
    print(f"[INFO] api_command_preview={command_preview[:220]}")

    session_payload = client.post("/chat/sessions", json={"title": "direct-command-check"}).json()
    session_id = ((session_payload.get("session") or {}).get("id") or "").strip()
    if not session_id:
        print("[FAIL] Could not create session.")
        return False

    response = client.post("/chat/stream", json={"message": command_text, "session_id": session_id})
    text = response.text
    has_chunk = '"type": "chunk"' in text
    has_done = '"type": "done"' in text
    command_like_reply = any(keyword in text.lower() for keyword in ["opened", "active window", "notepad", "nextgen feature status"])

    print(f"[INFO] status_code={response.status_code}")
    print(f"[INFO] has_chunk={has_chunk}")
    print(f"[INFO] has_done={has_done}")
    print(f"[INFO] command_like_reply={command_like_reply}")
    print(f"[INFO] preview={text[:280].replace(chr(10), ' ')}")

    ok = command_ok and response.status_code == 200 and has_done and (not has_chunk) and command_like_reply
    print(f"[{'PASS' if ok else 'FAIL'}] direct_command_stream_check")
    return ok


if __name__ == "__main__":
    target = "open notepad"
    if len(sys.argv) > 1 and str(sys.argv[1]).strip():
        target = str(sys.argv[1]).strip()
    success = run_check(target)
    if not success:
        sys.exit(1)
