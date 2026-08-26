"""Deploy script for EduAgent Class Aggregator to Cloud Run with all required environment variables."""

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

# ĐỢT 14 / ADR-020: every credential reaches the container as a Secret Manager
# reference, never as a plain env var. Mapping is {ENV_VAR: secret name}.
#
# WHY (this was a live vulnerability, not a theoretical one): an earlier version
# of this script read the Gmail and Sheets OAuth tokens off disk and passed them
# through `--env-vars-file`. Cloud Run stores plain env vars in the revision spec
# in cleartext, so `gcloud run services describe` printed both refresh tokens in
# full -- verified against the live service. That exposes them to anyone holding
# `run.services.get`, a *read* permission far more widely granted than
# `secretmanager.versions.access`. Mounted secrets appear in that same output as
# `valueFrom.secretKeyRef` (a pointer), so the value never lands in the spec.
#
# No application code changed: Cloud Run injects the secret value into the same
# env var name the integrations already read.
SECRET_ENV_VARS = {
    "EDUAGENT_SESSION_SECRET": "eduagent-session-secret",
    "GMAIL_COMPOSE_TOKEN_JSON": "eduagent-gmail-token",
    "SHEETS_TOKEN_JSON": "eduagent-sheets-token",
}


def _gcloud() -> str:
    """Absolute path to the gcloud launcher. Same ĐỢT 15 #5 Windows fix as
    scripts/doctor.py::_gcloud_executable(): on Windows gcloud is `gcloud.cmd`,
    so the bare string "gcloud" made subprocess.run() raise FileNotFoundError."""
    import shutil

    resolved = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if resolved is None:
        sys.exit("[FAIL] gcloud CLI not found on PATH. Install the Google Cloud SDK, then re-run this script.")
    return resolved


def _preflight_secrets() -> None:
    """Verifies every required secret exists BEFORE deploying.

    `auth.py` refuses to start on Cloud Run while the committed default signing
    key is in effect (ADR-016), so a deploy missing that secret produces a
    revision that never serves traffic. Failing here, with the exact commands to
    run, beats reading "container failed to start" out of Cloud Run logs.

    This checks rather than creates: minting a signing key is a deliberate,
    one-time act -- re-minting invalidates every issued token -- so it must not
    be a side effect of running a deploy script.
    """
    missing = []
    for env_var, secret_name in SECRET_ENV_VARS.items():
        probe = subprocess.run(
            [_gcloud(), "secrets", "describe", secret_name, f"--project={PROJECT_ID}"],
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0:
            print(f"[OK] secret '{secret_name}' exists -> will be mounted as {env_var}")
        else:
            missing.append((env_var, secret_name))

    if not missing:
        return

    print(f"\n[FAIL] {len(missing)} required secret(s) missing in project {PROJECT_ID}:\n")
    for env_var, secret_name in missing:
        print(f"  - {secret_name}  (for {env_var})")
    print(
        "\nCreate them once (see deploy.txt STEP 1):\n\n"
        "  # signing key -- random, never a reused password\n"
        "  printf '%s' \"$(openssl rand -base64 48)\" | \\\n"
        "    gcloud secrets create eduagent-session-secret --data-file=- --replication-policy=automatic\n\n"
        "  # OAuth tokens -- from the local files produced by the one-time auth flow\n"
        "  gcloud secrets create eduagent-gmail-token  --data-file=secrets/gmail_compose_only_token.json --replication-policy=automatic\n"
        "  gcloud secrets create eduagent-sheets-token --data-file=secrets/sheets_token.json --replication-policy=automatic\n\n"
        "  # least privilege: accessor on each secret, not project-wide\n"
        "  for s in eduagent-session-secret eduagent-gmail-token eduagent-sheets-token; do\n"
        f"    gcloud secrets add-iam-policy-binding $s \\\n"
        f"      --member=serviceAccount:{SERVICE_ACCOUNT} \\\n"
        "      --role=roles/secretmanager.secretAccessor\n"
        "  done\n"
    )
    sys.exit(1)


def main():
    _preflight_secrets()
    print("Preparing non-sensitive environment variables...")

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
        # NOTE: GMAIL_COMPOSE_TOKEN_JSON and SHEETS_TOKEN_JSON deliberately do
        # NOT appear here -- they are mounted from Secret Manager below
        # (SECRET_ENV_VARS). Putting them back in this dict would re-expose both
        # refresh tokens in `gcloud run services describe` output.
    }

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tmp:
        yaml.dump(env_vars, tmp)
        tmp_path = tmp.name

    try:
        cmd = [
            _gcloud(), "run", "deploy", "eduagent-class-aggregator",
            "--source", str(ROOT),
            "--region", "asia-southeast1",
            "--service-account", "eduagent-sa@project-4fc36103-f4ca-49f6-883.iam.gserviceaccount.com",
            "--allow-unauthenticated",
            "--max-instances", "5",
            "--concurrency", "80",
            "--min-instances", "0",
            f"--env-vars-file={tmp_path}",
            # Every credential arrives as a secret reference, never a plain env
            # var -- see SECRET_ENV_VARS for why (verified live exposure).
            "--update-secrets=" + ",".join(
                f"{env_var}={secret}:latest" for env_var, secret in SECRET_ENV_VARS.items()
            ),
        ]
        print("Running gcloud run deploy...")
        subprocess.run(cmd, check=True)
        print("Deployment successful!")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    main()
