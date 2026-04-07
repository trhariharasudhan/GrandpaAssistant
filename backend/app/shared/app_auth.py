import base64
import datetime
import hashlib
import hmac
import os
import re
import secrets
from typing import Any

from app_data_store import (
    count_users,
    create_session,
    create_user,
    get_audit_log,
    get_session_by_token_hash,
    get_user_by_id,
    get_user_by_username,
    list_users,
    log_audit_event,
    revoke_session,
    touch_session,
    update_user_last_login,
)
from utils.config import get_setting


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
AUTH_SECRET_PATH = os.path.join(DATA_DIR, "app_auth_secret.txt")
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
VALID_ROLES = {"admin", "user"}
DEFAULT_SESSION_TTL_HOURS = 24 * 7


def _utc_now() -> datetime.datetime:
    return datetime.datetime.utcnow()


def _utc_now_text() -> str:
    return _utc_now().isoformat() + "Z"


def _parse_timestamp(value: str) -> datetime.datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1]
    try:
        return datetime.datetime.fromisoformat(text)
    except ValueError:
        return None


def _load_or_create_secret() -> bytes:
    env_secret = os.getenv("GRANDPA_ASSISTANT_AUTH_SECRET", "").strip()
    if env_secret:
        return env_secret.encode("utf-8")

    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(AUTH_SECRET_PATH):
        try:
            with open(AUTH_SECRET_PATH, "rb") as file:
                payload = file.read().strip()
            if payload:
                return payload
        except Exception:
            pass

    payload = secrets.token_hex(32).encode("utf-8")
    with open(AUTH_SECRET_PATH, "wb") as file:
        file.write(payload)
    return payload


def _session_ttl_hours() -> int:
    try:
        configured = get_setting("auth.session_ttl_hours", DEFAULT_SESSION_TTL_HOURS)
        return max(
            1,
            int(
                os.getenv(
                    "GRANDPA_ASSISTANT_SESSION_TTL_HOURS",
                    configured,
                )
            ),
        )
    except Exception:
        return DEFAULT_SESSION_TTL_HOURS


def _normalize_username(username: str) -> str:
    return str(username or "").strip().lower()


def _hash_password(password: str, salt_text: str | None = None) -> tuple[str, str]:
    salt_bytes = (
        base64.urlsafe_b64decode(salt_text.encode("utf-8"))
        if salt_text
        else os.urandom(16)
    )
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 240000)
    return (
        base64.urlsafe_b64encode(salt_bytes).decode("utf-8"),
        base64.urlsafe_b64encode(derived).decode("utf-8"),
    )


def _verify_password(password: str, salt_text: str, expected_hash: str) -> bool:
    _salt, candidate_hash = _hash_password(password, salt_text)
    return hmac.compare_digest(candidate_hash, expected_hash)


def _hash_token(token: str) -> str:
    secret = _load_or_create_secret()
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()


def _serialize_user(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "id": row.get("id"),
        "username": row.get("username"),
        "display_name": row.get("display_name"),
        "role": row.get("role", "user"),
        "is_active": bool(row.get("is_active", 1)),
        "created_at": row.get("created_at", ""),
        "updated_at": row.get("updated_at", ""),
        "last_login_at": row.get("last_login_at", ""),
    }


def auth_bootstrap_status() -> dict[str, Any]:
    user_count = count_users()
    return {
        "enabled": True,
        "has_users": user_count > 0,
        "user_count": user_count,
        "session_ttl_hours": _session_ttl_hours(),
        "roles": sorted(VALID_ROLES),
    }


def register_app_user(
    username: str,
    password: str,
    *,
    display_name: str = "",
    role: str = "user",
) -> dict[str, Any]:
    normalized_username = _normalize_username(username)
    if not USERNAME_PATTERN.match(normalized_username):
        raise ValueError("Username must be 3-32 characters and use letters, numbers, dot, dash, or underscore.")

    if len(str(password or "")) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    if count_users() > 0 and not get_setting("auth.allow_self_signup", True):
        raise ValueError("Self signup is disabled.")

    if get_user_by_username(normalized_username):
        raise ValueError("That username already exists.")

    user_count = count_users()
    resolved_role = "admin" if user_count == 0 else str(role or "user").strip().lower()
    if resolved_role not in VALID_ROLES:
        resolved_role = "user"

    safe_display_name = str(display_name or normalized_username).strip() or normalized_username
    salt_text, password_hash = _hash_password(password)
    created = create_user(
        normalized_username,
        safe_display_name,
        password_hash,
        salt_text,
        role=resolved_role,
    )
    user_payload = _serialize_user(created)
    log_audit_event(
        "auth",
        "user_registered",
        user_id=user_payload.get("id") if user_payload else None,
        payload={"username": normalized_username, "role": resolved_role},
    )
    return {
        "user": user_payload,
        "bootstrap": auth_bootstrap_status(),
        "first_user_admin": user_count == 0,
    }


def login_app_user(
    username: str,
    password: str,
    *,
    user_agent: str = "",
    device_name: str = "",
) -> dict[str, Any]:
    normalized_username = _normalize_username(username)
    row = get_user_by_username(normalized_username)
    user = dict(row) if row else None
    if not user or not bool(user.get("is_active", 1)):
        log_audit_event("auth", "login_failed", payload={"username": normalized_username, "reason": "missing_user"})
        raise ValueError("Invalid username or password.")

    if not _verify_password(password, user.get("password_salt", ""), user.get("password_hash", "")):
        log_audit_event("auth", "login_failed", user_id=user.get("id"), payload={"username": normalized_username, "reason": "bad_password"})
        raise ValueError("Invalid username or password.")

    token = secrets.token_urlsafe(48)
    expires_at = (_utc_now() + datetime.timedelta(hours=_session_ttl_hours())).isoformat() + "Z"
    create_session(
        int(user["id"]),
        _hash_token(token),
        expires_at,
        device_name=device_name,
        user_agent=user_agent,
    )
    update_user_last_login(int(user["id"]))
    fresh_user_row = get_user_by_id(int(user["id"]))
    log_audit_event(
        "auth",
        "login_succeeded",
        user_id=int(user["id"]),
        payload={"device_name": device_name, "user_agent": user_agent[:240]},
    )
    return {
        "token": token,
        "expires_at": expires_at,
        "user": _serialize_user(dict(fresh_user_row) if fresh_user_row else user),
    }


def authenticate_app_token(token: str, *, touch: bool = True) -> dict[str, Any] | None:
    candidate = str(token or "").strip()
    if not candidate:
        return None

    session = get_session_by_token_hash(_hash_token(candidate))
    if not session:
        return None
    if session.get("revoked_at"):
        return None

    expires_at = _parse_timestamp(str(session.get("expires_at") or ""))
    if not expires_at or expires_at <= _utc_now():
        revoke_session(_hash_token(candidate))
        return None

    user_row = get_user_by_id(int(session["user_id"]))
    user = dict(user_row) if user_row else None
    if not user or not bool(user.get("is_active", 1)):
        return None

    if touch:
        touch_session(_hash_token(candidate))

    return {
        "user": _serialize_user(user),
        "session": {
            "expires_at": session.get("expires_at", ""),
            "created_at": session.get("created_at", ""),
            "last_seen_at": session.get("last_seen_at", ""),
            "device_name": session.get("device_name", ""),
        },
    }


def logout_app_token(token: str) -> None:
    candidate = str(token or "").strip()
    if not candidate:
        return
    session = get_session_by_token_hash(_hash_token(candidate))
    if session:
        log_audit_event("auth", "logout", user_id=session.get("user_id"), payload={"device_name": session.get("device_name", "")})
    revoke_session(_hash_token(candidate))


def require_admin(payload: dict[str, Any] | None) -> dict[str, Any]:
    user = (payload or {}).get("user") if isinstance(payload, dict) else None
    if not user:
        raise PermissionError("Authentication required.")
    if user.get("role") != "admin":
        raise PermissionError("Admin access required.")
    return user


def auth_status_payload() -> dict[str, Any]:
    return {
        **auth_bootstrap_status(),
        "users": list_users(limit=20),
        "recent_audit": get_audit_log(category="auth", limit=20),
        "generated_at": _utc_now_text(),
    }
