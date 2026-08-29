"""The preflight scripts must not die on a Windows machine.

`scripts/doctor.py` and `scripts/deploy_to_cloud_run.py` invoked the gcloud CLI
as the bare string "gcloud". On Windows the SDK installs `gcloud.cmd` and there
is no extension-less binary, so CreateProcess raised FileNotFoundError and
`python scripts/doctor.py` ended in a traceback instead of a report -- on the
exact machine it is most likely to be run from.

Two guards, because the fix has two halves:
  1. neither script may pass a bare "gcloud" to subprocess (AST-level, so the
     comments that necessarily mention the name cannot cause a false positive);
  2. the doctor check degrades to WARN when gcloud is genuinely absent, rather
     than raising.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _subprocess_run_arg_lists(path: Path) -> list[ast.AST]:
    """Every list literal handed to subprocess.run(...) as its first argument."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "run" and node.args:
            found.append(node.args[0])
    return found


@pytest.mark.parametrize("script", ["doctor.py", "deploy_to_cloud_run.py"])
def test_no_script_invokes_a_bare_gcloud(script):
    for arg in _subprocess_run_arg_lists(_SCRIPTS / script):
        if not isinstance(arg, ast.List) or not arg.elts:
            continue
        first = arg.elts[0]
        if isinstance(first, ast.Constant):
            assert first.value != "gcloud", (
                f"{script} passes a bare 'gcloud' to subprocess.run -- FileNotFoundError on Windows, "
                "where the launcher is gcloud.cmd. Resolve it with shutil.which() instead."
            )


def _load_doctor():
    spec = importlib.util.spec_from_file_location("_doctor_under_test", _SCRIPTS / "doctor.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_cloud_run_credential_check_warns_when_gcloud_is_absent():
    doctor = _load_doctor()
    with patch.object(doctor, "_gcloud_executable", return_value=None):
        status, message = doctor.check_no_plaintext_credentials_on_cloud_run()
    assert status == doctor.WARN
    assert "gcloud" in message


def test_cloud_run_credential_check_warns_instead_of_raising_on_oserror():
    """Belt and braces: even if which() finds something unexecutable, the doctor
    reports a skipped check rather than aborting the whole run."""
    doctor = _load_doctor()
    with (
        patch.object(doctor, "_gcloud_executable", return_value="/nonexistent/gcloud"),
        patch("subprocess.run", side_effect=OSError("not executable")),
    ):
        status, message = doctor.check_no_plaintext_credentials_on_cloud_run()
    assert status == doctor.WARN
    assert "skipped" in message.lower()
