from __future__ import annotations

import base64
import json
import os
from typing import Any

from security.state import DATA_DIR, STATE, append_security_activity, utc_now
from utils.config import get_setting


KEY_PATH = os.path.join(DATA_DIR, "security_fernet.key")
ENVELOPE_VERSION = 1


def encryption_available() -> bool:
    try:
        from cryptography.fernet import Fernet  # noqa: F401

        return True
    except Exception:
        return False


def _encryption_enabled() -> bool:
    return bool(get_setting("security.encryption_enabled", True))


def _get_fernet():
    if not encryption_available():
        raise RuntimeError("Cryptography is not installed.")
    from cryptography.fernet import Fernet

    os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
    if not os.path.exists(KEY_PATH):
        with open(KEY_PATH, "wb") as file:
            file.write(Fernet.generate_key())
    with open(KEY_PATH, "rb") as file:
        key = file.read().strip()
    return Fernet(key)


def _mark_encryption_state() -> None:
    STATE.update(
        lambda state: state["encryption"].update(
            {
                "available": encryption_available(),
                "enabled": _encryption_enabled(),
                "key_ready": os.path.exists(KEY_PATH),
                "last_protected_at": utc_now() if os.path.exists(KEY_PATH) else state["encryption"].get("last_protected_at", ""),
            }
        )
    )


def encrypt_text(plain_text: str) -> str:
    if not _encryption_enabled():
        return plain_text
    fernet = _get_fernet()
    token = fernet.encrypt(str(plain_text).encode("utf-8"))
    _mark_encryption_state()
    return token.decode("utf-8")


def decrypt_text(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    if cipher_text.startswith("plain:"):
        return cipher_text[6:]
    if cipher_text.startswith("enc:"):
        payload = cipher_text[4:]
    else:
        payload = cipher_text
    if not _encryption_enabled():
        return payload
    fernet = _get_fernet()
    _mark_encryption_state()
    return fernet.decrypt(payload.encode("utf-8")).decode("utf-8")


def protect_db_text(plain_text: str) -> str:
    if not _encryption_enabled() or not encryption_available():
        return "plain:" + str(plain_text)
    return "enc:" + encrypt_text(plain_text)


def unprotect_db_text(value: str) -> str:
    if not isinstance(value, str):
        return ""
    if value.startswith("enc:"):
        return decrypt_text(value)
    if value.startswith("plain:"):
        return value[6:]
    return value


def _is_secure_envelope(payload: Any) -> bool:
    return isinstance(payload, dict) and payload.get("__secure__") is True and isinstance(payload.get("ciphertext"), str)


def read_encrypted_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except Exception:
        return default

    if not _is_secure_envelope(payload):
        return payload if payload is not None else default

    if not encryption_available():
        return default

    try:
        plain_text = decrypt_text(payload.get("ciphertext", ""))
        decoded = json.loads(plain_text)
        return decoded if decoded is not None else default
    except Exception:
        return default


def write_encrypted_json(path: str, payload: Any, *, protect: bool = True) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if protect and _encryption_enabled() and encryption_available():
        plain_text = json.dumps(payload, ensure_ascii=False)
        envelope = {
            "__secure__": True,
            "version": ENVELOPE_VERSION,
            "ciphertext": encrypt_text(plain_text),
        }
        with open(path, "w", encoding="utf-8") as file:
            json.dump(envelope, file, ensure_ascii=False, indent=2)
        _mark_encryption_state()
        return

    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=4)


def encrypt_json_file(path: str) -> tuple[bool, str]:
    current = read_encrypted_json(path, None)
    if current is None:
        return False, "That file does not exist or could not be read."
    write_encrypted_json(path, current, protect=True)
    append_security_activity(
        "data_encrypted",
        source="encryption",
        message=f"Protected {os.path.basename(path)}",
        metadata={"path": os.path.abspath(path)},
    )
    return True, f"Protected {os.path.basename(path)}."


def encryption_status_payload() -> dict[str, Any]:
    _mark_encryption_state()
    snapshot = STATE.snapshot().get("encryption", {})
    protected_targets = list(snapshot.get("protected_targets") or [])
    return {
        "available": bool(snapshot.get("available")),
        "enabled": bool(snapshot.get("enabled")),
        "key_ready": bool(snapshot.get("key_ready")),
        "key_path": os.path.abspath(KEY_PATH),
        "protected_targets": protected_targets,
        "last_protected_at": snapshot.get("last_protected_at", ""),
    }


def remember_protected_target(path: str) -> None:
    resolved = os.path.abspath(path)

    def _update(state: dict[str, Any]) -> None:
        encryption = state.setdefault("encryption", {})
        targets = list(encryption.get("protected_targets") or [])
        if resolved not in targets:
            targets.append(resolved)
        encryption["protected_targets"] = targets[-20:]
        encryption["last_protected_at"] = utc_now()
        encryption["available"] = encryption_available()
        encryption["enabled"] = _encryption_enabled()
        encryption["key_ready"] = os.path.exists(KEY_PATH)

    STATE.update(_update)

