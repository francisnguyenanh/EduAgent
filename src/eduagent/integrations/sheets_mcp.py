"""Sheets MCP integration -- append-only audit log for teacher digests.

Uses the SAME OAuth client as gmail_mcp.py (Phase 0's eduagent-gmail-mcp
Desktop app) but a separate token/scope, so the spreadsheet lives in the
teacher's own Google account (easy to show live in the demo video) rather
than a service-account-owned Drive space nobody can easily open.

append-only by convention: this module only exposes append_audit_row(), no
update/delete -- an audit trail you can edit isn't an audit trail.
"""

from __future__ import annotations

import functools
import glob
from pathlib import Path

SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_SECRETS_DIR = Path(__file__).parent.parent.parent.parent / "secrets"
_TOKEN_PATH = _SECRETS_DIR / "sheets_token.json"

_HEADER_ROW = ["timestamp", "class_id", "event", "headline", "priority_students", "digest_draft_id"]


def _find_client_secret() -> Path:
    matches = glob.glob(str(_SECRETS_DIR / "client_secret_*.json"))
    if not matches:
        raise FileNotFoundError(f"No client_secret_*.json found in {_SECRETS_DIR}.")
    return Path(matches[0])


@functools.lru_cache(maxsize=1)
def _credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if _TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), SHEETS_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(_find_client_secret()), SHEETS_SCOPES)
            creds = flow.run_local_server(port=0)
        _TOKEN_PATH.write_text(creds.to_json())

    return creds


@functools.lru_cache(maxsize=1)
def _service():
    from googleapiclient.discovery import build

    return build("sheets", "v4", credentials=_credentials())


def create_audit_spreadsheet(*, title: str = "eduagent Audit Log") -> str:
    """Creates a new spreadsheet with the header row, returns its spreadsheet_id.
    Call once; reuse the returned id via EDUAGENT_AUDIT_SPREADSHEET_ID."""
    spreadsheet = (
        _service()
        .spreadsheets()
        .create(body={"properties": {"title": title}, "sheets": [{"properties": {"title": "audit_log"}}]})
        .execute()
    )
    spreadsheet_id = spreadsheet["spreadsheetId"]
    append_audit_row(spreadsheet_id=spreadsheet_id, row=_HEADER_ROW)
    return spreadsheet_id


def append_audit_row(*, spreadsheet_id: str, row: list) -> None:
    """Append-only: adds one row to the end of the sheet. No update/delete
    exposed from this module -- keep the audit trail immutable."""
    _service().spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="audit_log!A:F",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()
