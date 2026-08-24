"""ĐỢT 4 #1 -- Role-based Simple Login (mock multi-tenant auth).

Not a real auth system (no Firebase Auth/Keycloak, no session tokens,
no password hashing/storage) -- deliberately so, per the hackathon-scope
tradeoff in TODO.md's ĐỢT 4: a judge should feel a multi-tenant SaaS
(Student Portal / Teacher Portal, correct class_id scoping) without
burning implementation time on infrastructure the eval rubric doesn't
score. `EDUAGENT_MOCK_PASSWORD` is one shared demo password (not
per-user secrets), and login is stateless -- the frontend just carries
the returned identity in memory for the rest of the session, the same
way `interactive.py` already carries debate session state in memory.

ID convention (see TODO.md ĐỢT 4): "<class_id>_<local_id>", e.g.
"c1_stu01" or "12A1_NguyenAn" -- class_id is everything before the
FIRST underscore, local_id is everything after it. A bare ID with no
underscore is rejected (a class_id can never be inferred from nothing).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

from pydantic import BaseModel

_MOCK_PASSWORD = os.getenv("EDUAGENT_MOCK_PASSWORD", "eduagent2026")
_SESSION_SECRET = os.getenv("EDUAGENT_SESSION_SECRET", "eduagent-demo-secret-key-2026").encode("utf-8")


class LoginError(ValueError):
    """Raised for a malformed ID or a wrong password -- both map to 401 in server.py."""


@dataclass(frozen=True)
class LoginResult:
    role: str  # "student" | "teacher"
    class_id: str
    user_id: str  # the full "<class_id>_<local_id>" id, used as student_id/teacher_id downstream
    display_name: str
    token: str = ""


class LoginRequest(BaseModel):
    role: str  # "student" | "teacher"
    user_id: str
    password: str


def create_access_token(user_id: str, role: str, class_id: str, expires_in_seconds: int = 86400) -> str:
    """Issues a stateless HMAC-signed token carrying identity and scoped class_id."""
    import base64

    payload = {
        "user_id": user_id,
        "role": role,
        "class_id": class_id,
        "exp": int(time.time()) + expires_in_seconds,
    }
    raw_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(raw_payload).decode("utf-8")
    signature = hmac.new(_SESSION_SECRET, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{signature}"


def verify_access_token(token: str) -> dict:
    """Verifies HMAC signature and expiration; returns payload dict or raises LoginError."""
    import base64

    if not token or "." not in token:
        raise LoginError("Malformed token.")
    b64_payload, signature = token.split(".", 1)
    expected_sig = hmac.new(_SESSION_SECRET, b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        raise LoginError("Invalid token signature.")

    try:
        raw_payload = base64.urlsafe_b64decode(b64_payload.encode("utf-8"))
        payload = json.loads(raw_payload.decode("utf-8"))
    except Exception as exc:
        raise LoginError("Failed to decode token payload.") from exc

    if payload.get("exp", 0) < int(time.time()):
        raise LoginError("Token has expired.")

    return payload


def split_class_id(user_id: str) -> tuple[str, str]:
    """"c1_stu01" -> ("c1", "stu01"). Raises LoginError if there's no
    underscore to split on (per the ID convention above)."""
    user_id = user_id.strip()
    if "_" not in user_id:
        raise LoginError(f"Invalid ID format {user_id!r} -- expected '<class_id>_<local_id>', e.g. 'c1_stu01'.")
    class_id, _, local_id = user_id.partition("_")
    if not class_id or not local_id:
        raise LoginError(f"Invalid ID format {user_id!r} -- both class_id and local_id must be non-empty.")
    return class_id, local_id


def login(payload: LoginRequest) -> LoginResult:
    if payload.role not in ("student", "teacher"):
        raise LoginError(f"Unknown role {payload.role!r} -- expected 'student' or 'teacher'.")
    if payload.password != _MOCK_PASSWORD:
        raise LoginError("Incorrect password.")
    class_id, local_id = split_class_id(payload.user_id)
    token = create_access_token(payload.user_id.strip(), payload.role, class_id)
    return LoginResult(
        role=payload.role,
        class_id=class_id,
        user_id=payload.user_id.strip(),
        display_name=local_id,
        token=token,
    )


__all__ = [
    "LoginError",
    "LoginResult",
    "LoginRequest",
    "split_class_id",
    "login",
    "create_access_token",
    "verify_access_token",
]
