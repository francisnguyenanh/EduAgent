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

import os
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
    # ĐỢT 16 #7: the single worst regression this project has had (ĐỢT 8) was
    # the subscription sitting in PULL mode while every document described a
    # push pipeline -- "event-driven" only because a human was running a pull
    # script beside the demo. Doctor checked topic/DLQ/subscription existence
    # and would have reported PASS through all of it. Check the actual delivery
    # mode, not just that the objects exist.
    push = subscription.push_config
    if not push or not push.push_endpoint:
        return FAIL, (
            f"Subscription '{PUBSUB.class_aggregator_subscription}' is in PULL mode -- nothing is "
            "event-driven; a human has to run a pull script for events to be processed at all. "
            "Recreate it as a push subscription (see ADR-014 / README architecture section)."
        )
    if not push.oidc_token or not push.oidc_token.service_account_email:
        return FAIL, (
            f"Push subscription '{PUBSUB.class_aggregator_subscription}' carries no OIDC token, so "
            "server.py::_verify_pubsub_push_auth will reject every delivery with 401 (ADR-014). "
            "Re-create it with --push-auth-service-account."
        )

    return PASS, (
        f"Topic '{PUBSUB.essay_evaluated_topic}', DLQ '{PUBSUB.dead_letter_topic}', "
        f"subscription '{PUBSUB.class_aggregator_subscription}' all exist with dead-letter-policy wired correctly; "
        f"delivery is PUSH -> {push.push_endpoint} with OIDC as {push.oidc_token.service_account_email}."
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
    headers = {}
    auth_detail = "public probe"
    try:
        auth_request = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_request, CLOUD_RUN.service_url)
        headers["Authorization"] = f"Bearer {id_token}"
        auth_detail = "with IAM identity token"
    except Exception:
        # Fallback to direct health probe (health-check is public per ADR-011/014)
        pass

    response = requests.get(health_url, headers=headers, timeout=10)
    if response.status_code != 200:
        return FAIL, f"GET {health_url} -> HTTP {response.status_code}: {response.text[:200]}"
    return PASS, f"GET {health_url} -> 200 {response.json()} (live revision reachable, {auth_detail})."


def check_session_secret() -> tuple[str, str]:
    """ĐỢT 12 NHÓM 2 / ADR-016: surface the signing-key state BEFORE a demo.

    The audit's worst finding was invisible precisely because nothing reported
    it: the live service was signing teacher tokens with the repo's committed
    default. auth.py now hard-fails on Cloud Run, but a local run legitimately
    uses the default -- so this check reports which mode is active rather than
    pretending either one is always wrong.
    """
    from eduagent.auth import using_insecure_default_secret

    if not using_insecure_default_secret():
        return PASS, "EDUAGENT_SESSION_SECRET is set to a non-default value (tokens signed with a private key)."
    if os.getenv("K_SERVICE"):
        # Unreachable in practice -- auth.py refuses to import. Kept so that if
        # that guard is ever weakened, this check catches it instead of nothing.
        return FAIL, "Running on Cloud Run with the PUBLIC default signing key -- anyone can forge a teacher token."
    return WARN, (
        "Using the committed default signing key. Fine for local development; "
        "MUST be set via Secret Manager before deploying (see README section 3.4, step 1). "
        "The container refuses to start on Cloud Run without it."
    )


def check_teacher_password_separation() -> tuple[str, str]:
    """ĐỢT 16 #6 / ADR-025: is a teacher token still obtainable with the public
    demo passcode?

    ADR-016 closed token *forgery*; this reports on token *issuance*, which is
    the other half of the same exposure and stayed open. Reported rather than
    enforced: for judging, one shared passcode is a deliberate, documented
    tradeoff -- what must not happen is the state being invisible.
    """
    from eduagent.auth import teacher_password_is_shared_with_students

    if not teacher_password_is_shared_with_students():
        return PASS, "EDUAGENT_TEACHER_PASSWORD is set separately -- a teacher token cannot be minted with the README's student passcode."
    return WARN, (
        "Teacher login accepts the same public demo passcode as students, so anyone who reads the "
        "README can mint a role=teacher token for any class_id and read that class's roster/PII. "
        "This is the documented hackathon-judging tradeoff (ADR-025); set EDUAGENT_TEACHER_PASSWORD "
        "from Secret Manager to close it."
    )


def check_firestore_ttl_policy() -> tuple[str, str]:
    """ĐỢT 12 NHÓM 3: firestore_session.py writes `expire_at`, but Firestore only
    deletes documents when a TTL POLICY exists on that field. Without it, the
    documented "TTL 24h then permanently deleted" retention behaviour silently
    does not happen and sessions accumulate forever."""
    from google.cloud import firestore_admin_v1

    project_id = FIRESTORE.project_id or os.getenv("GCP_PROJECT_ID", "")
    if not project_id:
        return WARN, "No project_id resolved -- cannot check the debate_sessions TTL policy."

    client = firestore_admin_v1.FirestoreAdminClient()
    field_path = (
        f"projects/{project_id}/databases/(default)/collectionGroups/debate_sessions/fields/expire_at"
    )
    field = client.get_field(name=field_path)
    ttl = getattr(field, "ttl_config", None)
    state = getattr(ttl, "state", 0) if ttl is not None else 0

    # 1 = CREATING, 2 = ACTIVE, 3 = NEEDS_REPAIR (google.firestore.admin.v1.Field.TtlConfig.State)
    if state == 2:
        return PASS, "TTL policy ACTIVE on debate_sessions.expire_at -- sessions are really auto-deleted."
    if state == 1:
        return WARN, "TTL policy on debate_sessions.expire_at is still CREATING -- re-check before demo."
    if state == 3:
        return FAIL, "TTL policy on debate_sessions.expire_at is NEEDS_REPAIR -- documents are not being deleted."
    return FAIL, (
        "No TTL policy on debate_sessions.expire_at. `expire_at` is being written but nothing deletes "
        "the documents, so the 24h-retention claim is not true. Fix: "
        "`gcloud firestore fields ttls update expire_at --collection-group=debate_sessions --enable-ttl` "
        "(README section 3.4, step 2)."
    )


_CREDENTIAL_ENV_VARS = ("EDUAGENT_SESSION_SECRET", "GMAIL_COMPOSE_TOKEN_JSON", "SHEETS_TOKEN_JSON")


def _gcloud_executable() -> str | None:
    """Absolute path to the gcloud launcher, or None if it is not on PATH.

    ĐỢT 15 #5: this used to be the bare string "gcloud" passed to
    subprocess.run(). On Windows gcloud installs as `gcloud.cmd` (a batch
    wrapper) and there is no extension-less `gcloud` binary, so CreateProcess
    raised FileNotFoundError and the whole doctor run died with a traceback
    instead of reporting the check. shutil.which() resolves the real launcher on
    every platform (it honours PATHEXT on Windows), which also removes the
    shell=True workaround -- passing a user-influenced command line through a
    shell for a preflight script is not a trade worth making.
    """
    import shutil

    return shutil.which("gcloud") or shutil.which("gcloud.cmd")


def check_no_plaintext_credentials_on_cloud_run() -> tuple[str, str]:
    """ĐỢT 14 / ADR-020: verify no credential is stored as a plain env var on the
    deployed revision.

    Cloud Run keeps plain env vars in the revision spec in cleartext, so anyone
    with `run.services.get` can read them. This check exists because that was a
    real, live exposure: the deployed service was serving both the Gmail and the
    Sheets OAuth refresh tokens in full via `gcloud run services describe`. It
    was found by an external reviewer, not by us -- so now it is automated.
    """
    import json
    import subprocess

    gcloud = _gcloud_executable()
    if gcloud is None:
        return WARN, "gcloud CLI not found on PATH -- cannot inspect the live revision's env vars. Skipped."

    try:
        probe = subprocess.run(
            [
                gcloud, "run", "services", "describe", "eduagent-class-aggregator",
                "--region", "asia-southeast1", "--format=json",
            ],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return WARN, f"Could not execute gcloud ({exc}) -- skipped."
    if probe.returncode != 0:
        return WARN, "Could not describe the Cloud Run service (not deployed, or gcloud not authorized) -- skipped."

    try:
        env = json.loads(probe.stdout)["spec"]["template"]["spec"]["containers"][0].get("env", [])
    except (ValueError, KeyError, IndexError):
        return WARN, "Cloud Run service description had an unexpected shape -- could not inspect env vars."

    plaintext = [e["name"] for e in env if "value" in e and e["name"] in _CREDENTIAL_ENV_VARS]
    secret_refs = [e["name"] for e in env if "value" not in e]
    missing = [name for name in _CREDENTIAL_ENV_VARS if name not in {e["name"] for e in env}]

    if plaintext:
        return FAIL, (
            f"CREDENTIALS IN CLEARTEXT on the live revision: {plaintext}. Readable by anyone with "
            "run.services.get. Redeploy with Secret Manager (`python scripts/deploy_to_cloud_run.py`, "
            "or README section 3.4 steps 1 + 3), then ROTATE those credentials since they were exposed."
        )
    if missing:
        return WARN, (
            f"Credential env var(s) absent from the live revision: {missing} -- the dependent feature "
            f"is disabled there. Mounted as secrets: {secret_refs or 'none'}."
        )
    return PASS, f"All credentials mounted as Secret Manager references (secretKeyRef): {secret_refs}."


CHECKS = [
    ("GCP credentials (ADC)", check_gcp_credentials),
    ("Session signing secret", check_session_secret),
    ("Teacher password separation", check_teacher_password_separation),
    ("No plaintext credentials on Cloud Run", check_no_plaintext_credentials_on_cloud_run),
    ("Firestore connectivity", check_firestore_connectivity),
    ("Firestore TTL policy (debate_sessions)", check_firestore_ttl_policy),
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
