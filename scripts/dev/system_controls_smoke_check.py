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


def run_check():
    client = TestClient(web_api.app)
    failed = []

    for command, expected_tokens in CHECKS:
        response = client.post("/api/command", json={"command": command})
        payload = response.json() if response.status_code == 200 else {}
        messages = payload.get("messages") or []
        combined = _strip_tts_noise(" | ".join(messages))
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
