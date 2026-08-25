"""Deploy script for EduAgent Class Aggregator to Cloud Run with all required environment variables."""

import json
import os
import subprocess
import sys
import tempfile
import yaml
from pathlib import Path

ROOT = Path(__file__).parent.parent
SECRETS_DIR = ROOT / "secrets"

PROJECT_ID = "project-4fc36103-f4ca-49f6-883"
SERVICE_ACCOUNT = f"eduagent-sa@{PROJECT_ID}.iam.gserviceaccount.com"
SESSION_SECRET_NAME = "eduagent-session-secret"


def _preflight_session_secret() -> None:
    """ĐỢT 13 / ADR-016: the session signing key must come from Secret Manager.

    `auth.py` refuses to start on Cloud Run while the committed default key is
    still in effect, so a deploy without this secret produces a revision that
    never serves traffic. Failing here, with the exact commands to run, is much
    easier to act on than reading "container failed to start" out of Cloud Run
    logs afterwards.

    This checks rather than creates: minting a signing key is a deliberate,
    one-time act (and re-minting it would invalidate every issued token), so it
    should not be a side effect of running a deploy script.
    """
    probe = subprocess.run(
        ["gcloud", "secrets", "describe", SESSION_SECRET_NAME, f"--project={PROJECT_ID}"],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        print(f"[OK] Secret '{SESSION_SECRET_NAME}' exists -- will be mounted as EDUAGENT_SESSION_SECRET.")
        return

    print(
        f"\n[FAIL] Secret '{SESSION_SECRET_NAME}' does not exist in project {PROJECT_ID}.\n\n"
        "Without it the deployed container REFUSES TO START (ADR-016): the fallback signing key is\n"
        "committed to this public repo, so anyone could mint a role=teacher token for any class.\n\n"
        "Create it once (see deploy.txt STEP 1):\n\n"
        f"  printf '%s' \"$(openssl rand -base64 48)\" | \\\n"
        f"    gcloud secrets create {SESSION_SECRET_NAME} --data-file=- --replication-policy=automatic\n\n"
        f"  gcloud secrets add-iam-policy-binding {SESSION_SECRET_NAME} \\\n"
        f"    --member=serviceAccount:{SERVICE_ACCOUNT} \\\n"
        "    --role=roles/secretmanager.secretAccessor\n"
    )
    sys.exit(1)


def main():
    _preflight_session_secret()
    print("Reading secrets and preparing environment variables...")
    with open(SECRETS_DIR / "gmail_compose_only_token.json") as f:
        gmail_token = json.dumps(json.load(f))

    with open(SECRETS_DIR / "sheets_token.json") as f:
        sheets_token = json.dumps(json.load(f))

    env_vars = {
        "GCP_PROJECT_ID": "project-4fc36103-f4ca-49f6-883",
        "GOOGLE_GENAI_USE_VERTEXAI": "True",
        "GOOGLE_CLOUD_LOCATION": "global",
        "EDUAGENT_FLASH_MODEL": "gemini-3.5-flash",
        "EDUAGENT_HEAVY_MODEL": "gemini-3.7-flash",
        "PUBSUB_PUSH_AUDIENCE": "https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app",
        "PUBSUB_PUSH_SERVICE_ACCOUNT": "eduagent-sa@project-4fc36103-f4ca-49f6-883.iam.gserviceaccount.com",
        "EDUAGENT_TEACHER_EMAIL": "eikitomobe@gmail.com",
        "EDUAGENT_AUDIT_SPREADSHEET_ID": "1pUGTCIzGxZ8xKXbGSgUtd-1pV_qVYUAVqYaJQcyTFnE",
        "EDUAGENT_MOCK_PASSWORD": "eduagent2026",
        "GMAIL_COMPOSE_TOKEN_JSON": gmail_token,
        "SHEETS_TOKEN_JSON": sheets_token,
    }

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tmp:
        yaml.dump(env_vars, tmp)
        tmp_path = tmp.name

    try:
        cmd = [
            "gcloud", "run", "deploy", "eduagent-class-aggregator",
            "--source", str(ROOT),
            "--region", "asia-southeast1",
            "--service-account", "eduagent-sa@project-4fc36103-f4ca-49f6-883.iam.gserviceaccount.com",
            "--allow-unauthenticated",
            "--max-instances", "5",
            "--concurrency", "80",
            "--min-instances", "0",
            f"--env-vars-file={tmp_path}",
            # ADR-016: never inline this value as a plain env var -- it is the
            # token signing key, and --env-vars-file contents end up visible in
            # `gcloud run services describe` output.
            f"--update-secrets=EDUAGENT_SESSION_SECRET={SESSION_SECRET_NAME}:latest",
        ]
        print("Running gcloud run deploy...")
        subprocess.run(cmd, check=True)
        print("Deployment successful!")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    main()
