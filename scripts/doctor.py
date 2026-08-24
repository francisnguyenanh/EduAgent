"""System Doctor -- pre-demo readiness check.

Runs every external dependency this project touches (GCP credentials,
Firestore, Pub/Sub topic/DLQ/subscription, Gmail OAuth token, Sheets audit
spreadsheet, Vertex AI/Gemini reachability) and prints a single PASS/FAIL/WARN
report, so a broken credential or an expired OAuth token surfaces BEFORE a
live, unedited demo recording -- not mid-take.

Each check is independent and non-fatal to the others (one broken dependency
must not hide whether the rest are healthy, same principle as PHASE 4's
graceful degradation). Exit code is 0 only if every check that matters for a
live demo passed; a WARN (e.g. Sheets not configured, since it's optional)
does not fail the overall run.

Usage: python scripts/doctor.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env")

from eduagent.config import CLOUD_RUN, FIRESTORE, GEMINI, PUBSUB, SHEETS, TEACHER  # noqa: E402

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


def _check(name: str, fn) -> CheckResult:
    try:
        status, detail = fn()
        return CheckResult(name, status, detail)
    except Exception as exc:  # noqa: BLE001 -- doctor must never crash on one bad check
        return CheckResult(name, FAIL, f"{type(exc).__name__}: {exc}")


def check_gcp_credentials() -> tuple[str, str]:
    import google.auth

    credentials, project_id = google.auth.default()
    if not project_id:
        return WARN, "Application Default Credentials loaded but no project_id resolved -- set GCP_PROJECT_ID."
    return PASS, f"ADC loaded OK, project={project_id}, service_account={getattr(credentials, 'service_account_email', 'n/a')}"


def check_firestore_connectivity() -> tuple[str, str]:
    from google.cloud import firestore

    db = firestore.Client()
    doc_ref = db.collection(FIRESTORE.processed_events_collection).document("_doctor_check")
    doc_ref.set({"doctor_check": True})
    ok = doc_ref.get().exists
    doc_ref.delete()
    if not ok:
        return FAIL, "Write succeeded but read-back failed."
    return PASS, f"Write/read/delete OK against collection '{FIRESTORE.processed_events_collection}'."


def check_pubsub_topology() -> tuple[str, str]:
    from google.cloud import pubsub_v1

    import google.auth

    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()
    _, project_id = google.auth.default()
    if not project_id:
        return WARN, "No project_id resolved -- cannot check Pub/Sub topology."

    topic_path = publisher.topic_path(project_id, PUBSUB.essay_evaluated_topic)
    dlq_path = publisher.topic_path(project_id, PUBSUB.dead_letter_topic)
    sub_path = subscriber.subscription_path(project_id, PUBSUB.class_aggregator_subscription)

    publisher.get_topic(request={"topic": topic_path})
    publisher.get_topic(request={"topic": dlq_path})
    subscription = subscriber.get_subscription(request={"subscription": sub_path})

    dead_letter = subscription.dead_letter_policy
    if not dead_letter or not dead_letter.dead_letter_topic:
        return WARN, f"Topic/DLQ/subscription exist, but subscription '{PUBSUB.class_aggregator_subscription}' has no dead-letter-policy attached."
    if subscription.dead_letter_policy.max_delivery_attempts != PUBSUB.max_delivery_attempts:
        return WARN, (
            f"Dead-letter max_delivery_attempts={subscription.dead_letter_policy.max_delivery_attempts}, "
            f"expected {PUBSUB.max_delivery_attempts} (config.py PUBSUB.max_delivery_attempts)."
        )
    return PASS, (
        f"Topic '{PUBSUB.essay_evaluated_topic}', DLQ '{PUBSUB.dead_letter_topic}', "
        f"subscription '{PUBSUB.class_aggregator_subscription}' all exist with dead-letter-policy wired correctly."
    )


def check_gmail_oauth_token() -> tuple[str, str]:
    secrets_dir = Path(__file__).parent.parent / "secrets"
    token_path = secrets_dir / "gmail_compose_only_token.json"
    if not TEACHER.email:
        return WARN, "EDUAGENT_TEACHER_EMAIL not set -- Gmail digest delivery is disabled by config, not tested."
    if not token_path.exists():
        return FAIL, f"No token at {token_path} -- run scripts/verify_gmail_compose_only.py once to authorize."

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials.from_authorized_user_file(str(token_path), ["https://www.googleapis.com/auth/gmail.compose"])
    if creds.valid:
        return PASS, "Gmail compose-only token present and valid."
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
        return PASS, "Gmail token had expired but refreshed successfully -- re-saved."
    return FAIL, "Gmail token present but invalid and has no refresh_token -- re-run the OAuth flow before demo."


def check_sheets_permission() -> tuple[str, str]:
    if not SHEETS.audit_spreadsheet_id:
        return WARN, "EDUAGENT_AUDIT_SPREADSHEET_ID not set -- Sheets audit log is disabled by config, not tested."

    from eduagent.integrations.sheets_mcp import _service

    spreadsheet = _service().spreadsheets().get(spreadsheetId=SHEETS.audit_spreadsheet_id).execute()
    title = spreadsheet.get("properties", {}).get("title", "?")
    return PASS, f"Spreadsheet '{title}' ({SHEETS.audit_spreadsheet_id}) reachable with current Sheets token."


def check_vertex_ai_reachability() -> tuple[str, str]:
    from eduagent.llm import _client

    models = list(_client().models.list())
    available = {m.name.rsplit("/", 1)[-1] for m in models if m.name}
    missing = [m for m in (GEMINI.flash_model, GEMINI.heavy_model) if m not in available]
    if missing:
        return WARN, f"Vertex AI reachable, but configured model(s) not found in models.list(): {missing}."
    return PASS, f"Vertex AI reachable; flash_model='{GEMINI.flash_model}' and heavy_model='{GEMINI.heavy_model}' both available."


def check_cloud_run_deployment() -> tuple[str, str]:
    """ĐỢT 3 #5: the other 6 checks only verify local-SA reachability to each
    GCP service -- none of them prove the deployed Cloud Run revision is
    actually up and serving. Fetches a real Google-signed IAM identity token
    (not an OAuth access token -- that's what Cloud Run's IAM invoker check
    validates) and hits the live URL, end to end."""
    if not CLOUD_RUN.service_url:
        return WARN, "EDUAGENT_CLOUD_RUN_URL not set -- skipping live Cloud Run check."

    import google.auth.transport.requests
    import google.oauth2.id_token
    import requests

    health_url = CLOUD_RUN.service_url.rstrip("/") + "/health-check"
    auth_request = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(auth_request, CLOUD_RUN.service_url)

    response = requests.get(health_url, headers={"Authorization": f"Bearer {id_token}"}, timeout=10)
    if response.status_code != 200:
        return FAIL, f"GET {health_url} -> HTTP {response.status_code}: {response.text[:200]}"
    return PASS, f"GET {health_url} -> 200 {response.json()} (live revision reachable with IAM identity token)."


CHECKS = [
    ("GCP credentials (ADC)", check_gcp_credentials),
    ("Firestore connectivity", check_firestore_connectivity),
    ("Pub/Sub topic/DLQ/subscription", check_pubsub_topology),
    ("Gmail OAuth token", check_gmail_oauth_token),
    ("Sheets spreadsheet permission", check_sheets_permission),
    ("Vertex AI / Gemini quota", check_vertex_ai_reachability),
    ("Cloud Run live deployment", check_cloud_run_deployment),
]


def main() -> None:
    print("eduagent System Doctor -- pre-demo readiness check\n" + "=" * 60)
    results = [_check(name, fn) for name, fn in CHECKS]

    for r in results:
        print(f"[{r.status:4}] {r.name}\n       {r.detail}")

    print("=" * 60)
    failed = [r for r in results if r.status == FAIL]
    warned = [r for r in results if r.status == WARN]
    print(f"{len(results) - len(failed) - len(warned)} passed, {len(warned)} warned, {len(failed)} failed.")

    if failed:
        print("\nNOT READY TO DEMO -- fix the FAIL item(s) above first.")
        sys.exit(1)
    if warned:
        print("\nReady to demo, but review the WARN item(s) above (likely optional features left unconfigured).")
    else:
        print("\nAll checks green -- ready to demo.")


if __name__ == "__main__":
    main()
