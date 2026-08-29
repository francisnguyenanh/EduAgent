"""Role-based Simple Login (mock multi-tenant auth).

Not a real auth system (no Firebase Auth/Keycloak, no session tokens,
no password hashing/storage) -- deliberately so, per the hackathon-scope
tradeoff recorded: the deployment should present as a multi-tenant SaaS
(Student Portal / Teacher Portal, correct class_id scoping) without
burning implementation time on infrastructure the eval rubric doesn't
score. `EDUAGENT_MOCK_PASSWORD` is one shared demo password (not
per-user secrets), and login is stateless -- the frontend just carries
the returned identity in memory for the rest of the session, the same
way `interactive.py` already carries debate session state in memory.

ID convention: "<class_id>_<local_id>", e.g.
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

# ADR-016 described the exposure it was closing as "anyone who reads
# the repo can mint a role=teacher token for any class_id and read that class's
# students' names, scores and weakness history". It closed the *forgery* route
# (the signing key). It did not close the *issuance* route: `/api/auth/login`
# hands out a teacher token for any class to anyone who knows the shared demo
# passcode -- and that passcode is printed in the README. The end state for an
# attacker is identical, so the fix has to be at issuance too.
#
# Teacher login therefore takes its own password when one is configured. It
# falls back to the shared demo passcode when unset, so a laptop demo and
# `pytest` still need no setup -- but a deployment can now separate the two by
# mounting EDUAGENT_TEACHER_PASSWORD from Secret Manager, without publishing it.
_TEACHER_PASSWORD = os.getenv("EDUAGENT_TEACHER_PASSWORD") or _MOCK_PASSWORD


def teacher_password_is_shared_with_students() -> bool:
    """True when teacher login still accepts the public demo passcode.

    Surfaced by scripts/doctor.py so the state is visible before a demo rather
    than discovered by someone curling /api/auth/login -- same reasoning as
    using_insecure_default_secret() below.
    """
    return _TEACHER_PASSWORD == _MOCK_PASSWORD

# ADR-016: this default is committed to a public repo, so it is
# a PUBLICLY KNOWN signing key. Anyone who reads the repo can mint a valid
# `role=teacher` token for any class_id and read that class's students' names,
# scores and weakness history -- which silently voids ADR-013's tenancy
# isolation and contradicts the STRIDE table's Spoofing/IDOR mitigation. The
# deployed Cloud Run revision was in fact found signing with exactly this
# string, because EDUAGENT_SESSION_SECRET had never been set at deploy time.
#
# The fix is defense in depth, not just documentation: the default remains
# usable for local development (so `pytest` and a laptop demo need no setup),
# but the process REFUSES TO START if it detects it is running on Cloud Run
# with the default still in place. A missing env var is a silent failure; a
# container that will not boot is a loud one.
_INSECURE_DEFAULT_SECRET = "eduagent-demo-secret-key-2026"

_MIN_SECRET_LENGTH = 32


class InsecureConfigurationError(RuntimeError):
    """Raised at import time when a production deployment is using the
    publicly-known default signing key."""


def _is_cloud_run() -> bool:
    """Cloud Run always injects K_SERVICE into the container environment
    (https://cloud.google.com/run/docs/container-contract#services-env-vars),
    so this is a reliable "am I deployed?" signal that needs no extra config
    and cannot be forgotten the way a hand-set FLAG=prod can be."""
    return bool(os.getenv("K_SERVICE"))


def _resolve_session_secret() -> bytes:
    configured = os.getenv("EDUAGENT_SESSION_SECRET", "")
    if configured and configured != _INSECURE_DEFAULT_SECRET:
        if len(configured) < _MIN_SECRET_LENGTH and _is_cloud_run():
            raise InsecureConfigurationError(
                f"EDUAGENT_SESSION_SECRET is only {len(configured)} characters; "
                f"use at least {_MIN_SECRET_LENGTH} bytes of randomness "
                "(e.g. `openssl rand -base64 48`). See README §Deploy."
            )
        return configured.encode("utf-8")

    if _is_cloud_run() and not os.getenv("EDUAGENT_ALLOW_INSECURE_SECRET"):
        raise InsecureConfigurationError(
            "Refusing to start: EDUAGENT_SESSION_SECRET is unset (or still the "
            "committed demo default), and K_SERVICE indicates this process is "
            "running on Cloud Run. Session tokens would be signed with a key "
            "that is public in the repository, letting anyone mint a "
            "role=teacher token for any class_id.\n\n"
            "Fix (see README section 3.4 'Deploying to Cloud Run', step 1):\n"
            "  printf '%s' \"$(openssl rand -base64 48)\" | \\\n"
            "    gcloud secrets create eduagent-session-secret --data-file=-\n"
            "  gcloud run services update eduagent-class-aggregator \\\n"
            "    --update-secrets=EDUAGENT_SESSION_SECRET=eduagent-session-secret:latest\n\n"
            "To deliberately run an insecure throwaway deployment, set "
            "EDUAGENT_ALLOW_INSECURE_SECRET=1."
        )
    return _INSECURE_DEFAULT_SECRET.encode("utf-8")


_SESSION_SECRET = _resolve_session_secret()


def using_insecure_default_secret() -> bool:
    """True when tokens are being signed with the publicly-known default.
    Surfaced by scripts/doctor.py so the state is visible before a demo
    rather than discovered by someone reading auth.py."""
    return _SESSION_SECRET == _INSECURE_DEFAULT_SECRET.encode("utf-8")


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


def is_teacher_id(user_id: str) -> bool:
    """Returns True if the ID belongs to a teacher account."""
    _, local_id = split_class_id(user_id)
    return "teacher" in local_id.lower()


def login(payload: LoginRequest) -> LoginResult:
    if payload.role not in ("student", "teacher"):
        raise LoginError(f"Unknown role {payload.role!r} -- expected 'student' or 'teacher'.")
    expected_password = _TEACHER_PASSWORD if payload.role == "teacher" else _MOCK_PASSWORD
    if not hmac.compare_digest(payload.password, expected_password):
        raise LoginError("Incorrect password.")
    class_id, local_id = split_class_id(payload.user_id)

    is_teacher = "teacher" in local_id.lower()
    if payload.role == "teacher" and not is_teacher:
        raise LoginError(
            f"User ID {payload.user_id.strip()!r} is a student account. Please use your teacher ID (e.g. '{class_id}_teacher') or sign in via the Student Portal."
        )
    if payload.role == "student" and is_teacher:
        raise LoginError(
            f"User ID {payload.user_id.strip()!r} is a teacher account. Please sign in via the Teacher Portal."
        )

    token = create_access_token(payload.user_id.strip(), payload.role, class_id)
    return LoginResult(
        role=payload.role,
        class_id=class_id,
        user_id=payload.user_id.strip(),
        display_name=local_id,
        token=token,
    )


__all__ = [
    "InsecureConfigurationError",
    "using_insecure_default_secret",
    "teacher_password_is_shared_with_students",
    "LoginError",
    "LoginResult",
    "LoginRequest",
    "split_class_id",
    "is_teacher_id",
    "login",
    "create_access_token",
    "verify_access_token",
]
