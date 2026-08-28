"""Audit Wave 27 hard gate: no script may pass the bare string "gcloud" as argv[0].

WHY THIS TEST EXISTS
--------------------
On Windows the Cloud SDK ships `gcloud.CMD`, and `CreateProcess` does not apply
PATHEXT to argv[0]. So `subprocess.run(["gcloud", ...])` raises
`FileNotFoundError: [WinError 2]` -- the launcher is on PATH, but not under the
name given. The fix (resolve with `shutil.which` first) was applied to
`doctor.py` and `deploy_to_cloud_run.py` in Wave 15, and **missed
`rotate_oauth_tokens.py`**, where it stayed hidden for twelve waves because
nobody had rotated a token from Windows.

When it finally fired it did so at the worst possible moment: *after* the
browser consent had already minted a fresh token. The token existed on disk but
never reached Secret Manager, leaving the rotation half-applied -- and a naive
re-run would have revoked the good token and demanded consent again.

A partially-applied fix is the failure mode here, not the original bug, so the
guard is written against every script at once rather than against the one that
was broken. Same shape as `test_gmail_mcp_never_sends.py`: read the source, not
the behaviour, because the behaviour only shows up on one OS.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
_SUBPROCESS_CALLS = {"run", "call", "check_call", "check_output", "Popen"}


def _script_paths() -> list[Path]:
    return sorted(p for p in _SCRIPTS_DIR.glob("*.py") if p.name != "__init__.py")


def _bare_gcloud_invocations(source: str) -> list[int]:
    """Line numbers where a subprocess call's argv[0] is the literal 'gcloud'."""
    offenders: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name not in _SUBPROCESS_CALLS or not node.args:
            continue
        argv = node.args[0]
        if not isinstance(argv, (ast.List, ast.Tuple)) or not argv.elts:
            continue
        first = argv.elts[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            # Only the bare name is a bug. An absolute path, or the result of a
            # resolver call like _gcloud(), is exactly the fix we want.
            if first.value in ("gcloud", "gcloud.cmd", "gcloud.CMD"):
                offenders.append(node.lineno)
    return offenders


@pytest.mark.parametrize("script", _script_paths(), ids=lambda p: p.name)
def test_script_does_not_invoke_gcloud_by_bare_name(script: Path) -> None:
    offenders = _bare_gcloud_invocations(script.read_text(encoding="utf-8"))
    assert not offenders, (
        f"{script.name} passes the bare string 'gcloud' as argv[0] at line(s) {offenders}. "
        "On Windows that raises FileNotFoundError [WinError 2] because the launcher is "
        "gcloud.CMD and PATHEXT is not applied to argv[0]. Resolve it first with "
        "shutil.which('gcloud') -- see rotate_oauth_tokens.py::_gcloud()."
    )


def test_the_detector_actually_detects() -> None:
    """Guards the guard (ADR-019). A source-scanning test that cannot fire is
    worse than no test, so prove the detector sees the pattern it exists for,
    and does not fire on the fixed form."""
    broken = 'import subprocess\nsubprocess.run(["gcloud", "secrets", "list"])\n'
    assert _bare_gcloud_invocations(broken) == [2]

    fixed = 'import subprocess\nsubprocess.run([_gcloud(), "secrets", "list"])\n'
    assert _bare_gcloud_invocations(fixed) == []

    absolute = 'import subprocess\nsubprocess.run(["C:/sdk/bin/gcloud.CMD", "secrets", "list"])\n'
    assert _bare_gcloud_invocations(absolute) == []


def test_every_script_that_shells_out_to_gcloud_resolves_it() -> None:
    """The parametrized test above passes trivially for a script that never
    mentions gcloud. This asserts the three scripts that really do shell out to
    it each carry a resolver, so the guard is anchored to real call sites."""
    expected = {"doctor.py", "deploy_to_cloud_run.py", "rotate_oauth_tokens.py"}
    found = {
        p.name
        for p in _script_paths()
        if "shutil.which(\"gcloud\")" in p.read_text(encoding="utf-8")
    }
    missing = expected - found
    assert not missing, f"these scripts shell out to gcloud but no longer resolve it: {sorted(missing)}"
