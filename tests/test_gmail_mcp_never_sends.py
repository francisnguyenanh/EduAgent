"""HARD GATE, not a suggestion: gmail_mcp.py must never call .send().

ADR-001 established that gmail.compose does NOT block send() at the OAuth
layer -- the only real least-privilege guarantee left is that our own code
never exercises that capability. This test greps the module SOURCE (not just
runtime behavior) so a send() call added anywhere in the file -- even in a
branch never hit by other tests -- fails the build immediately.
"""

from __future__ import annotations

import ast
import inspect

from eduagent.integrations import gmail_mcp


def test_gmail_mcp_source_has_no_send_call():
    """Parses the AST rather than grepping raw text, so this can't be
    fooled by a docstring mentioning '.send()' as prose (as this module's
    own module docstring does) -- it only fails on an actual method call
    named `send` anywhere in the code."""
    source = inspect.getsource(gmail_mcp)
    tree = ast.parse(source)
    send_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "send"
    ]
    assert not send_calls, (
        "gmail_mcp.py must never call .send() -- ADR-001: least-privilege here "
        "is enforced by code discipline, not OAuth scope. If you're adding a "
        "legitimate send path, it does not belong in this module."
    )


def test_gmail_mcp_only_exports_draft_creation():
    """Restricts to names actually DEFINED in this module (not imported
    symbols like MIMEText/Path, which dir() also picks up)."""
    public_functions = [
        name
        for name in dir(gmail_mcp)
        if not name.startswith("_")
        and callable(getattr(gmail_mcp, name))
        and getattr(getattr(gmail_mcp, name), "__module__", None) == gmail_mcp.__name__
    ]
    assert public_functions == ["create_digest_draft"], (
        f"gmail_mcp.py exports unexpected public functions: {public_functions}. "
        "Only draft creation should be exposed from this module."
    )


def test_gmail_mcp_credentials_from_env(monkeypatch):
    import json
    from datetime import datetime, timezone, timedelta
    sample_token = {
        "token": "fake-token",
        "refresh_token": "fake-refresh-token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "fake-client-id",
        "client_secret": "fake-client-secret",
        "scopes": ["https://www.googleapis.com/auth/gmail.compose"],
        "expiry": (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    monkeypatch.setenv("GMAIL_COMPOSE_TOKEN_JSON", json.dumps(sample_token))
    gmail_mcp._credentials.cache_clear()
    creds = gmail_mcp._credentials()
    assert creds is not None
    assert creds.token == "fake-token"
    gmail_mcp._credentials.cache_clear()


def test_create_digest_draft_returns_both_ids(monkeypatch):
    """ADR-030: `drafts.create()` returns an API draft id
    ("r328879860172231529") AND a hex message id ("1a04055b6640d946"). Gmail's
    web UI addresses a draft by the SECOND one, so the dashboard's
    "open the draft" link needs it. Verified against the live mailbox --
    building the URL from the draft id opens an empty compose window.

    Sabotage check: return only `draft["id"]` and this goes red."""
    captured = {}

    class _Drafts:
        def create(self, *, userId, body):
            captured["userId"] = userId

            class _Exec:
                def execute(inner_self):
                    return {"id": "r328879860172231529", "message": {"id": "1a04055b6640d946"}}

            return _Exec()

    class _Users:
        def drafts(self):
            return _Drafts()

    class _Service:
        def users(self):
            return _Users()

    monkeypatch.setattr(gmail_mcp, "_service", lambda: _Service())
    result = gmail_mcp.create_digest_draft(
        to_address="teacher@example.com", subject="s", body_text="t", body_html="<p>t</p>"
    )

    assert result == {"draft_id": "r328879860172231529", "message_id": "1a04055b6640d946"}
    assert captured["userId"] == "me"
