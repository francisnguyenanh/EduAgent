"""Tier-A coverage: the ADR-014 push-endpoint OIDC gate.

`POST /` is the Pub/Sub push entrypoint on a service deployed
--allow-unauthenticated, so Cloud Run IAM does NOT protect it. This function
is the only thing standing between the open internet and LLM-costed digest
generation. `smoke_live.py` proves the no-token case returns 401 against the
live service; these cover the branches a live smoke test cannot reach --
a Google-signed token that is real but issued to the WRONG service account,
and a token that fails verification outright.
"""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from eduagent import server


def _call(auth):
    return server._verify_pubsub_push_auth(auth)


@pytest.mark.parametrize("header", [None, "", "token-without-bearer-prefix", "Basic abc"])
def test_missing_or_malformed_authorization_is_rejected(header):
    with pytest.raises(HTTPException) as exc:
        _call(header)
    assert exc.value.status_code == 401
    assert "Missing" in exc.value.detail


def test_token_failing_google_verification_is_rejected():
    """Anything Google's public keys do not validate -- forged, expired,
    wrong signature -- is refused regardless of configuration."""
    with patch.object(server.google_id_token, "verify_oauth2_token", side_effect=ValueError("bad signature")):
        with pytest.raises(HTTPException) as exc:
            _call("Bearer forged.token.here")
    assert exc.value.status_code == 401
    assert "Invalid" in exc.value.detail


def test_valid_google_token_from_the_wrong_service_account_is_rejected():
    """The gap this closes: a token can be genuinely Google-signed and still
    belong to *anyone with a Google account*. Verification alone is not
    authorisation -- the same distinction ADR-013 made for teacher tokens."""
    with (
        patch.object(server.google_id_token, "verify_oauth2_token", return_value={"email": "attacker@example.com"}),
        patch.object(server, "PUBSUB", replace(server.PUBSUB, push_service_account="eduagent-sa@project.iam.gserviceaccount.com")),
    ):
        with pytest.raises(HTTPException) as exc:
            _call("Bearer valid.but.wrong.identity")
    assert exc.value.status_code == 401
    assert "expected push service account" in exc.value.detail


def test_valid_google_token_from_the_expected_service_account_is_accepted():
    with (
        patch.object(server.google_id_token, "verify_oauth2_token", return_value={"email": "eduagent-sa@project.iam.gserviceaccount.com"}),
        patch.object(server, "PUBSUB", replace(server.PUBSUB, push_service_account="eduagent-sa@project.iam.gserviceaccount.com")),
    ):
        assert _call("Bearer valid.and.expected") is None


def test_signature_is_still_verified_when_no_service_account_is_pinned():
    """Local/unpinned config must not degrade into 'accept anything' -- the
    cryptographic check is mandatory, the identity pin is the extra layer."""
    with (
        patch.object(server, "PUBSUB", replace(server.PUBSUB, push_service_account="")),
        patch.object(server.google_id_token, "verify_oauth2_token", side_effect=ValueError("bad signature")) as verify,
    ):
        with pytest.raises(HTTPException):
            _call("Bearer forged")
    verify.assert_called_once()
