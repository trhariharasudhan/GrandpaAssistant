from __future__ import annotations

import contextlib
import hashlib
import math
import os
import tempfile
import time
from typing import Any

from security.encryption_utils import read_encrypted_json, remember_protected_target, write_encrypted_json
from security.state import STATE, VOICE_PROFILE_PATH, append_security_activity, utc_now, utc_timestamp
from utils.config import get_setting

try:
    import numpy as np
except Exception:  # pragma: no cover - runtime guard
    np = None


def _compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _voice_auth_threshold() -> float:
    try:
        return max(0.5, min(0.99, float(get_setting("security.voice_auth_threshold", 0.82) or 0.82)))
    except Exception:
        return 0.82


def _session_timeout_seconds() -> int:
    try:
        return max(60, int(get_setting("security.session_timeout_seconds", 900) or 900))
    except Exception:
        return 900


def _admin_session_timeout_seconds() -> int:
    try:
        return max(60, int(get_setting("security.admin_session_timeout_seconds", 300) or 300))
    except Exception:
        return 300


def _failed_attempt_limit() -> int:
    try:
        return max(2, int(get_setting("security.failed_attempt_limit", 3) or 3))
    except Exception:
        return 3


def _lockout_seconds() -> int:
    try:
        return max(30, int(get_setting("security.lockout_seconds", 300) or 300))
    except Exception:
        return 300


def _pin_hash(pin: str, salt_hex: str) -> str:
    return hashlib.scrypt(
        str(pin).encode("utf-8"),
        salt=bytes.fromhex(salt_hex),
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    ).hex()


def _activate_session(method: str, *, admin: bool = False) -> None:
    now_ts = utc_timestamp()
    now_iso = utc_now()

    def _update(state: dict[str, Any]) -> None:
        auth = state.setdefault("auth", {})
        auth["session_expires_at"] = now_ts + _session_timeout_seconds()
        if admin:
            auth["admin_session_expires_at"] = now_ts + _admin_session_timeout_seconds()
        auth["last_auth_method"] = method
        auth["last_successful_auth_at"] = now_iso
        auth["failed_attempts"] = 0
        auth["lockout_until"] = 0.0

    STATE.update(_update)
    append_security_activity(
        "authentication_success",
        source="auth",
        message=f"{method} authentication succeeded",
        metadata={"admin": admin},
    )


def record_auth_failure(method: str, detail: str) -> None:
    def _update(state: dict[str, Any]) -> None:
        auth = state.setdefault("auth", {})
        auth["failed_attempts"] = int(auth.get("failed_attempts", 0) or 0) + 1
        auth["failed_attempt_window_started_at"] = auth.get("failed_attempt_window_started_at") or utc_now()
        if auth["failed_attempts"] >= _failed_attempt_limit():
            auth["lockout_until"] = utc_timestamp() + _lockout_seconds()

    snapshot = STATE.update(_update)
    append_security_activity(
        "authentication_failed",
        level="warning",
        source="auth",
        message=detail,
        metadata={
            "method": method,
            "failed_attempts": snapshot.get("auth", {}).get("failed_attempts", 0),
            "lockout_until": snapshot.get("auth", {}).get("lockout_until", 0.0),
        },
    )


def _read_voice_profile() -> dict[str, Any]:
    return read_encrypted_json(VOICE_PROFILE_PATH, {"embedding": [], "sample_path": "", "updated_at": ""})


def _write_voice_profile(payload: dict[str, Any]) -> None:
    write_encrypted_json(VOICE_PROFILE_PATH, payload, protect=True)
    remember_protected_target(VOICE_PROFILE_PATH)


def _default_voice_sample_candidate() -> str:
    candidate = _compact_text(get_setting("voice.custom_voice_sample_path", ""))
    if candidate and os.path.exists(candidate):
        return os.path.abspath(candidate)
    roots = [
        os.path.join(os.path.dirname(VOICE_PROFILE_PATH), "voice_profiles"),
        os.path.join(os.path.dirname(VOICE_PROFILE_PATH), "voices", "custom"),
    ]
    for root in roots:
        if not os.path.isdir(root):
            continue
        for filename in os.listdir(root):
            if filename.lower().endswith(".wav"):
                return os.path.abspath(os.path.join(root, filename))
    return ""


def _capture_voice_sample(seconds: float = 3.0, sample_rate: int = 16000) -> tuple[str, str]:
    try:
        import sounddevice as sd
        import soundfile as sf
    except Exception:
        return "", "Voice recording libraries are not installed."

    seconds = max(1.5, min(8.0, float(seconds)))
    fd, sample_path = tempfile.mkstemp(prefix="voice_auth_", suffix=".wav")
    os.close(fd)
    try:
        audio = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="float32")
        sd.wait()
        sf.write(sample_path, audio, sample_rate)
        return sample_path, "Voice sample captured."
    except Exception as error:
        with contextlib.suppress(OSError):
            os.remove(sample_path)
        return "", f"Failed to capture voice sample: {error}"


def _extract_voice_embedding(sample_path: str) -> tuple[list[float], str]:
    if np is None:
        return [], "NumPy is not available for voice authentication."
    if not sample_path or not os.path.exists(sample_path):
        return [], "Voice sample file was not found."
    try:
        import librosa
    except Exception:
        return [], "Librosa is not installed."

    try:
        audio, sample_rate = librosa.load(sample_path, sr=16000, mono=True)
        if audio is None or len(audio) < 16000:
            return [], "Voice sample is too short. Please record at least one second."
        mfcc = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=20)
        spectral = librosa.feature.spectral_centroid(y=audio, sr=sample_rate)
        zcr = librosa.feature.zero_crossing_rate(audio)
        rms = librosa.feature.rms(y=audio)
        embedding = np.concatenate(
            [
                np.mean(mfcc, axis=1),
                np.std(mfcc, axis=1),
                np.mean(spectral, axis=1),
                np.std(spectral, axis=1),
                np.mean(zcr, axis=1),
                np.mean(rms, axis=1),
            ]
        )
        norm = np.linalg.norm(embedding)
        if norm == 0:
            return [], "Voice sample was too quiet to build a profile."
        embedding = embedding / norm
        return embedding.astype(float).tolist(), "Voice embedding ready."
    except Exception as error:
        return [], f"Failed to analyze voice sample: {error}"


def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    if not vector_a or not vector_b or len(vector_a) != len(vector_b):
        return 0.0
    numerator = sum(a * b for a, b in zip(vector_a, vector_b))
    denominator_a = math.sqrt(sum(a * a for a in vector_a))
    denominator_b = math.sqrt(sum(b * b for b in vector_b))
    if not denominator_a or not denominator_b:
        return 0.0
    return numerator / (denominator_a * denominator_b)


def is_voice_profile_enrolled() -> bool:
    payload = _read_voice_profile()
    return bool(payload.get("embedding"))


def enroll_user_voice(sample_path: str = "", *, seconds: float = 4.0) -> tuple[bool, str]:
    resolved_sample = os.path.abspath(sample_path) if _compact_text(sample_path) else _default_voice_sample_candidate()
    cleanup_path = ""
    if not resolved_sample:
        resolved_sample, message = _capture_voice_sample(seconds=seconds)
        if not resolved_sample:
            return False, message
        cleanup_path = resolved_sample

    embedding, message = _extract_voice_embedding(resolved_sample)
    if not embedding:
        with contextlib.suppress(OSError):
            if cleanup_path:
                os.remove(cleanup_path)
        return False, message

    payload = {
        "embedding": embedding,
        "sample_path": os.path.abspath(resolved_sample),
        "updated_at": utc_now(),
    }
    _write_voice_profile(payload)
    append_security_activity(
        "voice_profile_enrolled",
        source="auth",
        message="Voice authentication profile enrolled.",
        metadata={"sample_path": payload["sample_path"]},
    )
    return True, "Voice authentication profile saved."


def verify_user_voice(sample_path: str = "", *, seconds: float = 3.0, activate_session: bool = True) -> tuple[bool, str, float]:
    profile = _read_voice_profile()
    stored_embedding = profile.get("embedding") or []
    if not stored_embedding:
        return False, "No voice authentication profile is enrolled yet.", 0.0

    resolved_sample = os.path.abspath(sample_path) if _compact_text(sample_path) else ""
    cleanup_path = ""
    if not resolved_sample:
        resolved_sample, message = _capture_voice_sample(seconds=seconds)
        if not resolved_sample:
            return False, message, 0.0
        cleanup_path = resolved_sample

    current_embedding, message = _extract_voice_embedding(resolved_sample)
    if cleanup_path:
        with contextlib.suppress(OSError):
            os.remove(cleanup_path)
    if not current_embedding:
        return False, message, 0.0

    similarity = _cosine_similarity(stored_embedding, current_embedding)
    if similarity >= _voice_auth_threshold():
        if activate_session:
            _activate_session("voice")
        return True, f"Voice verified with score {similarity:.2f}.", similarity

    record_auth_failure("voice", f"Voice verification failed with score {similarity:.2f}.")
    return False, f"Voice did not match with score {similarity:.2f}.", similarity


def verify_face_identity(*, activate_session: bool = True) -> tuple[bool, str]:
    try:
        from features.security.face_verification import verify_user_face
    except Exception as error:
        return False, f"Face verification is unavailable: {error}"

    success, message = verify_user_face()
    if success and activate_session:
        _activate_session("face")
        return True, message
    if not success:
        record_auth_failure("face", message)
    return success, message


def is_face_profile_enrolled() -> bool:
    try:
        from features.security.face_verification import is_face_enrolled

        return bool(is_face_enrolled())
    except Exception:
        return False


def set_security_pin(pin: str) -> tuple[bool, str]:
    normalized = "".join(ch for ch in str(pin) if ch.isdigit())
    if len(normalized) < 4:
        return False, "Security PIN should be at least 4 digits."
    salt = os.urandom(16).hex()
    hashed = _pin_hash(normalized, salt)

    def _update(state: dict[str, Any]) -> None:
        auth = state.setdefault("auth", {})
        auth["pin_salt"] = salt
        auth["pin_hash"] = hashed
        auth["pin_configured"] = True

    STATE.update(_update)
    append_security_activity("pin_configured", source="auth", message="Security PIN configured.")
    return True, "Security PIN saved."


def verify_security_pin(pin: str, *, activate_session: bool = True, admin: bool = False) -> tuple[bool, str]:
    normalized = "".join(ch for ch in str(pin) if ch.isdigit())
    auth = STATE.snapshot().get("auth", {})
    if not auth.get("pin_configured"):
        return False, "No security PIN is configured yet."
    salt = auth.get("pin_salt", "")
    stored_hash = auth.get("pin_hash", "")
    if not salt or not stored_hash:
        return False, "Security PIN data is incomplete."
    if _pin_hash(normalized, salt) != stored_hash:
        record_auth_failure("pin", "Security PIN verification failed.")
        return False, "Security PIN did not match."
    if activate_session:
        _activate_session("pin", admin=admin)
    return True, "Security PIN verified."


def is_locked_out() -> bool:
    auth = STATE.snapshot().get("auth", {})
    return float(auth.get("lockout_until", 0.0) or 0.0) > utc_timestamp()


def has_active_security_session() -> bool:
    auth = STATE.snapshot().get("auth", {})
    return float(auth.get("session_expires_at", 0.0) or 0.0) > utc_timestamp()


def admin_mode_active() -> bool:
    auth = STATE.snapshot().get("auth", {})
    return float(auth.get("admin_session_expires_at", 0.0) or 0.0) > utc_timestamp()


def enable_admin_mode() -> tuple[bool, str]:
    if not has_active_security_session():
        return False, "Authentication is required before admin mode can be enabled."
    _activate_session(STATE.snapshot().get("auth", {}).get("last_auth_method", "session"), admin=True)
    return True, "Security admin mode is enabled."


def disable_admin_mode() -> tuple[bool, str]:
    def _update(state: dict[str, Any]) -> None:
        state.setdefault("auth", {})["admin_session_expires_at"] = 0.0

    STATE.update(_update)
    append_security_activity("admin_mode_disabled", source="auth", message="Security admin mode disabled.")
    return True, "Security admin mode is disabled."


def enable_lockdown(reason: str) -> tuple[bool, str]:
    clean_reason = _compact_text(reason) or "security request"

    def _update(state: dict[str, Any]) -> None:
        auth = state.setdefault("auth", {})
        auth["lockdown"] = True
        auth["lockdown_reason"] = clean_reason
        auth["last_lockdown_at"] = utc_now()

    STATE.update(_update)
    append_security_activity(
        "assistant_lockdown_enabled",
        level="warning",
        source="auth",
        message=f"Assistant lockdown enabled: {clean_reason}",
    )
    return True, f"Assistant lockdown is now enabled because of {clean_reason}."


def disable_lockdown() -> tuple[bool, str]:
    def _update(state: dict[str, Any]) -> None:
        auth = state.setdefault("auth", {})
        auth["lockdown"] = False
        auth["lockdown_reason"] = ""

    STATE.update(_update)
    append_security_activity("assistant_lockdown_disabled", source="auth", message="Assistant lockdown disabled.")
    return True, "Assistant lockdown is now disabled."


def auth_status_payload() -> dict[str, Any]:
    auth = STATE.snapshot().get("auth", {})
    profile = _read_voice_profile()
    return {
        "session_active": has_active_security_session(),
        "admin_mode_active": admin_mode_active(),
        "last_auth_method": auth.get("last_auth_method", ""),
        "last_successful_auth_at": auth.get("last_successful_auth_at", ""),
        "pin_configured": bool(auth.get("pin_configured")),
        "voice_profile_enrolled": bool(profile.get("embedding")),
        "voice_profile_sample_path": profile.get("sample_path", ""),
        "face_profile_enrolled": is_face_profile_enrolled(),
        "voice_auth_threshold": _voice_auth_threshold(),
        "lockout_until": float(auth.get("lockout_until", 0.0) or 0.0),
        "failed_attempts": int(auth.get("failed_attempts", 0) or 0),
        "lockdown": bool(auth.get("lockdown")),
        "lockdown_reason": auth.get("lockdown_reason", ""),
    }

