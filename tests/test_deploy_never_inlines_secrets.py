"""ĐỢT 14 / ADR-020 -- hard gate: the deploy script must never pass a credential
to Cloud Run as a plain environment variable.

This is the same style of guard as tests/test_gmail_mcp_never_sends.py, and it
exists because the failure it prevents was real and was live: an earlier version
of scripts/deploy_to_cloud_run.py read the Gmail and Sheets OAuth tokens off disk
and passed them through `--env-vars-file`. Cloud Run keeps plain env vars in the
revision spec in cleartext, so `gcloud run services describe` printed both
refresh tokens in full to anyone with `run.services.get`.

The check is AST-based rather than a text grep, so the module's own explanatory
comments (which necessarily mention the env var names) cannot cause a false
positive -- the same reasoning as the gmail `.send()` gate.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_DEPLOY_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "deploy_to_cloud_run.py"

# Env vars whose values are credentials. Each must arrive via Secret Manager.
_CREDENTIAL_ENV_VARS = {
    "EDUAGENT_SESSION_SECRET",
    "GMAIL_COMPOSE_TOKEN_JSON",
    "SHEETS_TOKEN_JSON",
}


@pytest.fixture(scope="module")
def tree() -> ast.Module:
    return ast.parse(_DEPLOY_SCRIPT.read_text(encoding="utf-8"))


def _dict_string_keys(node: ast.Dict) -> list[str]:
    return [k.value for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]


def test_no_credential_is_declared_as_a_plain_env_var(tree):
    """Fails if any credential name appears as a key in a dict literal -- which is
    how the plaintext env-vars payload is built."""
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key in _dict_string_keys(node):
                if key in _CREDENTIAL_ENV_VARS:
                    # SECRET_ENV_VARS legitimately uses these names as keys, but
                    # maps them to secret NAMES, not to credential values. Tell
                    # the two apart by checking the mapped value is a bare string
                    # literal secret name, never a variable holding file content.
                    idx = _dict_string_keys(node).index(key)
                    value = node.values[[i for i, k in enumerate(node.keys)
                                         if isinstance(k, ast.Constant) and k.value == key][0]]
                    if not (isinstance(value, ast.Constant) and isinstance(value.value, str)
                            and value.value.startswith("eduagent-")):
                        offenders.append(key)
    assert not offenders, (
        f"deploy_to_cloud_run.py declares credential(s) {sorted(set(offenders))} as plain env var "
        "values. Cloud Run stores plain env vars in the revision spec in cleartext, so they would "
        "be readable via `gcloud run services describe`. Mount them via --update-secrets instead "
        "(see SECRET_ENV_VARS / ADR-020)."
    )


def test_secret_env_vars_covers_every_known_credential(tree):
    """Every credential must be in the Secret Manager mapping -- otherwise it is
    simply absent from the deployed service and the feature silently breaks."""
    mapping_keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "SECRET_ENV_VARS" in targets and isinstance(node.value, ast.Dict):
                mapping_keys = set(_dict_string_keys(node.value))

    assert mapping_keys, "SECRET_ENV_VARS dict literal not found in deploy_to_cloud_run.py"
    missing = _CREDENTIAL_ENV_VARS - mapping_keys
    assert not missing, f"credential(s) {sorted(missing)} are not mounted from Secret Manager"


def test_deploy_command_passes_update_secrets(tree):
    """The mapping is inert unless the gcloud invocation actually uses it."""
    source = _DEPLOY_SCRIPT.read_text(encoding="utf-8")
    assert "--update-secrets" in source, "deploy command does not pass --update-secrets"
    # And it must be built from the mapping, not hand-written for one secret only
    # (the bug shape this replaced: session secret mounted, tokens still inline).
    assert "SECRET_ENV_VARS.items()" in source, (
        "--update-secrets should be built from SECRET_ENV_VARS so adding a credential "
        "to the mapping is sufficient to mount it"
    )


def test_script_does_not_read_token_files_into_memory(tree):
    """Reading the token files at deploy time was the mechanism of the exposure;
    with Secret Manager the script has no reason to open them at all."""
    source = _DEPLOY_SCRIPT.read_text(encoding="utf-8")
    for filename in ("gmail_compose_only_token.json", "sheets_token.json"):
        # The names may appear inside the remediation instructions printed on a
        # missing secret, but must not appear in an open() call.
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
                call_src = ast.unparse(node)
                assert filename not in call_src, (
                    f"deploy script opens {filename} -- token contents should never be read "
                    "into the deploy payload (ADR-020)"
                )
    assert source  # keeps the file-read explicit for readers
