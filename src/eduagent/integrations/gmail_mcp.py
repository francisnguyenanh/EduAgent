"""Gmail MCP integration -- compose-only by CODE DISCIPLINE, not OAuth scope.

ADR-001 (see TODO.md PHASE 0 / PROJECT_WIKI.md 9.1): real testing proved
`gmail.compose` does NOT block `messages.send()` at the credential layer --
Google's own docs describe the scope as including send. So the least-
privilege guarantee here is enforced by never calling `.send()` anywhere in
this module, full stop. tests/test_gmail_mcp_never_sends.py greps this file's
source for `.send(` and fails the build if it's ever added -- treat that
test as a hard gate, not a suggestion.

The real HITL gate is downstream of this module: the teacher opens the
draft in their own Gmail client and clicks Send themselves.
"""

from __future__ import annotations

import base64
import functools
import glob
from email.mime.text import MIMEText
from pathlib import Path

from eduagent.resilience import with_google_api_retry

COMPOSE_ONLY_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]

_SECRETS_DIR = Path(__file__).parent.parent.parent.parent / "secrets"
_TOKEN_PATH = _SECRETS_DIR / "gmail_compose_only_token.json"


def _find_client_secret() -> Path:
    matches = glob.glob(str(_SECRETS_DIR / "client_secret_*.json"))
    if not matches:
        raise FileNotFoundError(
            f"No client_secret_*.json found in {_SECRETS_DIR}. "
            "Download it from Cloud Console > Credentials > OAuth client ID (see TODO.md PHASE 0)."
        )
    return Path(matches[0])


@functools.lru_cache(maxsize=1)
def _credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if _TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), COMPOSE_ONLY_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(_find_client_secret()), COMPOSE_ONLY_SCOPES)
            creds = flow.run_local_server(port=0)
        _TOKEN_PATH.write_text(creds.to_json())

    return creds


@functools.lru_cache(maxsize=1)
def _service():
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=_credentials())


@with_google_api_retry
def create_digest_draft(*, to_address: str, subject: str, body_text: str) -> str:
    """Creates a Gmail draft. Returns the draft id. Never sends -- see module
    docstring; this function has no path to messages.send/drafts.send."""
    message = MIMEText(body_text)
    message["to"] = to_address
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    draft = _service().users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return draft["id"]
