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

from eduagent.resilience import with_google_api_retry

SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_SECRETS_DIR = Path(__file__).parent.parent.parent.parent / "secrets"
_TOKEN_PATH = _SECRETS_DIR / "sheets_token.json"

_HEADER_ROW = ["timestamp", "class_id", "event", "headline", "priority_students", "digest_draft_id"]


def extract_spreadsheet_id(url_or_id: str) -> str:
    """Extracts a Google Spreadsheet ID from either a raw ID or a full Google Sheet URL."""
    if not url_or_id:
        return ""
    cleaned = url_or_id.strip()
    if "/d/" in cleaned:
        try:
            return cleaned.split("/d/")[1].split("/")[0].split("?")[0].split("#")[0]
        except Exception:
            return cleaned
    return cleaned


def _find_client_secret() -> Path | None:
    matches = glob.glob(str(_SECRETS_DIR / "client_secret_*.json"))
    return Path(matches[0]) if matches else None


@functools.lru_cache(maxsize=1)
def _credentials():
    import json
    import os
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    import google.auth

    creds = None
    token_json_env = os.getenv("SHEETS_TOKEN_JSON")
    if token_json_env:
        try:
            creds_data = json.loads(token_json_env)
            creds = Credentials.from_authorized_user_info(creds_data, SHEETS_SCOPES)
        except Exception:
            pass

    if not creds and _TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), SHEETS_SCOPES)
        except Exception:
            pass

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secret = _find_client_secret()
            if client_secret is not None:
                flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SHEETS_SCOPES)
                creds = flow.run_local_server(port=0)
                try:
                    _TOKEN_PATH.write_text(creds.to_json())
                except Exception:
                    pass
            else:
                creds, _ = google.auth.default(scopes=SHEETS_SCOPES)

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


@with_google_api_retry
def append_audit_row(*, spreadsheet_id: str, row: list) -> None:
    """Append-only: adds one row to the end of the sheet. Tries 'audit_log!A:F'
    first, and if that tab doesn't exist, appends to the first/active sheet 'A:F'."""
    srv = _service()
    try:
        srv.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="audit_log!A:F",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()
    except Exception as exc:
        # If audit_log tab doesn't exist, append to whatever tab exists in the user's sheet
        if "Unable to parse range" in str(exc) or "audit_log" in str(exc):
            srv.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range="A:F",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]},
            ).execute()
        else:
            raise

