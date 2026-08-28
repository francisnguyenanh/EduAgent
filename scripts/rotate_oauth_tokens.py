"""Wave 16 -- rotates the Gmail and Sheets OAuth refresh tokens end to end.

WHY: both refresh tokens were exposed in cleartext on the live Cloud Run
revision spec before ADR-020 (readable by anyone with `run.services.get`).
Moving them into Secret Manager stops FUTURE reads; it does not invalidate a
value that already leaked. The only real fix for an exposed credential is to
make the old value stop working -- i.e. rotate it, not just relocate it.

This script does everything that does NOT require a browser:
  1. Revokes the OLD refresh token at Google's revoke endpoint (best-effort --
     if it's already invalid/expired, that's a no-op, not a failure).
  2. Deletes the local token file so the next step cannot silently reuse
     (refresh()) the old refresh_token -- it forces a brand-new consent grant.
  3. After step 4 (see below) produces a new local token, uploads it as a new
     Secret Manager version.

Step 4 -- getting the NEW token -- needs a human: `flow.run_local_server()`
opens a real browser window and needs YOUR Google login + consent click. No
agent can complete that on your behalf. Run this script yourself, in a real
terminal on your own machine, and complete the two browser prompts (Gmail
scope, then Sheets scope) when they appear.

Usage:
    .venv/bin/python scripts/rotate_oauth_tokens.py            # both
    .venv/bin/python scripts/rotate_oauth_tokens.py --gmail-only
    .venv/bin/python scripts/rotate_oauth_tokens.py --sheets-only
    .venv/bin/python scripts/rotate_oauth_tokens.py --skip-redeploy
    .venv/bin/python scripts/rotate_oauth_tokens.py --gmail-only --upload-only   # recovery
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

_SECRETS_DIR = _ROOT / "secrets"

_TARGETS = {
    "gmail": {
        "token_path": _SECRETS_DIR / "gmail_compose_only_token.json",
        "scopes": ["https://www.googleapis.com/auth/gmail.compose"],
        "secret_name": "eduagent-gmail-token",
        "env_var": "GMAIL_COMPOSE_TOKEN_JSON",
    },
    "sheets": {
        "token_path": _SECRETS_DIR / "sheets_token.json",
        "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
        "secret_name": "eduagent-sheets-token",
        "env_var": "SHEETS_TOKEN_JSON",
    },
}


def _find_client_secret() -> Path:
    matches = sorted(_SECRETS_DIR.glob("client_secret_*.json"))
    if not matches:
        raise FileNotFoundError(
            f"No client_secret_*.json in {_SECRETS_DIR}. Download it from "
            "Cloud Console > APIs & Services > Credentials > OAuth client ID."
        )
    return matches[0]


def _revoke_old_token(token_path: Path, label: str) -> None:
    """Best-effort revoke at Google's endpoint. Not fatal if it fails -- an
    already-expired or already-revoked token, or a network hiccup, must not
    block getting the new one."""
    if not token_path.exists():
        print(f"  [skip] no existing {label} token file to revoke.")
        return
    try:
        data = json.loads(token_path.read_text())
        refresh_token = data.get("refresh_token")
        if not refresh_token:
            print(f"  [skip] {label} token file has no refresh_token field.")
            return
        import requests

        resp = requests.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": refresh_token},
            headers={"content-type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        if resp.status_code == 200:
            print(f"  [ok] old {label} refresh_token revoked at Google -- it no longer works, exposed or not.")
        else:
            print(f"  [warn] revoke endpoint returned {resp.status_code} for {label} -- continuing anyway.")
    except Exception as exc:
        print(f"  [warn] could not revoke old {label} token ({exc}) -- continuing anyway.")


def _mint_new_token(scopes: list[str], token_path: Path, label: str):
    """The one step that needs YOU: opens a browser for Google consent."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    print(f"\n>>> A browser window is about to open for the {label.upper()} scope.")
    print(f">>> Sign in and click Allow for: {scopes[0]}")
    flow = InstalledAppFlow.from_client_secrets_file(str(_find_client_secret()), scopes)
    creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json())
    print(f"  [ok] new {label} token written to {token_path}")
    return creds


def _gcloud() -> str:
    """Absolute path to the gcloud launcher.

    Wave 27: this script was the one place the Wave 15 #5 Windows fix never
    reached. `doctor.py::_gcloud_executable()` and
    `deploy_to_cloud_run.py::_gcloud()` both resolve the launcher first,
    because on Windows gcloud ships as `gcloud.CMD` and CreateProcess does not
    apply PATHEXT to an argv[0] of "gcloud" -- so the bare string raised
    `FileNotFoundError: [WinError 2]`. It surfaced at the worst moment: after
    the browser consent had already minted a new token, so the token existed
    locally but never reached Secret Manager, leaving the rotation half done.
    """
    import shutil

    resolved = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not resolved:
        sys.exit("[FAIL] gcloud CLI not found on PATH. Install the Google Cloud SDK, then re-run this script.")
    return resolved


def _upload_secret_version(secret_name: str, token_path: Path) -> None:
    result = subprocess.run(
        [_gcloud(), "secrets", "versions", "add", secret_name, f"--data-file={token_path}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  [FAIL] could not upload new version of {secret_name}:\n{result.stderr}")
        sys.exit(1)
    print(f"  [ok] new version of secret '{secret_name}' uploaded.")


def rotate(which: str, *, upload_only: bool = False) -> None:
    cfg = _TARGETS[which]
    if upload_only:
        # Wave 27 recovery path. Rotation is revoke -> mint -> upload, and the
        # upload used to be able to fail on Windows *after* the browser consent
        # had already produced a valid token. Re-running the whole thing would
        # then revoke that good token and demand consent a second time --
        # punishing the user for the script's own bug. This uploads the token
        # already on disk instead. Refuses to guess: if there is no local token,
        # say so rather than uploading nothing.
        print(f"\n=== Uploading EXISTING local {which} token (no revoke, no consent) ===")
        if not cfg["token_path"].exists():
            sys.exit(f"[FAIL] no local token at {cfg['token_path']} -- nothing to upload. Run without --upload-only.")
        _upload_secret_version(cfg["secret_name"], cfg["token_path"])
        return
    print(f"\n=== Rotating {which} OAuth token ===")
    _revoke_old_token(cfg["token_path"], which)
    cfg["token_path"].unlink(missing_ok=True)  # force a fresh grant, not a refresh() of the old one
    _mint_new_token(cfg["scopes"], cfg["token_path"], which)
    _upload_secret_version(cfg["secret_name"], cfg["token_path"])


def main() -> None:
    # ASCII only. argparse prints this to a console that may be cp932; a
    # non-ASCII character here raises UnicodeEncodeError and kills --help,
    # which is exactly what someone runs when the script has confused them.
    parser = argparse.ArgumentParser(description="Rotate the Gmail/Sheets OAuth refresh tokens (Audit Wave 16).")
    parser.add_argument("--gmail-only", action="store_true")
    parser.add_argument("--sheets-only", action="store_true")
    parser.add_argument("--skip-redeploy", action="store_true", help="Don't run deploy_to_cloud_run.py at the end.")
    parser.add_argument("--upload-only", action="store_true", help="Upload the token already on disk to Secret Manager; skip revoke and browser consent. Recovery path when the upload failed after consent succeeded.")
    args = parser.parse_args()

    targets = ["gmail", "sheets"]
    if args.gmail_only:
        targets = ["gmail"]
    elif args.sheets_only:
        targets = ["sheets"]

    for which in targets:
        rotate(which, upload_only=args.upload_only)

    print("\n=== Done rotating token(s). New Secret Manager versions are live. ===")
    if args.skip_redeploy:
        print("--skip-redeploy set -- remember Cloud Run still needs a redeploy to pick up ':latest'.")
        return

    print("\nRedeploying Cloud Run so the running revision picks up the new secret version...")
    subprocess.run([sys.executable, str(_ROOT / "scripts" / "deploy_to_cloud_run.py")], check=True)
    print("\nVerify: .venv/bin/python scripts/doctor.py  (Gmail/Sheets checks should still PASS with the new tokens)")


if __name__ == "__main__":
    main()
