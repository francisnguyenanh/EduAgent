"""Verification: what gmail.compose actually enforces, and what it
doesn't (real finding, tested 2026-08-24 against the live Gmail API).

CORRECTED UNDERSTANDING (see ADR-001 in README.md for the
original, WRONG assumption):
  Google's gmail.compose scope is documented as "create, read, update, and
  delete drafts; send messages and drafts" — it is NOT a send-blocking scope.
  A live test on 2026-08-24 confirmed `messages.send()` succeeds with a
  compose-only token (two real emails were sent to the developer's own inbox
  during that test, then cleaned up). There is no narrower Gmail API scope
  that permits draft creation but rejects send() at the credential layer.

CONSEQUENCE FOR THE HITL GATE (wiki 9.1 principle #5 needs revising):
  Least-privilege for the Teacher Digest Mailer must be enforced at the
  APPLICATION CODE layer, not the OAuth scope layer:
    - Our codebase must never contain a call to `messages.send` / `drafts.send`
      for the digest flow. This script and unit tests should assert that.
    - The actual "gate" is that the teacher opens their own Gmail client and
      clicks Send on the draft themselves — a real human action outside any
      code path we control — not a scope-enforced technical impossibility.
  This is a legitimate least-privilege design (the agent's OWN code path has
  no send capability), it's just enforced by code discipline + review, not by
  a Google-side technical wall. State this honestly in the README/ADR and in
  the demo video — do not claim "OAuth technically prevents it".

This script now ONLY verifies draft creation/deletion (safe, no side effects
on a real inbox). It does not test send() again — that finding is settled.
"""

from __future__ import annotations

import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

SECRETS_DIR = Path(__file__).parent.parent / "secrets"
TOKEN_PATH = SECRETS_DIR / "gmail_compose_only_token.json"

COMPOSE_ONLY_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


def _find_client_secret() -> Path:
    matches = glob.glob(str(SECRETS_DIR / "client_secret_*.json"))
    if not matches:
        raise FileNotFoundError(
            f"No client_secret_*.json found in {SECRETS_DIR}. "
            "Download it from Cloud Console > Credentials > OAuth client ID."
        )
    return Path(matches[0])


def _get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), COMPOSE_ONLY_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secret = _find_client_secret()
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), COMPOSE_ONLY_SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())

    return creds


def main() -> None:
    import base64
    from email.mime.text import MIMEText

    from googleapiclient.discovery import build

    to_address = sys.argv[1] if len(sys.argv) > 1 else None
    if not to_address:
        print("Usage: python verify_gmail_compose_only.py <your-gmail-address>")
        sys.exit(2)

    creds = _get_credentials()
    service = build("gmail", "v1", credentials=creds)

    message = MIMEText("This is a Phase 0 verification draft from eduagent. Safe to delete.")
    message["to"] = to_address
    message["subject"] = "[eduagent] Phase 0 Gmail draft verification (not sent)"
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    draft_id = draft["id"]
    print(f"[OK] Draft created with gmail.compose token: draft_id={draft_id}")

    service.users().drafts().delete(userId="me", id=draft_id).execute()
    print(f"[OK] Draft {draft_id} deleted. No send() attempted (see module docstring).")
    print("\ngmail.compose draft create/delete verification PASSED.")
    print("Reminder: send() capability is NOT blocked by this scope -- enforce")
    print("least-privilege at the application code layer, not OAuth alone.")


if __name__ == "__main__":
    main()
