import os
import sys
import tempfile
import uuid
from contextlib import contextmanager

from fastapi.testclient import TestClient


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
APP_DIR = os.path.join(ROOT, "backend", "app")
SHARED_DIR = os.path.join(APP_DIR, "shared")
FEATURES_DIR = os.path.join(APP_DIR, "features")
for _path in (APP_DIR, SHARED_DIR, FEATURES_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import api.web_api as web_api  # noqa: E402
import app_data_store  # noqa: E402
import brain.database as brain_database  # noqa: E402


CHECKS = [
    ("admin status", ["administrator", "admin"]),
    ("focus assist status", ["do not disturb", "focus assist"]),
    ("turn on focus assist", ["do not disturb", "focus assist"]),
    ("turn off focus assist", ["do not disturb", "focus assist"]),
    ("camera status", ["camera"]),
    ("microphone status", ["microphone", "mic"]),
    ("open settings and go to system", ["opening", "system"]),
    ("open settings and go to bluetooth and devices", ["opening", "bluetooth"]),
    ("open settings and go to network and internet", ["opening", "network"]),
    ("open privacy & security", ["opening", "privacy"]),
    ("go to windows update and search update history", ["opening", "windows update", "searched"]),
    ("turn on energy saver", ["toggled", "energy saver", "opening"]),
    ("turn off energy saver", ["toggled", "energy saver", "opening"]),
    ("turn on night light", ["toggled", "night light", "opening"]),
    ("turn off night light", ["toggled", "night light", "opening"]),
    ("display mode duplicate", ["display mode", "duplicate"]),
    ("display mode extend", ["display mode", "extend"]),
]


def _strip_tts_noise(text):
    cleaned = (text or "").strip()
    marker = "tts error:"
    idx = cleaned.lower().find(marker)
    if idx >= 0:
        cleaned = cleaned[:idx].strip()
    return cleaned


@contextmanager
def _temporary_database():
    original_brain_db_path = brain_database.DB_PATH
    original_app_db_path = app_data_store.DB_PATH
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = os.path.join(temp_dir, "assistant.db")
        brain_database.DB_PATH = temp_db_path
        app_data_store.DB_PATH = temp_db_path
        try:
            yield
        finally:
            brain_database.DB_PATH = original_brain_db_path
            app_data_store.DB_PATH = original_app_db_path


def _auth_headers(client):
    username = f"smoke_{uuid.uuid4().hex[:10]}"
    password = "SmokePass123!"
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": password,
            "display_name": "System Controls Smoke",
            "device_name": "system-controls-smoke",
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"Could not create smoke-test user: {response.status_code} {response.text}")
    token = response.json().get("token", "")
    if not token:
        raise RuntimeError("Smoke-test authentication did not return a session token.")
    return {"Authorization": f"Bearer {token}"}


def _run_command(client, headers, command):
    response = client.post("/api/command", json={"command": command}, headers=headers)
    payload = response.json() if response.status_code == 200 else {}

    if payload.get("requires_confirmation") and payload.get("confirmation_id"):
        response = client.post(
            "/api/command",
            json={"command": command, "confirmation_id": payload["confirmation_id"]},
            headers=headers,
        )
        payload = response.json() if response.status_code == 200 else {}

    messages = payload.get("messages") or []
    combined = _strip_tts_noise(" | ".join(messages))

    if response.status_code == 200 and "please confirm this" in combined.lower():
        response = client.post("/api/command", json={"command": "yes"}, headers=headers)
        payload = response.json() if response.status_code == 200 else {}
        messages = payload.get("messages") or []
        combined = _strip_tts_noise(" | ".join(messages))

    return response, combined


def run_check():
    failed = []

    with _temporary_database():
        client = TestClient(web_api.app)
        headers = _auth_headers(client)

        for command, expected_tokens in CHECKS:
            response, combined = _run_command(client, headers, command)
            lowered = combined.lower()
            ok = response.status_code == 200 and bool(combined) and any(
                token in lowered for token in expected_tokens
            )
            print(f"[{'PASS' if ok else 'FAIL'}] {command}")
            print(f"  -> status={response.status_code}")
            print(f"  -> reply={combined[:260]}")
            if not ok:
                failed.append((command, response.status_code, combined))

    if failed:
        print(f"\n[FAIL] system_controls_smoke_check ({len(failed)} failed)")
        for command, status, reply in failed[:6]:
            print(f"  - {command} | status={status} | reply={reply[:180]}")
        return False

    print("\n[PASS] system_controls_smoke_check")
    return True


if __name__ == "__main__":
    success = run_check()
    if not success:
        sys.exit(1)
