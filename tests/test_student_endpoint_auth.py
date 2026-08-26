"""ĐỢT 12 NHÓM 2 -- tests for the two protections added to the student-facing
debate endpoints: ownership authorization and token-bucket rate limiting.

The audit's finding was that `/api/debate/{start,start-with-image,
start-with-gdoc,turn,reflect}` had NO authentication at all while every
`/api/classes/*` route did, on a service deployed --allow-unauthenticated.
Anyone could write into any student's Firestore profile and burn Vertex AI
quota. These tests exist so that regression is caught rather than re-audited.
"""

from __future__ import annotations

import base64
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from eduagent.auth import create_access_token
from eduagent.rate_limit import (
    RateLimitExceeded,
    RateLimitPolicy,
    TokenBucketLimiter,
    client_key,
    debate_limiter,
)
from eduagent.server import app

client = TestClient(app)

_VICTIM = "c1_stu01"
_ATTACKER = "c1_stu99"


def _headers(user_id: str, role: str = "student", class_id: str | None = None) -> dict:
    token = create_access_token(user_id=user_id, role=role, class_id=class_id or user_id.split("_", 1)[0])
    return {"Authorization": f"Bearer {token}"}


def _start_body(student_id: str = _VICTIM) -> dict:
    return {"essay_text": "Cats are great.", "student_id": student_id, "class_id": "c1"}


# ---------------------------------------------------------------- no token ----

_DEBATE_ROUTES = [
    ("/api/debate/start", {"essay_text": "x", "student_id": _VICTIM, "class_id": "c1"}),
    ("/api/debate/start-with-image", {"image_base64": base64.b64encode(b"f").decode(), "student_id": _VICTIM, "class_id": "c1"}),
    ("/api/debate/start-with-gdoc", {"gdoc_url": "https://docs.google.com/document/d/abc/edit", "student_id": _VICTIM, "class_id": "c1"}),
    # ĐỢT 15 #2: this payload is session-only now. The no-token / forged-token
    # checks below still apply, because the token is verified BEFORE the session
    # lookup (same ordering as /api/debate/turn).
    ("/api/debate/reflect", {"session_id": "sess-x", "revised_claim": "Revised."}),
]


@pytest.mark.parametrize("path,body", _DEBATE_ROUTES, ids=[r[0] for r in _DEBATE_ROUTES])
def test_debate_routes_reject_missing_token(path, body):
    response = client.post(path, json=body)
    assert response.status_code == 401, f"{path} accepted an unauthenticated request"
    assert "Authentication required" in response.text


@pytest.mark.parametrize("path,body", _DEBATE_ROUTES, ids=[r[0] for r in _DEBATE_ROUTES])
def test_debate_routes_reject_forged_token(path, body):
    response = client.post(path, json=body, headers={"Authorization": "Bearer forged.signature"})
    assert response.status_code == 401, f"{path} accepted a forged token"


def test_debate_turn_rejects_missing_token():
    response = client.post("/api/debate/turn", json={"session_id": "s", "student_reply": "r"})
    assert response.status_code == 401


# --------------------------------------------------------------- ownership ----


def test_student_cannot_submit_as_another_student():
    """The core integrity finding: student A writing into student B's profile."""
    response = client.post("/api/debate/start", json=_start_body(_VICTIM), headers=_headers(_ATTACKER))
    assert response.status_code == 403
    assert "own student_id" in response.text


def test_student_cannot_reflect_as_another_student():
    """ĐỢT 15 #2: the request no longer names a student, so the attacker has to
    aim at the victim's SESSION -- and ownership is resolved from the session's
    own stored student_id, so the same 403 must come back."""
    from eduagent import interactive

    interactive.start_debate_session(
        "sess-victim",
        persona_id="skeptic",
        essay_text="Cats are great.",
        summary={"fallacies_draft": ["hasty generalization"]},
        student_id=_VICTIM,
        class_id="c1",
    )
    try:
        response = client.post(
            "/api/debate/reflect",
            json={"session_id": "sess-victim", "revised_claim": "Revised."},
            headers=_headers(_ATTACKER),
        )
        assert response.status_code == 403
    finally:
        interactive._sessions.pop("sess-victim", None)


def test_student_from_another_class_is_rejected():
    """Cross-tenant boundary -- the same rule ADR-013 set for teacher routes."""
    response = client.post("/api/debate/start", json=_start_body(_VICTIM), headers=_headers("c2_stu01"))
    assert response.status_code == 403
    assert "cannot access class" in response.text


def test_student_can_submit_as_themselves():
    fake = {"session_id": "s1", "turn": {}, "turn_number": 1}
    with patch("eduagent.server.start_debate", return_value=fake):
        response = client.post("/api/debate/start", json=_start_body(_VICTIM), headers=_headers(_VICTIM))
    assert response.status_code == 200


def test_same_class_teacher_may_drive_a_student_debate():
    """A teacher reproducing a student's debate is legitimate and already
    trusted with that class's data -- so this must NOT be a 403."""
    fake = {"session_id": "s1", "turn": {}, "turn_number": 1}
    with patch("eduagent.server.start_debate", return_value=fake):
        response = client.post(
            "/api/debate/start", json=_start_body(_VICTIM), headers=_headers("c1_teacher", role="teacher")
        )
    assert response.status_code == 200


def test_turn_ownership_resolved_from_the_session_not_the_request():
    """`/api/debate/turn` carries only a session_id, so a guessed session id
    must not let a different student advance someone else's debate."""
    session = {"student_id": _VICTIM, "class_id": "c1"}
    with patch("eduagent.server.get_debate_session", return_value=session):
        forbidden = client.post(
            "/api/debate/turn", json={"session_id": "sess-1", "student_reply": "r"}, headers=_headers(_ATTACKER)
        )
    assert forbidden.status_code == 403

    with patch("eduagent.server.get_debate_session", return_value=session), patch(
        "eduagent.server.submit_debate_turn", return_value={"turn": {}, "turn_number": 2, "completed": False}
    ):
        allowed = client.post(
            "/api/debate/turn", json={"session_id": "sess-1", "student_reply": "r"}, headers=_headers(_VICTIM)
        )
    assert allowed.status_code == 200


def test_unsplittable_student_id_is_rejected_with_400():
    """A bare id gives no class to scope against, so it must be refused rather
    than defaulted into some class."""
    response = client.post(
        "/api/debate/start",
        json={"essay_text": "x", "student_id": "nounderscore", "class_id": ""},
        headers=_headers(_VICTIM),
    )
    assert response.status_code == 400
    assert "Cannot determine class" in response.text


# -------------------------------------------------------------- rate limit ----


def test_token_bucket_allows_burst_then_refuses():
    limiter = TokenBucketLimiter(RateLimitPolicy(capacity=3, refill_per_second=1.0))
    for _ in range(3):
        limiter.check("ip-a", now=100.0)
    with pytest.raises(RateLimitExceeded):
        limiter.check("ip-a", now=100.0)


def test_token_bucket_refills_over_time():
    limiter = TokenBucketLimiter(RateLimitPolicy(capacity=2, refill_per_second=1.0))
    limiter.check("ip-a", now=0.0)
    limiter.check("ip-a", now=0.0)
    with pytest.raises(RateLimitExceeded):
        limiter.check("ip-a", now=0.0)
    limiter.check("ip-a", now=1.0)  # one token refilled


def test_token_bucket_reports_usable_retry_after():
    limiter = TokenBucketLimiter(RateLimitPolicy(capacity=1, refill_per_second=0.2))
    limiter.check("ip-a", now=0.0)
    with pytest.raises(RateLimitExceeded) as exc:
        limiter.check("ip-a", now=0.0)
    assert exc.value.retry_after_seconds == 5  # 1 token / 0.2 per second


def test_token_bucket_is_isolated_per_key():
    limiter = TokenBucketLimiter(RateLimitPolicy(capacity=1, refill_per_second=1.0))
    limiter.check("ip-a", now=0.0)
    limiter.check("ip-b", now=0.0)  # a different caller must be unaffected
    with pytest.raises(RateLimitExceeded):
        limiter.check("ip-a", now=0.0)


def test_rejected_caller_still_accrues_tokens_and_is_not_locked_out():
    """A limiter that stops refilling on rejection would permanently lock out
    anyone who ever hit the limit once."""
    limiter = TokenBucketLimiter(RateLimitPolicy(capacity=1, refill_per_second=1.0))
    limiter.check("ip-a", now=0.0)
    for t in (0.1, 0.2, 0.3):
        with pytest.raises(RateLimitExceeded):
            limiter.check("ip-a", now=t)
    limiter.check("ip-a", now=1.5)


def test_client_key_uses_the_last_forwarded_hop_not_the_client_supplied_one():
    """ĐỢT 17 #1 -- this test used to assert the opposite, and its docstring
    had the direction of X-Forwarded-For exactly backwards.

    Cloud Run APPENDS the real client address, so the header reads
    `<whatever the caller invented>, <real IP>`. Keying on the FIRST entry --
    which is what the code and this test both did -- let anyone mint a fresh
    bucket per request by varying a header. Verified against the live service:
    with the real bucket drained, 8/8 requests carrying random spoofed values
    were served, then the drained bucket returned 429 again the moment the
    spoof stopped. Only the last entry is vouched for by the infrastructure.
    """
    # The caller invented "1.2.3.4"; Cloud Run appended the real "10.0.0.1".
    assert client_key(x_forwarded_for="1.2.3.4, 10.0.0.1", peer_host="10.0.0.1") == "10.0.0.1"

    # Varying the forgeable part must NOT change the bucket.
    keys = {
        client_key(x_forwarded_for=f"172.16.0.{i}, 203.0.113.7", peer_host="10.0.0.1")
        for i in range(1, 20)
    }
    assert keys == {"203.0.113.7"}, f"spoofed hops leaked into the rate-limit key: {keys}"

    # Multiple forged hops are all still ignored.
    assert client_key(x_forwarded_for="1.1.1.1, 2.2.2.2, 3.3.3.3, 198.51.100.4", peer_host=None) == "198.51.100.4"

    # Trailing/edge whitespace and empty segments must not resurrect a forged hop.
    assert client_key(x_forwarded_for="1.2.3.4, 10.0.0.1, ", peer_host=None) == "10.0.0.1"

    assert client_key(x_forwarded_for=None, peer_host="10.0.0.1") == "10.0.0.1"
    assert client_key(x_forwarded_for="", peer_host=None) == "unknown"


def test_debate_endpoint_returns_429_with_retry_after_when_flooded():
    """End-to-end through the real route, which is what the STRIDE table's
    DoS row now actually refers to."""
    debate_limiter.reset()
    headers = _headers(_VICTIM)
    fake = {"session_id": "s1", "turn": {}, "turn_number": 1}
    statuses = []
    with patch("eduagent.server.start_debate", return_value=fake):
        for _ in range(15):  # DEBATE_POLICY.capacity is 10
            statuses.append(client.post("/api/debate/start", json=_start_body(_VICTIM), headers=headers).status_code)

    assert 429 in statuses, f"flood was never rate limited: {statuses}"
    assert statuses[0] == 200, "the very first legitimate request must not be limited"

    limited = client.post("/api/debate/start", json=_start_body(_VICTIM), headers=headers)
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) >= 1


def test_login_is_rate_limited_against_password_brute_force():
    from eduagent.rate_limit import login_limiter

    login_limiter.reset()
    statuses = [
        client.post("/api/auth/login", json={"role": "student", "user_id": "c1_stu01", "password": f"guess{i}"}).status_code
        for i in range(10)  # LOGIN_POLICY.capacity is 5
    ]
    assert 401 in statuses, "wrong passwords should still be rejected as 401"
    assert 429 in statuses, f"brute-force attempt was never rate limited: {statuses}"
