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
