"""One-off cleanup: delete leftover Phase 0 verification drafts/messages
created while probing whether gmail.compose blocks send() (it doesn't)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

SECRETS_DIR = Path(__file__).parent.parent / "secrets"
TOKEN_PATH = SECRETS_DIR / "gmail_compose_only_token.json"


def main() -> None:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(
        str(TOKEN_PATH), ["https://www.googleapis.com/auth/gmail.compose"]
    )
    service = build("gmail", "v1", credentials=creds)

    drafts = service.users().drafts().list(userId="me", q="subject:Phase 0 Gmail compose-only verification").execute()
    for d in drafts.get("drafts", []):
        service.users().drafts().delete(userId="me", id=d["id"]).execute()
        print(f"[OK] deleted leftover draft {d['id']}")

    if not drafts.get("drafts"):
        print("No leftover drafts found (already cleaned or auto-consumed by send()).")


if __name__ == "__main__":
    main()
